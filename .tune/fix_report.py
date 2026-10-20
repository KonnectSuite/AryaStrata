"""Repair the report: undo the double-encoded UTF-8 (a PowerShell round-trip did it), drop the
embedded BOM, and rewrite one sloppy sentence. Repairs line by line and only where the corruption
pattern is present, so correct characters elsewhere are left alone."""
from pathlib import Path

P = Path(r"C:\AryaStrata\.tune\SETTINGS-REPORT.md")
raw = P.read_text(encoding="utf-8")
before_len = len(raw)

lines = raw.split("\n")
fixed_lines = []
repaired = skipped = 0
for line in lines:
    if "\u00e2\u20ac" in line:                     # 'â€' - the double-encoded marker
        try:
            fixed_lines.append(line.encode("latin-1").decode("utf-8"))
            repaired += 1
            continue
        except (UnicodeEncodeError, UnicodeDecodeError):
            skipped += 1
    fixed_lines.append(line)

text = "\n".join(fixed_lines)
text = text.replace("\ufeff", "")                    # embedded BOM from Add-Content

SLOPPY = (
    "  `max_context 262144`, reads 131K cold in 60 s, and reads a 200K conversation in 35.7 s because only ~71,000 of its\n"
    "  200,024 tokens were read fresh - ~129,000 came from the prompt cache (derived from the DONE line\n"
    "  reports: 2,000,024 ms? no - prompt_read 70,982 of prompt_tokens 200,024). A cold 256K read extrapolates to **~130 s**, then it\n"
    "  streams."
)
CLEAN = (
    "  `max_context 262144`, reads 131K cold in 60 s, and reads a 200K conversation in 35.7 s because\n"
    "  only 70,982 of its 200,024 tokens were read fresh - the other ~129,000 came out of the prompt\n"
    "  cache. A cold 256K read extrapolates to **~130 s**, then it streams."
)
sloppy_fixed = SLOPPY in text
text = text.replace(SLOPPY, CLEAN)

P.write_text(text, encoding="utf-8")
print(f"lines repaired: {repaired}, skipped: {skipped}")
print(f"sloppy sentence replaced: {sloppy_fixed}")
print(f"length {before_len} -> {len(text)}")
print(f"remaining double-encoded sequences: {text.count(chr(0x00e2) + chr(0x20ac))}")
print(f"remaining BOM chars: {text.count(chr(0xfeff))}")
print(f"em dashes now: {text.count(chr(0x2014))}, en dashes: {text.count(chr(0x2013))}")
