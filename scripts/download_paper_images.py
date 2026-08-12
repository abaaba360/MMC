# -*- coding: utf-8 -*-
"""批量下载2025国赛B题获奖论文展示预览图（B060等）

图片来源：中国大学生在线 dxs.moe.gov.cn 论文展示页
图片托管在腾讯云 myqcloud.com，URL连续编号，可直接批量下载。
"""
import os
import sys
import urllib.request
import time

BASE_URL = "https://univs-news-1256833609.file.myqcloud.com/123/upload/resources/image/{}.jpg"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Referer": "https://dxs.moe.gov.cn/",
}


def download_paper(paper_id: str, first_image_id: int, total_pages: int, out_root: str):
    out_dir = os.path.join(out_root, paper_id)
    os.makedirs(out_dir, exist_ok=True)
    ok, fail = 0, []
    for page in range(1, total_pages + 1):
        img_id = first_image_id + page - 1
        url = BASE_URL.format(img_id)
        fname = f"{paper_id}_页面_{page:02d}.jpg"
        fpath = os.path.join(out_dir, fname)
        if os.path.exists(fpath) and os.path.getsize(fpath) > 1024:
            ok += 1
            continue
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            # 简单校验是JPEG
            if data[:2] != b"\xff\xd8":
                raise ValueError(f"非JPEG内容 ({len(data)} bytes)")
            with open(fpath, "wb") as f:
                f.write(data)
            ok += 1
            print(f"[{ok:3d}/{total_pages}] {fname}  {len(data)//1024} KB")
            time.sleep(0.2)  # 温和一点
        except Exception as e:
            fail.append((page, img_id, str(e)))
            print(f"[FAIL] 第{page}页 (id={img_id}): {e}")
    print(f"\n完成: {ok}/{total_pages} 成功, {len(fail)} 失败")
    if fail:
        for p, i, e in fail:
            print(f"  失败: 第{p}页 id={i} -> {e}")
    return len(fail) == 0


if __name__ == "__main__":
    out_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates", "award_papers")
    out_root = os.path.normpath(out_root)
    # B060: 第1页 image id = 10022785, 共72页
    download_paper("B060", 10022785, 72, out_root)
