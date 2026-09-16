from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


SRC = Path(r"D:\数模工作流\state\docx_render_qa\visual_enhanced_v1_word")
OUT = SRC / "contact_sheets"
OUT.mkdir(parents=True, exist_ok=True)

pages = sorted(SRC.glob("page-*.png"), key=lambda p: int(p.stem.split("-")[-1]))
font = ImageFont.load_default()
for batch_start in range(0, len(pages), 10):
    batch = pages[batch_start:batch_start + 10]
    thumb_w, thumb_h = 360, 510
    sheet = Image.new("RGB", (thumb_w * 5, (thumb_h + 26) * 2), "#d9d9d9")
    draw = ImageDraw.Draw(sheet)
    for j, path in enumerate(batch):
        image = Image.open(path).convert("RGB")
        image.thumbnail((thumb_w - 10, thumb_h - 10))
        x = (j % 5) * thumb_w + (thumb_w - image.width) // 2
        y = (j // 5) * (thumb_h + 26) + 20
        sheet.paste(image, (x, y))
        draw.text((j % 5 * thumb_w + 8, j // 5 * (thumb_h + 26) + 3), path.stem, fill="black", font=font)
    out = OUT / f"pages_{batch_start + 1:03d}_{batch_start + len(batch):03d}.png"
    sheet.save(out, dpi=(150, 150))
print(f"pages={len(pages)} sheets={len(list(OUT.glob('*.png')))} out={OUT}")
