"""Thinking-mode verification, offline half: render the wire prompt for every control mode.

No GPU, no engine. Uses the same objects the server does (`Service.render_prompt` over the
installed chat_template.jinja), so what it prints is exactly what the engine would receive.

Modes come from serve/frontend.py:
    EFFORT = {none|off|minimal|disabled -> enable_thinking=False,
              low -> "low", medium -> "medium", high|xhigh|max -> "xhigh"}
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(r"C:\AryaStrata")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from strata_tokenizer import Tokenizer                      # noqa: E402
from serve.frontend import ChatTemplate, effort_kwargs      # noqa: E402
from serve.server import MockEngine, Service                # noqa: E402

LEVELS = ("none", "low", "medium", "high")
MESSAGES = [{"role": "user", "content": "Reply READY."}]
TOOLS = [{"name": "read_file", "description": "Read a fixture",
          "parameters": {"type": "object",
                         "properties": {"path": {"type": "string"}},
                         "required": ["path"]}}]


def audit(config_path: Path) -> dict:
    cfg = json.loads(config_path.read_text(encoding="utf-8-sig"))
    identity = cfg["model_name"]
    folder = Path(cfg["tokenizer"])
    template_path = folder / "chat_template.jinja"
    tok = Tokenizer.from_dir(folder)
    svc = Service(MockEngine(tok, "READY"), tok, ChatTemplate(template_path),
                  model_name=identity)

    rows = []
    for tools in (None, TOOLS):
        prompts = {lvl: svc.render_prompt(MESSAGES, tools, effort_kwargs(lvl)) for lvl in LEVELS}
        hashes = {k: hashlib.sha256(v.encode()).hexdigest()[:16] for k, v in prompts.items()}
        rows.append({
            "tools": bool(tools),
            "sha": hashes,
            "distinct_all": len(set(hashes.values())) == len(LEVELS),
            "tails": {lvl: prompts[lvl][-90:].replace("\n", "\\n") for lvl in LEVELS},
        })
    return {
        "model": identity,
        "template": str(template_path),
        "template_sha256": hashlib.sha256(template_path.read_bytes()).hexdigest()[:16],
        "levels": list(LEVELS),
        "cases": rows,
    }


def main() -> int:
    out = {}
    for cfg in sorted(ROOT.glob("strata-*.json")):
        if ".pre-calibration" in cfg.name:
            continue
        try:
            res = audit(cfg)
        except Exception as exc:  # noqa: BLE001
            print(f"{cfg.name}: FAILED {type(exc).__name__}: {exc}")
            out[cfg.name] = {"error": f"{type(exc).__name__}: {exc}"}
            continue
        out[cfg.name] = res
        print(f"\n=== {res['model']}  (template {res['template_sha256']}) ===")
        for case in res["cases"]:
            print(f"  tools={str(case['tools']):<5} distinct={case['distinct_all']}  "
                  + "  ".join(f"{k}={v}" for k, v in case["sha"].items()))
        for lvl in LEVELS:
            print(f"    tail[{lvl}] ...{res['cases'][0]['tails'][lvl]}")
    path = ROOT / ".tune" / "results" / "think-audit.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
