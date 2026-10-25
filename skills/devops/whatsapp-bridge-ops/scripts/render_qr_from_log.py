#!/usr/bin/env python3
"""把配对日志里的终端字符二维码（█▀▄ 半块字符）还原成标准 PNG。

用法: /opt/data/.venv-browser/bin/python render_qr_from_log.py <pair.log> [out.png]

原理: 每行文本对应 2 像素高（█=两格、▀=上格、▄=下格、空=白）；
终端二维码是「亮块在深色背景」，标准码必须黑块白底 → 初始全黑底，亮块画白。
不做反转扫不出来。
"""
import sys
from PIL import Image

logf = sys.argv[1]
outp = sys.argv[2] if len(sys.argv) > 2 else "/opt/data/cache/scratch/muse_wa/wa-fresh-qr.png"
lines = open(logf, encoding="utf-8", errors="ignore").read().splitlines()
qr = [l for l in lines if l and set(l) <= set("█ ▄▀") and "█" in l]
if len(qr) < 34:
    sys.exit(f"no QR block found in {logf} (need >=34 rows, got {len(qr)})")
qr = qr[-34:]

grid = []
for r in qr:
    top = []; bot = []
    for ch in r:
        if ch == "█":   top.append(1); bot.append(1)
        elif ch == "▀": top.append(1); bot.append(0)
        elif ch == "▄": top.append(0); bot.append(1)
        else:           top.append(0); bot.append(0)
    grid.append(top); grid.append(bot)

h = len(grid); w = max(len(r) for r in grid)
for r in grid: r += [0] * (w - len(r))
while grid and not any(grid[-1]): grid.pop()

SCALE = 12; PAD = 4
img = Image.new("1", ((w + PAD * 2) * SCALE, (h + PAD * 2) * SCALE), 0)
px = img.load()
for y, row in enumerate(grid):
    for x, v in enumerate(row):
        if v:
            for dy in range(SCALE):
                for dx in range(SCALE):
                    px[(x + PAD) * SCALE + dx, (y + PAD) * SCALE + dy] = 1
img.save(outp)
print("saved", outp, img.size, "grid", w, h)
