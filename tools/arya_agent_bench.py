"""Bounded local coding-agent evaluation through the OpenAI-compatible API.

Each session must read a fixture, edit it through a tool, and run its tests.
This evaluates the model/API tool loop, not the AryaAI desktop UI or SWE-bench.
Generated Python is syntax-checked and restricted, then tested in a timed child.
"""
from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

CASES = [
    {"name": "merge_sorted", "source": "def merge_sorted(a, b):\n    return list(a) + list(b)\n",
     "request": "Fix merge_sorted(a, b): return the sorted merge of two sorted integer lists. Preserve duplicates, handle empty inputs, and do not mutate either input.",
     "tests": "a=[1,3,3]; b=[2,3,4]; assert merge_sorted(a,b)==[1,2,3,3,3,4]; assert a==[1,3,3] and b==[2,3,4]; assert merge_sorted([],[])==[]; assert merge_sorted([],[-2,0])==[-2,0]; assert merge_sorted([-4,-1],[0])==[-4,-1,0]"},
    {"name": "chunked", "source": "def chunked(values, size):\n    return [values]\n",
     "request": "Fix chunked(values, size): return consecutive list chunks of at most size, preserve ordering, return [] for empty input, and raise ValueError for size <= 0. Do not mutate values.",
     "tests": "a=[1,2,3,4,5]; assert chunked(a,2)==[[1,2],[3,4],[5]]; assert a==[1,2,3,4,5]; assert chunked([],3)==[]; assert chunked([1],10)==[[1]]; assert chunked([1,2],1)==[[1],[2]]\nfor size in [0,-1]:\n    try: chunked([],size)\n    except ValueError: pass\n    else: raise AssertionError('invalid size accepted')"},
    {"name": "parse_pairs", "source": "def parse_pairs(lines):\n    return {}\n",
     "request": "Fix parse_pairs(lines): skip blank lines, split each other line on its first '=', strip whitespace from key/value, reject missing '=' or empty key with ValueError, preserve '=' in values, and let later duplicate keys win. Do not mutate input.",
     "tests": "a=[' x = a=b ', '', 'x=c', ' y = 2 ']; assert parse_pairs(a)=={'x':'c','y':'2'}; assert a==[' x = a=b ', '', 'x=c', ' y = 2 ']; assert parse_pairs([])=={}; assert parse_pairs(['key='])=={'key':''}\nfor lines in [['bad'],[' =x']]:\n    try: parse_pairs(lines)\n    except ValueError: pass\n    else: raise AssertionError('invalid line accepted')"},
]

TOOLS = [{"type": "function", "function": {"name": name, "description": desc,
          "parameters": {"type": "object", "properties": props, "required": required,
                         "additionalProperties": False}}}
         for name, desc, props, required in [
             ("read_file", "Read the fixture module.py", {"path": {"type": "string"}}, ["path"]),
             ("write_file", "Replace module.py with the corrected Python code",
              {"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
             ("run_tests", "Run the fixture's regression tests", {}, []),
         ]]


def validate(source):
    tree = ast.parse(source)
    banned = (ast.Import, ast.ImportFrom, ast.ClassDef, ast.AsyncFunctionDef,
              ast.Global, ast.Nonlocal, ast.With, ast.AsyncWith)
    attrs = {"append", "extend", "split", "strip", "items", "get", "lower", "isdigit", "copy"}
    for node in ast.walk(tree):
        if isinstance(node, banned):
            raise ValueError("Only standalone Python functions without imports are allowed")
        if isinstance(node, ast.Name) and (node.id.startswith("__") or node.id in
                {"open", "exec", "eval", "compile", "getattr", "setattr", "globals", "locals", "vars", "input", "breakpoint"}):
            raise ValueError("Forbidden name")
        if isinstance(node, ast.Attribute) and node.attr not in attrs:
            raise ValueError("Unsupported attribute: " + node.attr)
    return tree


def check(source, tests):
    try:
        validate(source)
        body = ("scope={'__builtins__':{k:__builtins__[k] for k in "
                "('len','range','enumerate','sorted','list','dict','tuple','min','max','ValueError','TypeError','AssertionError','StopIteration','int','str','float','zip','bool','sum','any','all','abs','isinstance','reversed','set','iter','next','map','filter')}}\n"
                "exec(" + repr(source) + ",scope)\nexec(" + repr(tests) + ",scope)\n")
        # __builtins__ is a module when the interpreter runs -c.
        body = "import builtins\n__builtins__=vars(builtins)\n" + body
        result = subprocess.run([sys.executable, "-I", "-c", body],
                                capture_output=True, text=True, timeout=5)
        return {"passed": result.returncode == 0, "detail": result.stderr[-1800:]}
    except Exception as exc:
        return {"passed": False, "detail": str(exc)}


def request(base, messages, think):
    payload = {"model": "qwen3.8-flash-next-iq3_xxs", "messages": messages,
               "tools": TOOLS, "temperature": 0, "max_tokens": 1400,
               "reasoning_effort": think}
    req = urllib.request.Request(base.rstrip("/") + "/v1/chat/completions",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    start = time.monotonic()
    with urllib.request.urlopen(req, timeout=240) as response:
        result = json.load(response)
    return result, time.monotonic() - start


def session(base, case, run, think):
    messages = [{"role": "system", "content":
        "You are a coding agent in a bounded Python fixture. Read module.py, fix it with write_file, then run_tests. "
        "Only standalone functions, no imports, no classes, no filesystem or networking code. "
        "Use tools rather than merely describing a patch. After tests pass, give a short summary."},
        {"role": "user", "content": f"Session {case['name']}-{run}-{think}. {case['request']}"}]
    source, read, wrote, passed = case["source"], False, False, False
    trace, calls = [], []
    start = time.monotonic()
    for turn in range(9):
        result, secs = request(base, messages, think)
        msg = result["choices"][0]["message"]
        trace.append({"turn": turn, "seconds": secs, "response": result})
        messages.append(msg)
        if not msg.get("tool_calls"):
            break
        for call in msg["tool_calls"]:
            name = call["function"]["name"]
            try:
                args = json.loads(call["function"]["arguments"])
                if name == "read_file" and args.get("path") == "module.py":
                    read = True
                    output = {"content": source}
                elif name == "write_file" and args.get("path") == "module.py" and read:
                    validate(args["content"])
                    source, wrote = args["content"], True
                    output = {"written": True}
                elif name == "run_tests" and wrote:
                    output = check(source, case["tests"])
                    passed = output["passed"]
                else:
                    output = {"error": "Read module.py first, write module.py, then run_tests; no other paths allowed"}
            except Exception as exc:
                output = {"error": str(exc)}
            calls.append({"name": name, "result": output})
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(output)})
    final_check = check(source, case["tests"])
    return {"case": case["name"], "run": run, "think": think,
            "passed": bool(read and wrote and passed and final_check["passed"]), "final_check": final_check,
            "seconds": time.monotonic() - start, "calls": calls, "source": source, "trace": trace}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default="http://127.0.0.1:8080")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--think", default="none")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = []
    for run in range(a.runs):
        for case in CASES:
            try:
                row = session(a.url, case, run, a.think)
            except Exception as exc:
                row = {"case": case["name"], "run": run, "think": a.think, "passed": False, "error": str(exc)}
            rows.append(row)
            Path(a.out).write_text(json.dumps({"tool": __file__, "results": rows}, indent=2), encoding="utf-8")
            print(case["name"], run, "PASS" if row["passed"] else "FAIL", round(row.get("seconds", 0), 2), flush=True)
    return int(not all(row["passed"] for row in rows))


if __name__ == "__main__":
    sys.exit(main())
