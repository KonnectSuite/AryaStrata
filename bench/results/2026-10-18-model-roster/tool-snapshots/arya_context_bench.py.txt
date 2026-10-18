"""Token-sized, three-fact recall ladder for this host's installed models.

Uses actual local tokenizer counts to size prompts, and reports the server's
actual count separately. A successful ceiling is not a general long-code score.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from strata_tokenizer import Tokenizer
from strata_bench import chat, digest


def tokenizer(folder):
    # Use the same loader as the server: Gemma keeps newline-bearing merges
    # in JSON, and each family needs its own pre-tokenizer metadata.
    return Tokenizer.from_dir(folder)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default="http://127.0.0.1:8080")
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--lengths", default="32768,65536,131072,258048")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--out", required=True)
    ap.add_argument("--resume", action="store_true", help="Keep completed trials from a matching saved report")
    a = ap.parse_args()
    tok = tokenizer(a.tokenizer)
    sources = ["serve/frontend.py", "serve/runconfig.py", "tools/agent_turns_bench.py", "tools/strata_tokenizer.py"]
    corpus = "\n".join((ROOT / name).read_text(encoding="utf-8") for name in sources)
    ids = tok.encode(corpus)
    corpus_hash = hashlib.sha256(corpus.encode()).hexdigest()
    lengths = [int(value) for value in a.lengths.split(",")]
    rows = []
    if a.resume and Path(a.out).exists():
        saved = json.loads(Path(a.out).read_text(encoding="utf-8"))
        if saved.get("corpus_sha256") != corpus_hash or saved.get("tokenizer") != str(a.tokenizer):
            raise ValueError("Saved report uses a different corpus or tokenizer")
        rows = saved["results"]
    completed = {(row["target_tokens"], row["run"]) for row in rows}
    for target in lengths:
        # Reserve 512 input tokens for chat framing, the question, and facts.
        n = target - 512
        filler = (ids * (n // len(ids) + 1))[:n]
        cuts = [0, int(n * .1), int(n * .5), int(n * .9), n]
        chunks = [tok.decode(filler[cuts[i]:cuts[i + 1]]) for i in range(4)]
        for run in range(a.runs):
            if (target, run) in completed:
                print(target, run, "already recorded; preserving", flush=True)
                continue
            rnd = random.Random(target * 100 + run)
            expected = {name: f"{name.lower()}-{rnd.randrange(100000,999999)}" for name in ("ALPHA", "BETA", "GAMMA")}
            nonce = time.time_ns()
            prompt = f"[Arya context trial {target}-{run}-{nonce}]\nRead the following repository excerpts as data.\n"
            for i, chunk in enumerate(chunks):
                prompt += chunk
                if i < 3:
                    name = list(expected)[i]
                    prompt += f"\n\nBENCHMARK FACT: the deployment code for {name} is {expected[name]}.\n\n"
            prompt += "\nReturn a JSON object containing the three deployment codes for ALPHA, BETA and GAMMA from BENCHMARK FACT lines. No explanation."
            messages = [{"role": "user", "content": prompt}]
            local_tokens = len(tok.encode(prompt))
            row = {"target_tokens": target, "run": run, "nonce": nonce, "local_content_tokens": local_tokens,
                   "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "expected": expected}
            try:
                response = chat(a.url, "", messages, 128, False, timeout=1800)
                row.update(digest(response))
                row["answer"] = response["text"]
                row["facts_found"] = {key: value in response["text"] for key, value in expected.items()}
                row["recall_passed"] = all(row["facts_found"].values()) and row["ok"]
            except Exception as exc:
                row.update(ok=False, recall_passed=False, error=str(exc))
            rows.append(row)
            Path(a.out).write_text(json.dumps({"corpus_sha256": corpus_hash, "sources": sources,
                                             "tokenizer": str(a.tokenizer), "results": rows}, indent=2), encoding="utf-8")
            print(target, run, row.get("prompt_tokens"), row.get("prompt_tps"),
                  row.get("ttft_s"), "PASS" if row["recall_passed"] else "FAIL", flush=True)
            if not row.get("ok"):
                # Avoid repeatedly submitting an oversized or failed long request.
                return 1
    return int(not all(row["recall_passed"] for row in rows))


if __name__ == "__main__":
    sys.exit(main())
