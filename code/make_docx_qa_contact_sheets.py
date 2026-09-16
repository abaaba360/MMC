from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont


SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"D:\数模工作流\state\docx_qa_body_refs_final_v2")
OUTPUT = SOURCE / "contact_sheets"
OUTPUT.mkdir(exist_ok=True)

pages = sorted(SOURCE.glob("page-*.png"))
batch_size = 8
thumb_w = 420
thumb_h = 594
label_h = 32
cols = 4
rows = 2
margin = 20

try:
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 20)
except OSError:
    font = ImageFont.load_default()

for start in range(0, len(pages), batch_size):
    batch = pages[start:start + batch_size]
    sheet = Image.new(
        "RGB",
        (margin + cols * (thumb_w + margin), margin + rows * (thumb_h + label_h + margin)),
        "#d8d8d8",
    )
    draw = ImageDraw.Draw(sheet)
    for index, page_path in enumerate(batch):
        row, col = divmod(index, cols)
        x = margin + col * (thumb_w + margin)
        y = margin + row * (thumb_h + label_h + margin)
        with Image.open(page_path) as source:
            page = source.convert("RGB")
            page.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (thumb_w, thumb_h), "white")
            px = (thumb_w - page.width) // 2
            py = (thumb_h - page.height) // 2
            canvas.paste(page, (px, py))
        sheet.paste(canvas, (x, y))
        draw.text((x + 8, y + thumb_h + 4), page_path.stem, fill="black", font=font)
    first_no = int(batch[0].stem.split("-")[1])
    last_no = int(batch[-1].stem.split("-")[1])
    sheet.save(OUTPUT / f"pages-{first_no:03d}-{last_no:03d}.png", optimize=True)

print(f"created {len(list(OUTPUT.glob('*.png')))} contact sheets in {OUTPUT}")
