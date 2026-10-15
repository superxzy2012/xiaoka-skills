#!/usr/bin/env python3
"""本地 OCR 读图 —— 视觉模型不可用时读出图片/截图里的文字。

用法:
    /opt/data/.venv-browser/bin/python read_image_text.py <图片路径> [--raw]

飞书发来的图片落在 /opt/data/cache/images/img_*.jpg。
默认按版面排序输出（先 y 行再 x 列），能还原侧边栏菜单 + 主区域 + 错误提示的相对位置；
--raw 保留 OCR 原始顺序。

依赖（已装在 /opt/data/.venv-browser）: rapidocr-onnxruntime + opencv-python-headless。
若报 `libGL.so.1: cannot open shared object file`，说明装的是需要 GUI 库的 opencv-python，
换成 headless 版即可（不需要 apt / root）：

    UV=/opt/hermes/tools/uv-0.12.3-linux-x64/uv
    $UV pip uninstall --python /opt/data/.venv-browser/bin/python opencv-python
    $UV pip install --python /opt/data/.venv-browser/bin/python opencv-python-headless
"""
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    raw = "--raw" in sys.argv

    from rapidocr_onnxruntime import RapidOCR

    res, _ = RapidOCR()(path)
    if not res:
        print("NO TEXT DETECTED")
        return 1

    print(f"detected {len(res)} lines:\n")
    items = res if raw else sorted(res, key=lambda r: (int(r[0][0][1]) // 12, int(r[0][0][0])))
    for box, txt, _score in items:
        print(f"[y={int(box[0][1]):5d} x={int(box[0][0]):5d}] {txt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
