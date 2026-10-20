"""End-to-end check: start the real server on the tuned config, then drive it the way AryaAI does.

Proves the whole stack - config -> engine -> OpenAI-compatible API -> thinking modes - not just the
engine pipe the benchmarks used.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(r"C:\AryaStrata")
PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
PORT = 8091          # not 8080: leave the daily-driver port free
BASE = f"http://127.0.0.1:{PORT}"
LOG = ROOT / ".tune" / "logs" / f"server-verify-{int(time.time())}.log"


def wait_health(timeout: float = 300.0) -> dict:
    t0 = time.monotonic()
    last = None
    while time.monotonic() - t0 < timeout:
        try:
            r = requests.get(f"{BASE}/health", timeout=3)
            if r.status_code == 200:
                return {"health": r.json(), "waited_s": round(time.monotonic() - t0, 1)}
        except Exception as exc:  # noqa: BLE001
            last = str(exc)[:120]
        time.sleep(2)
    raise TimeoutError(f"no /health after {timeout}s (last error: {last}); see {LOG}")


def main() -> int:
    out = {"port": PORT, "log": str(LOG)}
    log = open(LOG, "w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(
        [PY, str(ROOT / "serve" / "server.py"), "--config", str(ROOT / "strata-iq3_xxs.json"),
         "--engine", "strata", "--port", str(PORT), "--host", "127.0.0.1"],
        cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT, text=True,
    )
    try:
        h = wait_health()
        out.update(h)
        print(f"health after {h['waited_s']}s: {json.dumps(h['health'])}", flush=True)

        models = requests.get(f"{BASE}/v1/models", timeout=10).json()
        out["models"] = [m.get("id") for m in models.get("data", [])]
        print(f"/v1/models: {out['models']}", flush=True)

        question = ("A pump moves 240 litres per minute into a tank holding 1,800 litres; the tank "
                    "drains 90 litres per minute. How many minutes until it holds exactly 6,000 litres?")
        results = {}
        for effort in ("none", "low", "medium", "high"):
            body = {"model": out["models"][0] if out["models"] else "qwen3.8-flash-next-iq3_xxs",
                    "messages": [{"role": "user", "content": question}],
                    "reasoning_effort": effort, "max_tokens": 700, "temperature": 0}
            t0 = time.monotonic()
            r = requests.post(f"{BASE}/v1/chat/completions", json=body, timeout=600)
            dt = time.monotonic() - t0
            if r.status_code != 200:
                results[effort] = {"status": r.status_code, "error": r.text[:200]}
                print(f"  {effort:<7} HTTP {r.status_code}: {r.text[:160]}", flush=True)
                continue
            j = r.json()
            msg = j["choices"][0]["message"]
            reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
            content = msg.get("content") or ""
            usage = j.get("usage") or {}
            results[effort] = {
                "status": 200, "wall_s": round(dt, 2),
                "reasoning_chars": len(reasoning), "content_chars": len(content),
                "completion_tokens": usage.get("completion_tokens"),
                "prompt_tokens": usage.get("prompt_tokens"),
                "answer_has_28": "28" in content,
                "reasoning_preview": reasoning.strip()[:120].replace("\n", " "),
                "answer_preview": content.strip()[:120].replace("\n", " "),
            }
            print(f"  {effort:<7} {dt:5.1f}s  reasoning {len(reasoning):>4} ch  "
                  f"answer {len(content):>4} ch  says-28={results[effort]['answer_has_28']}", flush=True)
        out["modes"] = results
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=45)
        except Exception:  # noqa: BLE001
            proc.kill()
        log.close()
    p = ROOT / ".tune" / "results" / "server-verify.json"
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
