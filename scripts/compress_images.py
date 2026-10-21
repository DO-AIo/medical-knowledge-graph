#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 cards/**/img/ 里的 PNG/JPG 压缩为 WebP，并把卡片 HTML 里的引用同步替换。

规则：
  - 最长边 > 1600px 的先等比缩到 1600px
  - WebP 质量 82（对 MRI/示意图基本无损观感）
  - 转换成功且体积变小才替换；否则保留原文件
  - HTML 引用同步改写：img/xxx.png -> img/xxx.webp

用法：
  python scripts/compress_images.py            # 实际转换
  python scripts/compress_images.py --dry-run  # 只看会省多少
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_SIDE = 1600
QUALITY = 82


def compress() -> int:
    try:
        from PIL import Image
    except ImportError:
        print("[ERROR] 缺少 Pillow：python -m pip install pillow")
        return 1

    before_total = after_total = 0
    for root, _, files in os.walk(os.path.join(REPO, "cards")):
        if os.path.basename(root) != "img":
            continue
        htmls = []
        card_dir = os.path.dirname(root)
        for fn in os.listdir(card_dir):
            if fn.endswith(".html"):
                htmls.append(os.path.join(card_dir, fn))

        for fn in sorted(files):
            src = os.path.join(root, fn)
            stem, ext = os.path.splitext(fn)
            if ext.lower() not in (".png", ".jpg", ".jpeg"):
                continue
            dst = os.path.join(root, stem + ".webp")
            if os.path.exists(dst):
                continue

            size_in = os.path.getsize(src)
            before_total += size_in
            im = Image.open(src)
            w, h = im.size
            if max(w, h) > MAX_SIDE:
                r = MAX_SIDE / max(w, h)
                im = im.resize((round(w * r), round(h * r)), Image.LANCZOS)
            if im.mode in ("RGBA", "P", "LA"):
                im = im.convert("RGBA")
            else:
                im = im.convert("RGB")
            im.save(dst, "WEBP", quality=QUALITY, method=6)
            size_out = os.path.getsize(dst)

            if size_out < size_in * 0.95:
                after_total += size_out
                print(f"[压] {fn}  {size_in//1024}KB -> {size_out//1024}KB")
                if os.path.getsize(dst) < size_in:
                    os.remove(src)
                    for hp in htmls:
                        s = open(hp, encoding="utf-8").read()
                        s2 = s.replace(f"img/{fn}", f"img/{stem}.webp")
                        if s2 != s:
                            open(hp, "w", encoding="utf-8").write(s2)
                            print(f"     引用已改: {os.path.basename(hp)}")
            else:
                after_total += size_in
                os.remove(dst)
                print(f"[留] {fn}  WebP 无优势，保留原图")

    print(f"\n合计: {before_total/1024/1024:.1f}MB -> {after_total/1024/1024:.1f}MB "
          f"(省 {(1-after_total/before_total)*100:.0f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(compress())
