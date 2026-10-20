"""Rebuild the sweep table from its interleaved log (the results JSON is only written at the end,
so a crash loses it - the log always has the rows)."""
from __future__ import annotations

import re
import statistics
import sys
from pathlib import Path

ROW = re.compile(r"\[\s*(?P<tag>[^\]\s]+)\s*\]\s+(?P<case>\S+)\s+pp\s+(?P<pp>[\d.]+)\s+dec\s+(?P<dec>[\d.]+)")


def main() -> int:
    path = Path(sys.argv[1])
    raw = path.read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = raw.decode("utf-16")          # PowerShell Tee-Object writes UTF-16 on Windows
    else:
        text = raw.decode("utf-8", "replace")
    data: dict[str, dict[str, dict[str, list[float]]]] = {}
    order: list[str] = []
    for line in text.splitlines():
        m = ROW.search(line)
        if not m:
            continue
        tag, case = m["tag"], m["case"]
        if tag not in data:
            data[tag] = {}
            order.append(tag)
        cell = data[tag].setdefault(case, {"dec": [], "pp": []})
        cell["dec"].append(float(m["dec"]))
        cell["pp"].append(float(m["pp"]))

    base = "baseline"
    for case in ("2k", "8k", "32k"):
        print(f"\n=== {case} (n samples in brackets) ===")
        print(f"{'arm':<15}{'decode med':>12}{'vs base':>9}{'range':>18}{'prefill med':>13}{'vs base':>9}")
        bd = statistics.median(data.get(base, {}).get(case, {}).get("dec") or [0]) or None
        bp = statistics.median(data.get(base, {}).get(case, {}).get("pp") or [0]) or None
        ranked = []
        for tag in order:
            cell = data.get(tag, {}).get(case)
            if not cell or not cell["dec"]:
                continue
            d = statistics.median(cell["dec"])
            p = statistics.median(cell["pp"])
            ranked.append((d, tag, p, cell))
        for d, tag, p, cell in sorted(ranked, reverse=True):
            dd = f"{(d / bd - 1) * 100:+.1f}%" if bd else ""
            pd = f"{(p / bp - 1) * 100:+.1f}%" if bp else ""
            rng = f"{min(cell['dec']):.1f}-{max(cell['dec']):.1f}[{len(cell['dec'])}]"
            print(f"{tag:<15}{d:>12.2f}{dd:>9}{rng:>18}{p:>13.1f}{pd:>9}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
