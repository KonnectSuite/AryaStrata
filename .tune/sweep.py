"""Interleaved A/B sweep for Qwen3.8 Flash Next settings on this host.

Every arm needs a fresh engine (startup flags), so the run is organised as passes over the
whole arm list with the order alternating each pass: engine-to-engine drift lands on every arm
equally, and the median over passes decides - the same defence tools/calibrate.py uses, because
single decode measurements on this class of PC move several percent between engine starts.

    python sweep.py --arms arms.json --cases 2048:128,8192:32,32768:64 --passes 2
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(r"C:\AryaStrata")
sys.path.insert(0, str(ROOT / ".tune"))

import bench                                              # noqa: E402
from strata_tokenizer import Tokenizer                    # noqa: E402


def parse_cases(spec: str) -> list[tuple[int, int]]:
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        n, _, m = part.partition(":")
        out.append((int(n), int(m or 128)))
    return out


def run_pass(arms, cases, order, tok, results):
    for tag in order:
        arm = next(a for a in arms if a["tag"] == tag)
        ov = dict(arm.get("overrides") or {})
        ov.setdefault("--prompt-cache", "0")          # every read must be a real read
        base = bench.load_base()
        args = bench.apply_overrides(base["args"], ov)
        env_extra = arm.get("env") or {}
        try:
            eng = bench.Engine(args, f"{tag}", env_extra=env_extra)
        except Exception as exc:  # noqa: BLE001
            print(f"  [{tag}] engine did not start: {type(exc).__name__}: {exc}", flush=True)
            results.setdefault(tag, {"failed": str(exc)[:200]})
            continue
        row = results.setdefault(tag, {})
        row.setdefault("load_s", []).append(round(eng.load_s, 1))
        row.setdefault("slots", eng.info.get("expert_slots"))
        row.setdefault("vram_free", eng.info.get("vram_free_mib"))
        try:
            for n, max_new in cases:
                ids = bench.prompt_ids(tok, n, tag="sweep")
                m = eng.generate(ids, max_new)
                key = f"{n // 1024}k" if n >= 1024 else str(n)
                dec = m.get("decode_tok_s")
                pre = m.get("prefill_tok_s")
                acc = m.get("draft_accept")
                print(f"  [{tag:<14}] {key:>5}  pp {pre:>8.1f}  dec {dec:>7.2f}  "
                      f"accept {acc}  slots {eng.info.get('expert_slots')}", flush=True)
                cell = row.setdefault(key, {"dec": [], "pp": [], "acc": [], "ms": []})
                if dec:
                    cell["dec"].append(dec)
                if pre:
                    cell["pp"].append(pre)
                if acc is not None:
                    cell["acc"].append(acc)
                cell["ms"].append(m["decode_ms"])
        finally:
            eng.close()


def summarise(arms, results, cases):
    lines = []
    base = arms[0]["tag"]
    for n, _ in cases:
        key = f"{n // 1024}k" if n >= 1024 else str(n)
        lines.append(f"\n=== {key} ===")
        lines.append(f"{'arm':<16}{'decode tok/s':>14}{'vs base':>10}{'prefill tok/s':>15}{'accept':>8}{'slots':>7}")
        base_dec = None
        for arm in arms:
            tag = arm["tag"]
            row = results.get(tag) or {}
            cell = row.get(key) or {}
            if not cell.get("dec"):
                lines.append(f"{tag:<16}{'--':>14}")
                continue
            dec = statistics.median(cell["dec"])
            pre = statistics.median(cell["pp"]) if cell["pp"] else 0.0
            acc = statistics.median(cell["acc"]) if cell["acc"] else 0.0
            if tag == base:
                base_dec = dec
            delta = f"{(dec / base_dec - 1) * 100:+.1f}%" if base_dec else ""
            lines.append(f"{tag:<16}{dec:>14.2f}{delta:>10}{pre:>15.1f}{acc:>8.2f}"
                         f"{str(row.get('slots') or '-'):>7}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", required=True)
    ap.add_argument("--cases", default="2048:128,8192:32,32768:64")
    ap.add_argument("--passes", type=int, default=2)
    ap.add_argument("--out", default=None)
    ap.add_argument("--tokenizer", default=r"C:\AI\Strata-data\packs\iq3_xxs\tokenizer")
    a = ap.parse_args()

    arms = json.loads(Path(a.arms).read_text(encoding="utf-8"))
    cases = parse_cases(a.cases)
    tok = Tokenizer.from_dir(a.tokenizer)
    results: dict = {}
    t0 = time.monotonic()
    for p in range(a.passes):
        order = [x["tag"] for x in arms] if p % 2 == 0 else [x["tag"] for x in arms][::-1]
        print(f"\n########## pass {p + 1}/{a.passes}: {' -> '.join(order)}", flush=True)
        run_pass(arms, cases, order, tok, results)

    table = summarise(arms, results, cases)
    print(table, flush=True)
    out = Path(a.out) if a.out else ROOT / ".tune" / "results" / f"sweep-{int(time.time())}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"cases": cases, "passes": a.passes, "arms": arms,
                               "results": results, "table": table,
                               "minutes": round((time.monotonic() - t0) / 60, 1)}, indent=1),
                   encoding="utf-8")
    (out.with_suffix(".txt")).write_text(table, encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
