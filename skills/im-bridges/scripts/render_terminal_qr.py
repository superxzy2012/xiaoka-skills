#!/usr/bin/env python3
"""把日志里的终端二维码（█▀▄ 块字符，取最后一组）渲染成可扫的 PNG。
用法：render_terminal_qr.py <日志文件> [输出.png]
依赖 PIL。注意：终端 QR 是「亮块在深色背景」，PNG 必须黑块白底。
"""
import sys
from PIL import Image

logf = sys.argv[1]
outp = sys.argv[2] if len(sys.argv) > 2 else "wa-qr.png"
lines = open(logf).read().splitlines()
qr = [l for l in lines if l and set(l) <= set("█ ▄▀") and "█" in l]
if len(qr) < 34:
    sys.exit("no terminal QR found in log")
qr = qr[-34:]  # 只取最后一组（最新一版码）

# 半块渲染：每个字符列 1 像素宽，每行文本 2 像素高
grid = []
for r in qr:
    top, bot = [], []
    for ch in r:
        if ch == "█": top.append(1); bot.append(1)
        elif ch == "▀": top.append(1); bot.append(0)
        elif ch == "▄": top.append(0); bot.append(1)
        else: top.append(0); bot.append(0)
    grid.append(top); grid.append(bot)
h = len(grid); w = max(len(r) for r in grid)
for r in grid: r += [0] * (w - len(r))
while grid and not any(grid[-1]): grid.pop()

SCALE, PAD = 12, 4
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
