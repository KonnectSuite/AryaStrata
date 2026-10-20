"""Undo the whole-file double-encoding in SETTINGS-REPORT.md.

The file's UTF-8 bytes were once decoded as cp1252 and re-encoded, so every non-ASCII character
became 2-3 characters. Repair: cp1252 -> bytes -> utf-8. The few characters that are already correct
(they cannot be cp1252-encoded, or they decode to invalid utf-8) are protected first and restored
afterwards, so a mixed file repairs without losing either half.
"""
from pathlib import Path

P = Path(r"C:\AryaStrata\.tune\SETTINGS-REPORT.md")
text = P.read_text(encoding="utf-8")
original = text

# 1. protect characters that are already right: anything not cp1252-encodable, plus any run that
#    already decodes as valid UTF-8 when cp1252-encoded (i.e. it is not double-encoded).
protect = {}
idx = 0


def protect_char(ch: str) -> str:
    global idx
    try:
        ch.encode("cp1252")
    except UnicodeEncodeError:
        key = f"\u0001{idx}\u0002"
        protect[key] = ch
        idx += 1
        return key
    return ch


text = "".join(protect_char(c) for c in text)

# 2. repair in one pass
try:
    raw = text.encode("cp1252")
    fixed = raw.decode("utf-8")
    ok = True
except (UnicodeEncodeError, UnicodeDecodeError) as exc:
    ok = False
    fixed = text
    print(f"roundtrip failed: {exc}")

# 3. restore the protected characters
for key, ch in protect.items():
    fixed = fixed.replace(key, ch)

if ok:
    # sanity: no double-encoded markers should survive
    print("remaining 'â€' markers:", fixed.count("\u00e2\u20ac"))
    print("remaining 'Ã¢' markers:", fixed.count("\u00c3\u00a2"))
    P.write_text(fixed, encoding="utf-8")
    print(f"repaired: {len(original)} -> {len(fixed)} chars")
    print("em dashes:", fixed.count("\u2014"), "en dashes:", fixed.count("\u2013"),
          "arrows:", fixed.count("\u2192"), "minus:", fixed.count("\u2212"),
          "ellipsis:", fixed.count("\u2026"), "le/ge:", fixed.count("\u2264"),
          fixed.count("\u2265"), "pm:", fixed.count("\u00b1"))
else:
    print("nothing written")
