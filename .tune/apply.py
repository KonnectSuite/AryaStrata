"""Apply the tuned settings to strata-iq3_xxs.json, then validate every path it references."""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

CFG = Path(r"C:\AryaStrata\strata-iq3_xxs.json")
# (flag, value) — value None removes the flag
CHANGES = [
    ("--vram-reserve-mib", "1000"),   # 1792 -> 1000: expert cache 2189 -> 2703 slots, prefill +24%
    ("--spec-min-p", "0.50"),         # 0.70 -> 0.50: calibrate.py pick
    ("--adapt-swaps", "160"),         # 80 -> 160: calibrate.py pick, +4.3% on its adapt phase
    ("--max-context", "262144"),      # deliberately UNCHANGED: the user needs long context
]


def main() -> int:
    dry = "--dry-run" in sys.argv
    cfg = json.loads(CFG.read_text(encoding="utf-8-sig"))
    args: list = list(cfg["args"])

    if not dry:
        bak = CFG.with_name(CFG.name + ".pre-tune-" + time.strftime("%Y%m%d-%H%M%S"))
        shutil.copyfile(CFG, bak)
        print(f"backup: {bak.name}")

    changed = {}
    for flag, value in CHANGES:
        if flag in args:
            i = args.index(flag)
            old = args[i + 1] if i + 1 < len(args) else "(none)"
            if old == value:
                changed[flag] = f"unchanged {value}"
                continue
            args[i + 1] = value
            changed[flag] = f"{old} -> {value}"
        else:
            if value is None:
                changed[flag] = "absent"
                continue
            args.extend([flag, value])
            changed[flag] = f"(absent) -> {value}"

    dups = sorted({f for f in args if str(f).startswith("--") and args.count(f) > 1})
    print("changes:")
    for k, v in changed.items():
        print(f"  {k:<22} {v}")
    print(f"duplicate flags: {dups or 'none'}")

    cfg["args"] = args
    if dry:
        print("(dry run: not written)")
        return 0
    CFG.write_text(json.dumps(cfg, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")

    # validate
    cfg = json.loads(CFG.read_text(encoding="utf-8-sig"))
    refs = [x for x in cfg["args"] if isinstance(x, str) and x.startswith("C:\\")]
    refs += [cfg["tokenizer"], cfg["vision"]["mmproj"], cfg["vision"]["model"], cfg["exe"], *cfg["lib_dirs"]]
    missing = [p for p in refs if not Path(p).exists()]
    print(f"paths checked: {len(refs)}, missing: {missing or 'none'}")
    return 0 if not missing and not dups else 1


if __name__ == "__main__":
    raise SystemExit(main())
