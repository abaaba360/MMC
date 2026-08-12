# -*- coding: utf-8 -*-
"""批量解析数模论文/截图 -> Markdown（文字+公式+图表色彩解读）

链路: 本地图片 → 智谱 GLM-4V-Flash(视觉模型) → image_parse_result.md → DeepSeek 主模型读取

相对原稿的修复:
1. 模型改用 glm-4v-flash（glm-4-flash 是纯文本模型，无视觉能力）
2. MIME 按文件后缀判断 (jpg->image/jpeg, png->image/png)
3. 避免粘贴引入的特殊连字符 (utf‑8 是 U+2011，会导致 LookupError)
4. 增强: 自动遍历 ROOT 下所有子文件夹、断点续传、页码过滤、限页保护
"""
import os
import re
import base64
import sys
import time
import requests

# ==========【请修改这里】==========
ROOT = r"D:\数模工作流\templates\award_papers"   # 论文根目录(自动遍历 B060/B157 等子文件夹)
OUTPUT_NAME = "image_parse_result.md"             # 每个子文件夹下输出的 md 文件名
ZHIPU_API_KEY = "填入你的智谱API-KEY"             # https://open.bigmodel.cn/ 控制台创建
MODEL_NAME = "glm-4v-flash"                       # 免费视觉模型; 需更精准可换 glm-4v-plus(付费)
MAX_IMAGES = 200                                  # 单文件夹最多解析页数(防止误跑全量)
PAGES_FILTER = None                               # 例 "1-15,42" 只解析这些页; None=全部
# ==================================

API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
HEADERS = {"Authorization": f"Bearer {ZHIPU_API_KEY}", "Content-Type": "application/json"}

PROMPT = """仔细解析这张数模论文截图：
1. 完整提取图中所有文字、公式、表格数据，数学公式尽量用LaTeX还原；
2. 如果是图表(折线图、热力图、干涉彩图、等高图等)：
   - 说明每种颜色/色块代表的数据含义；
   - 颜色深浅对应的物理量大小，干涉彩色图样描述色彩变化规律；
3. 结合数模论文场景解读图表信息；
4. 输出条理清晰，不要简略；
不要只做简单OCR，完整还原图片携带的图表信息。"""

MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


def parse_filter(fs):
    """把 '1-15,42' 解析成页码集合"""
    if not fs:
        return None
    pages = set()
    for part in fs.replace("，", ",").split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            pages.update(range(int(a), int(b) + 1))
        elif part:
            pages.add(int(part))
    return pages


def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def page_no(fname):
    m = re.search(r"_(\d+)\.", fname)
    return int(m.group(1)) if m else -1


def parse_one(img_path):
    ext = os.path.splitext(img_path)[1].lower()
    mime = MIME.get(ext, "image/jpeg")
    b64 = encode_image(img_path)
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]}],
    }
    r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=120)
    rj = r.json()
    try:
        return rj["choices"][0]["message"]["content"]
    except Exception:
        return f"解析失败：{rj}"


def main():
    if not os.path.isdir(ROOT):
        sys.exit(f"文件夹不存在: {ROOT}")
    if "填入你的" in ZHIPU_API_KEY:
        sys.exit("请先在脚本顶部填入 ZHIPU_API_KEY")
    filter_pages = parse_filter(PAGES_FILTER)
    done_total = 0

    for folder in sorted(os.listdir(ROOT)):
        fdir = os.path.join(ROOT, folder)
        if not os.path.isdir(fdir):
            continue
        out_md = os.path.join(fdir, OUTPUT_NAME)

        # 断点续传: 收集已解析文件名
        done = set()
        if os.path.exists(out_md):
            with open(out_md, encoding="utf-8") as f:
                for line in f:
                    m = re.match(r"^## 文件名称：(.+)$", line.strip())
                    if m:
                        done.add(m.group(1).strip())

        imgs = sorted(f for f in os.listdir(fdir)
                      if os.path.splitext(f)[1].lower() in MIME)
        if filter_pages is not None:
            imgs = [f for f in imgs if page_no(f) in filter_pages]
        imgs = imgs[:MAX_IMAGES]
        pending = [f for f in imgs if f not in done]
        if not pending:
            print(f"[{folder}] 无新增，跳过")
            continue

        print(f"[{folder}] 待解析 {len(pending)} 页")
        with open(out_md, "a", encoding="utf-8") as f:
            if os.path.getsize(out_md) == 0:
                f.write(f"# 图片解析汇总：{folder}\n\n")
            for i, fname in enumerate(pending, 1):
                img_path = os.path.join(fdir, fname)
                print(f"  [{i}/{len(pending)}] {fname} ...", flush=True)
                try:
                    reply = parse_one(img_path)
                except Exception as e:
                    reply = f"解析异常: {e}"
                f.write(f"## 文件名称：{fname}\n{reply}\n\n")
                f.flush()
                done_total += 1
                time.sleep(0.3)

    print(f"\n完成，本次新增解析 {done_total} 张图片")


if __name__ == "__main__":
    main()
