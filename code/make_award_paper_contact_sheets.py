"""为国奖论文逐页图像生成检索用联系表，不修改论文原件。"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"D:\数模工作流\state\award_visual_study")
SOURCES = {
    "2025_22C": ROOT / "render_2025_22C",
    "2024_68C": ROOT / "render_2024_68C",
    "C023": Path(r"D:\数模工作流\templates\award_papers\C023"),
    "C132": Path(r"D:\数模工作流\templates\award_papers\C132"),
}

try:
    FONT = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 18)
except OSError:
    FONT = ImageFont.load_default()

for label, source in SOURCES.items():
    output = ROOT / f"contacts_{label}"
    output.mkdir(exist_ok=True)
    pages = list(source.glob("*.jpg"))
    pages.sort(key=lambda p: int(''.join(ch for ch in p.stem.split('_')[-1] if ch.isdigit()) or p.stem.split('-')[-1]))
    batch_size, cols, rows = 10, 5, 2
    thumb_w, thumb_h, label_h, margin = 300, 424, 28, 16
    for start in range(0, len(pages), batch_size):
        batch = pages[start:start + batch_size]
        sheet = Image.new(
            "RGB",
            (margin + cols * (thumb_w + margin), margin + rows * (thumb_h + label_h + margin)),
            "#d7d7d7",
        )
        draw = ImageDraw.Draw(sheet)
        for i, page_path in enumerate(batch):
            row, col = divmod(i, cols)
            x = margin + col * (thumb_w + margin)
            y = margin + row * (thumb_h + label_h + margin)
            with Image.open(page_path) as image:
                page = image.convert("RGB")
                page.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (thumb_w, thumb_h), "white")
            canvas.paste(page, ((thumb_w - page.width) // 2, (thumb_h - page.height) // 2))
            sheet.paste(canvas, (x, y))
            draw.text((x + 5, y + thumb_h + 3), page_path.stem, fill="black", font=FONT)
        first_no = int(''.join(ch for ch in batch[0].stem.split('_')[-1] if ch.isdigit()) or batch[0].stem.split('-')[-1])
        last_no = int(''.join(ch for ch in batch[-1].stem.split('_')[-1] if ch.isdigit()) or batch[-1].stem.split('-')[-1])
        sheet.save(output / f"{label}_{first_no:02d}-{last_no:02d}.jpg", quality=92)
    print(label, len(pages), len(list(output.glob("*.jpg"))))
