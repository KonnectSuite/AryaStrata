"""Thinking-mode verification, live half: every control mode against the real engine.

Renders the wire prompt the server would send (serve/frontend.effort_kwargs + the installed
chat_template.jinja), feeds it straight to the engine over the pipe protocol, decodes the reply
and reports where the reasoning stopped. Proves each advertised mode is a distinct, working
behaviour on this model - not only a distinct prompt hash.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(r"C:\AryaStrata")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / ".tune"))

import bench                                              # noqa: E402
from strata_tokenizer import Tokenizer                    # noqa: E402
from serve.frontend import ChatTemplate, effort_kwargs    # noqa: E402
from serve.server import MockEngine, Service              # noqa: E402

LEVELS = ("none", "low", "medium", "high")
QUESTION = (
    "A pump moves 240 litres per minute into a tank that already holds 1,800 litres. "
    "The tank drains at 90 litres per minute while filling. After how many minutes is the "
    "tank at exactly 6,000 litres? Show the arithmetic and give the final number."
)
MAX_NEW = 700


def render(tok, template, model, level):
    svc = Service(MockEngine(tok, "READY"), tok, ChatTemplate(template), model_name=model)
    wire = svc.render_prompt([{"role": "user", "content": QUESTION}], None, effort_kwargs(level))
    return wire


def split_reasoning(text: str) -> dict:
    """The assistant turn as the engine produced it: reasoning up to </think>, then the answer."""
    if "</think>" in text:
        head, _, tail = text.partition("</think>")
        reason, answer = head.replace("<think>", "", 1), tail.strip()
    else:
        reason, answer = "", text.strip()
    return {"reasoning_chars": len(reason.strip()), "answer_chars": len(answer),
            "reasoning_preview": reason.strip()[:160].replace("\n", " "),
            "answer_preview": answer[:160].replace("\n", " ")}


def main() -> int:
    cfg = bench.load_base()
    folder = Path(cfg["tokenizer"])
    tok = Tokenizer.from_dir(folder)
    template = folder / "chat_template.jinja"
    model = cfg["model_name"]

    base_args = bench.apply_overrides(cfg["args"], {"--prompt-cache": "0"})
    print("starting one engine for every thinking mode ...", flush=True)
    eng = bench.Engine(base_args, "think-live")
    print(f"engine ready in {eng.load_s:.1f}s", flush=True)
    out = {"model": model, "question": QUESTION, "modes": {}}
    try:
        for level in LEVELS:
            wire = render(tok, template, model, level)
            ids = tok.encode(wire, parse_special=True)
            t0 = time.monotonic()
            m = eng.generate(ids, MAX_NEW)
            wall = time.monotonic() - t0
            text = tok.decode(eng.last_ids)
            info = split_reasoning(text)
            info.update({"prompt_tokens": len(ids), "generated": m["generated"],
                         "reasoning_tokens_est": round(info["reasoning_chars"] / 3.6),
                         "decode_tok_s": m["decode_tok_s"], "wall_s": round(wall, 1),
                         "finish": m["finish"],
                         "answer_tail": text.strip()[-200:].replace("\n", " ")})
            out["modes"][level] = info
            print(f"  {level:<7} reasoning {info['reasoning_tokens_est']:>4} tok est, "
                  f"answer {info['answer_chars']:>4} ch, {m['decode_tok_s']} tok/s, "
                  f"finish={m['finish']}", flush=True)
            print(f"          think: {info['reasoning_preview'][:120]}", flush=True)
            print(f"          answer: {info['answer_preview'][:120]}", flush=True)
    finally:
        eng.close()
    path = ROOT / ".tune" / "results" / "think-live.json"
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
