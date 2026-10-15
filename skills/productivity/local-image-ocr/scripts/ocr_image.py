#!/usr/bin/env python3
"""本地 OCR 读图 —— 读用户发来的截图/图片里的文字。

用法:
    /opt/data/.venv-browser/bin/python ocr_image.py <图片路径> [--crop L T R B] [--scale 2]

依赖: rapidocr_onnxruntime + opencv-python-headless
      若报 libGL.so.1 缺失 -> 见 SKILL.md「坑一」。
"""
import argparse
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--crop", nargs=4, type=float, metavar=("L", "T", "R", "B"),
                    help="裁剪区域，取值为 0~1 的比例（放大重跑小字时用）")
    ap.add_argument("--scale", type=float, default=1.0, help="裁剪后放大倍数，默认 1")
    ap.add_argument("--raw", action="store_true", help="按识别顺序输出，不重排版面")
    args = ap.parse_args()

    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as e:
        print(f"rapidocr 不可用: {e}", file=sys.stderr)
        print("若为 libGL.so.1 缺失，按 SKILL.md 把 opencv-python 换成 opencv-python-headless",
              file=sys.stderr)
        return 2

    src = args.image
    if args.crop:
        from PIL import Image
        im = Image.open(src)
        w, h = im.size
        left, top, right, bottom = args.crop
        im = im.crop((int(w * left), int(h * top), int(w * right), int(h * bottom)))
        if args.scale != 1.0:
            im = im.resize((int(im.width * args.scale), int(im.height * args.scale)))
        src = "/tmp/_ocr_crop.png"
        im.save(src)

    ocr = RapidOCR()
    res, _ = ocr(src)
    if not res:
        print("NO TEXT DETECTED")
        return 1

    # 版面重排：多栏界面不排序会串行错乱
    items = res if args.raw else sorted(res, key=lambda r: (int(r[0][0][1]) // 12, int(r[0][0][0])))
    print(f"detected {len(items)} lines:\n")
    for box, txt, _score in items:
        print(f"[y={int(box[0][1]):5d} x={int(box[0][0]):5d}] {txt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
