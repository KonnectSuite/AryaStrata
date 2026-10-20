import os
from PIL import Image, ImageDraw, ImageFont

SRC = r"C:\AryaStrata\.bench-review\shots"
OUT = r"C:\AryaStrata\.bench-review\heroes-side-by-side.png"

items = [
    ("qwen38", "Qwen3.8 Flash Next", "IQ3_XXS"),
    ("gemma", "Gemma 4 26B-A4B", "Q4_K_M"),
    ("ornith", "Ornith1.5 35B-A3B", "Q8_0"),
    ("qwen36", "Qwen3.6 35B-A3B", "Q8_0"),
    ("minicpm", "MiniCPM 4.7 35B-A3B", "Q8_0"),
    ("lfm", "LFM2.5 24B-A2B", "Q8_0"),
]

TW, TH = 700, 438      # tile image size (1440x900 -> 700x437.5)
PAD = 14
LABEL_H = 34
COLS = 2
ROWS = 3
W = COLS * TW + (COLS + 1) * PAD
H = ROWS * (TH + LABEL_H) + (ROWS + 1) * PAD

canvas = Image.new("RGB", (W, H), (12, 14, 20))
draw = ImageDraw.Draw(canvas)

def font(sz, bold=False):
    for p in (r"C:\Windows\Fonts\seguisb.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
              r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()

f_title = font(21, True)
f_sub = font(15)

for i, (slug, name, quant) in enumerate(items):
    col, row = i % COLS, i // COLS
    x = PAD + col * (TW + PAD)
    y = PAD + row * (TH + LABEL_H + PAD)
    draw.text((x, y), name, font=f_title, fill=(235, 240, 255))
    draw.text((x + TW - 120, y + 6), quant, font=f_sub, fill=(120, 200, 200))
    src = os.path.join(SRC, f"{slug}-0-hero.png")
    im = Image.open(src).convert("RGB").resize((TW, TH), Image.LANCZOS)
    canvas.paste(im, (x, y + LABEL_H))
    draw.rectangle([x, y + LABEL_H, x + TW - 1, y + LABEL_H + TH - 1], outline=(45, 52, 70), width=2)

canvas.save(OUT, optimize=True)
print(OUT, canvas.size)
