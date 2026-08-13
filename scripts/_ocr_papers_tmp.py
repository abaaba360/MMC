# -*- coding: utf-8 -*-
"""临时OCR脚本：批量识别两篇扫描论文并输出txt（按页顺序，含页码标记）。"""
import os
import sys
import time

from rapidocr_onnxruntime import RapidOCR

BASE = r"D:\数模工作流\state\agent_outputs"
JOBS = [
    ("att1_25", "qA_scanned_images/att1_25", 36, "qA_papers/att1_25.txt"),
    ("att2_2-8", "qA_scanned_images/att2_2-8", 43, "qA_papers/att2_2-8.txt"),
]


def sort_lines(result):
    """按阅读顺序排序OCR结果：先按纵坐标，再按横坐标。"""
    if not result:
        return []
    items = []
    for box, text, score in result:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        items.append((min(ys), min(xs), text))
    items.sort(key=lambda t: (round(t[0] / 12), t[1]))
    return [t[2] for t in items]


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    engine = RapidOCR(use_angle_cls=False)

    for name, subdir, npages, outrel in JOBS:
        if which != "all" and which != name:
            continue
        img_dir = os.path.join(BASE, subdir)
        out_path = os.path.join(BASE, outrel)
        parts = []
        total_chars = 0
        for i in range(1, npages + 1):
            img = os.path.join(img_dir, "p%02d.png" % i)
            t0 = time.time()
            result, _ = engine(img)
            lines = sort_lines(result)
            # 过滤低置信度噪点行（纯空白/极短符号）
            page_text = "\n".join(lines)
            nchars = len(page_text)
            total_chars += nchars
            block = "[第%d页]\n%s" % (i, page_text.strip())
            parts.append(block)
            dt = time.time() - t0
            print("%s p%02d: %d lines, %d chars, %.1fs" % (name, i, len(lines), nchars, dt), flush=True)
        full = "\n\n".join(parts) + "\n"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(full)
        print("==> wrote %s  (%d chars total)" % (out_path, total_chars), flush=True)


if __name__ == "__main__":
    main()
