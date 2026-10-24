"""Flint benchmark at 256K context: prefill and decode separated.

Each request opens with a unique nonce, so no prefix/conversation cache is reused.
Numbers are taken from the engine's own `timings` block when present, with
client-side TTFT as a cross-check.
"""
import json
import random
import statistics
import time
import uuid

import requests

BASE = "http://127.0.0.1:8080/v1/chat/completions"
MODEL = "flint-40b-a2.5b-ud-q4_k_xl"
# size -> repeats (the 245K runs are minutes each)
SIZES = {8192: 3, 32768: 3, 131072: 3, 246000: 2}
MAX_TOKENS = 128
CHARS_PER_TOKEN = 5.54        # measured on this filler: 29,491 chars -> 5,321 tokens

WORDS = ("engine memory expert router token context tensor layer cache matrix vector batch "
         "decode prefill gradient window attention block stream buffer thread kernel").split()


def filler(target_tokens: int, seed: int) -> str:
    rnd = random.Random(seed)
    target_chars = int(target_tokens * CHARS_PER_TOKEN)
    out = [f"Benchmark document {uuid.uuid4()}.\n"]
    n = 0
    while n < target_chars:
        line = " ".join(rnd.choice(WORDS) for _ in range(rnd.randint(8, 16)))
        line = f"{line} {rnd.randint(1000, 999999)}.\n"
        out.append(line)
        n += len(line)
    return "".join(out)


def run_once(target_tokens: int, seed: int) -> dict:
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": filler(target_tokens, seed)
                      + "\n\nIgnore the document. Reply with the single word DONE."}],
        "max_tokens": MAX_TOKENS,
        "temperature": 0,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    t0 = time.perf_counter()
    ttft = None
    timing = {}
    usage = {}
    text = []
    with requests.post(BASE, json=body, stream=True, timeout=3600) as r:
        r.raise_for_status()
        for raw in r.iter_lines(decode_unicode=True):
            if not raw:
                continue
            if raw.startswith("data: "):
                raw = raw[6:]
            if raw.strip() == "[DONE]":
                break
            try:
                ev = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if ev.get("usage"):
                usage = ev["usage"]
            if ev.get("timings"):
                timing = ev["timings"]
            for ch in ev.get("choices", []):
                d = ch.get("delta") or {}
                if d.get("content") or d.get("reasoning_content"):
                    if ttft is None:
                        ttft = time.perf_counter() - t0
                    text.append(d.get("content") or "")
    total = time.perf_counter() - t0
    return {
        "target": target_tokens,
        "cache_n": timing.get("cache_n"),
        "prompt_n": timing.get("prompt_n"),
        "predicted_n": timing.get("predicted_n"),
        "prefill_tps": timing.get("prompt_per_second"),
        "decode_tps": timing.get("predicted_per_second"),
        "ttft_s": ttft,
        "total_s": total,
        "usage_prompt": usage.get("prompt_tokens"),
        "answer": "".join(text).strip()[:40],
    }


rows = []
for size, reps in SIZES.items():
    for rep in range(reps):
        try:
            r = run_once(size, seed=size * 7 + rep)
        except Exception as e:
            print(f"FAILED size={size} rep={rep}: {type(e).__name__} {e}", flush=True)
            continue
        rows.append(r)
        print(json.dumps(r), flush=True)

print("\n=== medians (engine timings) ===", flush=True)
head = f"{'target':>7} {'actual':>7} {'cached':>6} {'ttft_s':>7} {'prefill t/s':>12} {'decode t/s':>11}"
print(head, flush=True)
for size in SIZES:
    got = [r for r in rows if r["target"] == size and r["prefill_tps"]]
    if not got:
        print(f"{size:>7} {'-':>7} {'-':>6} {'-':>7} {'-':>12} {'-':>11}", flush=True)
        continue
    dec = [r["decode_tps"] for r in got if r["decode_tps"]]
    print(f"{size:>7} {statistics.median([r['prompt_n'] or 0 for r in got]):>7.0f} "
          f"{statistics.median([r['cache_n'] or 0 for r in got]):>6.0f} "
          f"{statistics.median([r['ttft_s'] for r in got]):>7.1f} "
          f"{statistics.median([r['prefill_tps'] for r in got]):>12.1f} "
          f"{(statistics.median(dec) if dec else 0):>11.1f}", flush=True)

with open(r"C:\AryaStrata\.sync-work\flint-bench-256k.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=1)
print("\nraw:", r"C:\AryaStrata\.sync-work\flint-bench-256k.json", flush=True)
