import sys, os
from PIL import Image

src = sys.argv[1]
out_prefix = sys.argv[2]
target_w = int(sys.argv[3]) if len(sys.argv) > 3 else 980
max_h = int(sys.argv[4]) if len(sys.argv) > 4 else 3000

im = Image.open(src).convert("RGB")
w, h = im.size
scale = target_w / w
new_w = target_w
new_h = int(h * scale)
im = im.resize((new_w, new_h), Image.LANCZOS)

# slice into chunks of at most max_h
n = max(1, (new_h + max_h - 1) // max_h)
step = (new_h + n - 1) // n
for i in range(n):
    top = i * step
    bot = min(new_h, top + step)
    if bot <= top:
        continue
    piece = im.crop((0, top, new_w, bot))
    p = f"{out_prefix}-{i+1}.png"
    piece.save(p)
    print(f"{p}  {piece.size[0]}x{piece.size[1]}  (source rows {int(top/scale)}-{int(bot/scale)})")
print(f"TOTAL source {w}x{h} -> {new_w}x{new_h}, {n} slices")
