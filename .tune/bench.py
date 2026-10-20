"""Qwen3.8 Flash Next tuning harness for AryaStrata.

Drives `strata.exe --serve` directly over its pipe protocol (GEN / T / DONE), so every
measurement is the engine's own accounting: prompt_ms, decode_ms, draft acceptance,
expert-tier hits. No HTTP, no client-side timing noise.

Protocol (serve/server.py: `_parse_done`):
    DONE <generated> <prompt_tokens> <prompt_ms> <decode_ms> <finish>
         [<drafts_accepted> <drafts_offered> <reused> <hits> <lookups>
          <ram_blobs> <file_blobs> <file_mb> <prompt_read> <offloaded>]
         [chunk=N experts_streamed=N]

Usage:
    python bench.py --config baseline --reps 3
    python bench.py --sweep sweeps/pool_workers.json
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(r"C:\AryaStrata")
CONFIG = ROOT / "strata-iq3_xxs.json"
DLL_DIR = ROOT / ".venv" / "Lib" / "site-packages" / "nvidia" / "cu13" / "bin" / "x86_64"
OUT = ROOT / ".tune" / "results"
LOGS = ROOT / ".tune" / "logs"

sys.path.insert(0, str(ROOT / "tools"))
import strata_tokenizer as ST  # noqa: E402

READY_TIMEOUT_S = 420.0

# ---------------------------------------------------------------- prompt fixtures

FILLER = (
    "The motor control sequence must latch the run output only after the start "
    "pushbutton is held, the safety interlock chain is closed, and the drive reports "
    "no fault. Each scan the routine evaluates the permissive bits, the seal-in "
    "contact, and the fault timer, then writes the coil state and the diagnostic "
    "word the HMI reads back. Adding a diagnostic requires a new tag and a matching "
    "faceplate block, so the sequence and the display must be changed together.\n"
)


def prompt_ids(tok: ST.Tokenizer, target_tokens: int, tag: str = "") -> list[int]:
    """A fixed prompt of roughly `target_tokens` tokens, stable for a given (target, tag)."""
    text = f"# Maintenance note {tag}\n" + FILLER
    ids = tok.encode(text)
    while len(ids) < target_tokens:
        text += FILLER
        ids = tok.encode(text)
    # trim to the requested length so the prompt is byte-identical across configs
    return ids[:target_tokens]


# ---------------------------------------------------------------- config plumbing

def load_base() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8-sig"))


def apply_overrides(base_args: list[str], overrides: dict) -> list[str]:
    """overrides: {"--flag": value, ...}. None removes the flag; True adds a bare switch.

    Replaces an existing flag in place (keeping its position) or appends it, so the
    engine never sees the same flag twice.
    """
    args = list(base_args)
    for flag, value in overrides.items():
        idx = None
        for i, a in enumerate(args):
            if a == flag:
                idx = i
                break
        if value is None:
            if idx is not None:
                if idx + 1 < len(args) and not args[idx + 1].startswith("--"):
                    del args[idx:idx + 2]
                else:
                    del args[idx:idx + 1]
            continue
        if value is True:
            if idx is None:
                args.append(flag)
            continue
        if value is False:
            if idx is not None:
                del args[idx:idx + 2]
            continue
        if idx is None:
            args.extend([flag, str(value)])
        else:
            args[idx + 1] = str(value)
    return args


def engine_env(base: dict) -> dict:
    env = os.environ.copy()
    dirs = [str(Path(d)) for d in (base.get("lib_dirs") or [])]
    if DLL_DIR.exists() and str(DLL_DIR) not in dirs:
        dirs.insert(0, str(DLL_DIR))
    env["PATH"] = ";".join(dirs + [env.get("PATH", "")])
    for k, v in (base.get("env") or {}).items():
        env[str(k)] = str(v)
    return env


# ---------------------------------------------------------------- one engine run

class Engine:
    def __init__(self, args: list[str], tag: str, env_extra: dict | None = None):
        base = load_base()
        if env_extra:
            base = {**base, "env": {**(base.get("env") or {}), **env_extra}}
        self.tag = tag
        self.log_path = LOGS / f"{tag}.log"
        self.log = open(self.log_path, "w", encoding="utf-8", errors="replace")
        t0 = time.monotonic()
        self.proc = subprocess.Popen(
            [base["exe"], "--serve", *args],
            cwd=base.get("cwd") or str(ROOT),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
            env=engine_env(base),
        )
        self.q: queue.Queue = queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()
        self.info: dict = {}
        self.max_context = 0
        self.reused = 0
        deadline = time.monotonic() + READY_TIMEOUT_S
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                self.kill()
                raise TimeoutError(f"{tag}: no READY within {READY_TIMEOUT_S}s (see {self.log_path})")
            try:
                line = self.q.get(timeout=min(left, 5.0))
            except queue.Empty:
                if self.proc.poll() is not None:
                    raise RuntimeError(f"{tag}: engine exited {self.proc.returncode} before READY (see {self.log_path})")
                continue
            if line is None:
                raise RuntimeError(f"{tag}: engine closed stdout before READY (see {self.log_path})")
            if line.startswith("INFO "):
                for kv in line.split()[1:]:
                    k, _, v = kv.partition("=")
                    self.info[k] = int(v) if v.lstrip("-").isdigit() else v
            if line.startswith("READY"):
                self.max_context = int(line.split()[1])
                break
        self.load_s = time.monotonic() - t0

    def _pump(self):
        try:
            for line in self.proc.stdout:
                self.q.put(line.rstrip("\n"))
        except Exception:
            pass
        self.q.put(None)

    def generate(self, ids: list[int], max_new: int, timeout: float = 900.0) -> dict:
        self.proc.stdin.write(f"GEN {max_new} {','.join(str(i) for i in ids)}\n")
        self.proc.stdin.flush()
        toks: list[int] = []
        pp_lines = 0
        deadline = time.monotonic() + timeout
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError(f"{self.tag}: no DONE within {timeout}s")
            try:
                line = self.q.get(timeout=min(left, 5.0))
            except queue.Empty:
                continue
            if line is None:
                raise RuntimeError(f"{self.tag}: engine died during GEN (see {self.log_path})")
            if line.startswith("T "):
                toks.append(int(line[2:]))
            elif line.startswith("PP"):
                pp_lines += 1
            elif line.startswith("DONE"):
                self.last_ids = list(toks)
                return parse_done(line, len(toks), pp_lines)
            elif line.startswith("ERR"):
                raise RuntimeError(f"{self.tag}: engine refused GEN: {line[4:].strip()}")

    def close(self):
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self.kill()
        try:
            self.log.close()
        except Exception:
            pass

    def kill(self):
        try:
            self.proc.kill()
        except Exception:
            pass


def parse_done(line: str, seen_tokens: int, pp_lines: int) -> dict:
    f = line.split()
    out = {
        "generated": int(f[1]), "prompt_tokens": int(f[2]),
        "prompt_ms": float(f[3]), "decode_ms": float(f[4]), "finish": f[5],
    }
    names15 = ["drafts_accepted", "drafts_offered", "reused", "hits", "lookups",
               "ram_blobs", "file_blobs", "file_mb", "prompt_read", "offloaded"]
    for name, tok in zip(names15, f[6:16]):
        try:
            out[name] = float(tok) if "." in tok else int(tok)
        except ValueError:
            out[name] = tok
    for tok in f[16:]:
        k, eq, v = tok.partition("=")
        if eq and k in ("chunk", "experts_streamed"):
            out[k] = int(v)
    out["tokens_seen"] = seen_tokens
    out["pp_lines"] = pp_lines
    g = out["generated"]
    out["decode_tok_s"] = round(g * 1000.0 / out["decode_ms"], 3) if out["decode_ms"] > 0 else None
    pr = out.get("prompt_read") or out["prompt_tokens"]
    out["prefill_tok_s"] = round(pr * 1000.0 / out["prompt_ms"], 3) if out["prompt_ms"] > 0 else None
    if out.get("drafts_offered"):
        out["draft_accept"] = round(out.get("drafts_accepted", 0) / out["drafts_offered"], 3)
    return out


# ---------------------------------------------------------------- one arm

def run_arm(tag: str, overrides: dict, cases: list[dict], reps: int, keep_raw: bool = True) -> dict:
    base = load_base()
    args = apply_overrides(base["args"], overrides)
    eng = Engine(args, tag)
    result = {
        "tag": tag, "overrides": overrides, "args": args,
        "load_s": round(eng.load_s, 2), "max_context": eng.max_context,
        "engine_info": dict(eng.info), "cases": {},
    }
    try:
        for case in cases:
            ids = case["ids"]
            samples = []
            for r in range(reps):
                m = eng.generate(ids, case["max_new"])
                m["rep"] = r
                samples.append(m)
            dec = [s["decode_tok_s"] for s in samples if s.get("decode_tok_s")]
            pre = [s["prefill_tok_s"] for s in samples if s.get("prefill_tok_s")]
            entry = {
                "name": case["name"], "prompt_tokens": case["prompt_tokens"],
                "max_new": case["max_new"],
                "decode_tok_s": round(sorted(dec)[len(dec) // 2], 3) if dec else None,
                "prefill_tok_s": round(sorted(pre)[len(pre) // 2], 3) if pre else None,
                "prompt_ms": round(median([s["prompt_ms"] for s in samples]), 2),
                "decode_ms": round(median([s["decode_ms"] for s in samples]), 2),
                "draft_accept": round(median([s["draft_accept"] for s in samples if "draft_accept" in s] or [0]), 3),
                "hits": samples[-1].get("hits"), "lookups": samples[-1].get("lookups"),
                "file_mb": samples[-1].get("file_mb"), "offloaded": samples[-1].get("offloaded"),
                "chunk": samples[-1].get("chunk"),
                "samples": samples if keep_raw else None,
            }
            result["cases"][case["name"]] = entry
            print(f"  [{tag}] {case['name']:>10}  pp {entry['prefill_tok_s']} tok/s  "
                  f"decode {entry['decode_tok_s']} tok/s  accept {entry['draft_accept']}"
                  f"  chunk {entry['chunk']}", flush=True)
    finally:
        eng.close()
    return result


def median(xs: list[float]) -> float:
    xs = sorted(xs)
    if not xs:
        return 0.0
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


# ---------------------------------------------------------------- cases

def build_cases(tok: ST.Tokenizer, sizes: list[int], max_new: int, tag: str) -> list[dict]:
    cases = []
    for n in sizes:
        ids = prompt_ids(tok, n, tag=tag)
        cases.append({"name": f"{n // 1024}k" if n >= 1024 else str(n),
                      "prompt_tokens": len(ids), "max_new": max_new, "ids": ids})
    return cases


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="baseline")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--sizes", default="2048,8192")
    ap.add_argument("--max-new", type=int, default=128)
    ap.add_argument("--sweep", help="JSON file: [{tag, overrides}, ...]")
    ap.add_argument("--override", action="append", default=[],
                    help="flag=value (or flag= for a bare switch); repeatable")
    ap.add_argument("--out", default=None)
    ap.add_argument("--tokenizer", default=r"C:\AI\Strata-data\packs\iq3_xxs\tokenizer")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)

    t_tok = time.monotonic()
    tok = ST.Tokenizer.from_dir(args.tokenizer)
    print(f"tokenizer loaded in {time.monotonic() - t_tok:.1f}s", flush=True)

    sizes = [int(s) for s in args.sizes.split(",") if s.strip()]
    tag = args.config.replace(" ", "_")
    cases = build_cases(tok, sizes, args.max_new, tag)
    print("cases: " + ", ".join(f"{c['name']}={c['prompt_tokens']}tok" for c in cases), flush=True)

    if args.sweep:
        arms = json.loads(Path(args.sweep).read_text(encoding="utf-8"))
    else:
        ov = {}
        for item in args.override:
            flag, _, value = item.partition("=")
            ov[flag] = True if value == "" else value
        arms = [{"tag": tag, "overrides": ov}]

    results = []
    for arm in arms:
        print(f"\n=== arm {arm['tag']}  {arm['overrides']} ===", flush=True)
        results.append(run_arm(arm["tag"], arm["overrides"], cases, args.reps))

    out_path = Path(args.out) if args.out else OUT / f"{tag}-{int(time.time())}.json"
    payload = {"when": time.strftime("%Y-%m-%dT%H:%M:%S"), "reps": args.reps,
               "sizes": sizes, "max_new": args.max_new, "arms": results}
    out_path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"\nwrote {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
