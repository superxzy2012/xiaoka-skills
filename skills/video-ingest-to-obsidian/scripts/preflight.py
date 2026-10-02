#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""短视频入库管线预检

在向用户承诺「能入库」之前跑这个。共享库的入库技能是别的机器写的，
脚本路径在本机可能不存在；本预检把依赖状态摊开，避免边做边发现。

退出码： 0=齐备  1=可降级（无登录态，走免登录下载器）  2=阻断（需先补依赖）
"""
import os, shutil, subprocess, sys

SHARED = "/opt/nas/volume2/2-AI/skills"
SCRATCH = os.environ.get("TMPDIR", "/opt/data/cache/scratch")
INGEST_SKILLS = [
    "video-downloader",          # 单条无水印（第三方 API，免登录）
    "douyin-video-downloader",   # 批量拉账号作品
    "douyin-bilibili-ingest",    # 入库规范权威版
    "douyin-obsidian",
    "douyin-kb-feed",
]

rows, blockers = [], []

def add(name, state, detail, blocking=False):
    rows.append((name, state, detail))
    if blocking:
        blockers.append(f"{name}: {detail}")

# 1. 媒体工具
for tool, args in (("ffmpeg", ["-version"]), ("ffprobe", ["-version"])):
    if shutil.which(tool):
        add(tool, "OK", shutil.which(tool))
    else:
        add(tool, "缺失", "音视频处理依赖，缺失则无法抽音频/截帧", blocking=True)

# 2. 下载器
found = [s for s in INGEST_SKILLS if os.path.isdir(os.path.join(SHARED, s))]
if found:
    add("下载器技能", "OK", f"{len(found)} 个: {', '.join(found)}")
else:
    add("下载器技能", "缺失", f"共享库 {SHARED} 未挂载或无入库技能", blocking=True)

# 3. 转录后端（重点：缺它就出不了真实转录稿）
asr = []
for mod in ("faster_whisper", "whisper", "funasr"):
    r = subprocess.run([sys.executable, "-c", f"import {mod}"],
                       capture_output=True, timeout=60)
    if r.returncode == 0:
        asr.append(mod)
if asr:
    add("转录后端", "OK", f"本地可导入: {', '.join(asr)}")
else:
    add("转录后端", "缺失",
        "无本地 ASR。补装: uv pip install faster-whisper（首次运行会下模型）。"
        "没有真实转录就不得入库（铁律 1）", blocking=True)

# 4. yt-dlp（裸连抖音会被 412，仅作参考）
add("yt-dlp", "OK" if shutil.which("yt-dlp") else "未安装",
    "共享下载器已处理登录态；裸 yt-dlp 直连抖音易 412 风控")

# 5. 登录态（决定是否需要扫码）
cookie_candidates = []
for root in (os.path.join(SHARED, "..",), "/opt/data", SCRATCH):
    try:
        for dirpath, _, files in os.walk(root):
            for f in files:
                if f.endswith((".txt", ".json")) and "cookie" in f.lower():
                    cookie_candidates.append(os.path.join(dirpath, f))
            if len(cookie_candidates) > 12:
                break
    except (OSError, PermissionError):
        pass
if cookie_candidates:
    add("登录态", "OK", f"发现 {len(cookie_candidates)} 个候选 cookie 文件")
else:
    add("登录态", "缺失", "无抖音登录态；游客态下载会报 Fresh cookies needed，需扫码")

# 6. 浏览器（扫码登录依赖）
browser = next((b for b in ("chromium", "chromium-browser", "google-chrome", "brave")
                if shutil.which(b)), None)
if browser:
    add("浏览器", "OK", browser)
else:
    add("浏览器", "缺失",
        "扫码登录需 Chromium: uv venv .venv-browser && "
        "uv pip install playwright && python -m playwright install chromium")

# 7. 落盘目录
try:
    os.makedirs(SCRATCH, exist_ok=True)
    add("暂存目录", "OK", SCRATCH)
except OSError as e:
    add("暂存目录", "不可写", f"{SCRATCH}: {e}", blocking=True)

w = max(len(r[0]) for r in rows)
print("短视频入库管线预检")
print("=" * (w + 34))
for name, state, detail in rows:
    icon = {"OK": "OK  ", "缺失": "MISS", "未安装": "WARN"}.get(state, "WARN")
    print(f"{name:<{w}}  [{icon}] {detail}")
print("=" * (w + 34))
if blockers:
    print(f"阻断 {len(blockers)} 项 —— 先补齐再向用户承诺入库：")
    for b in blockers:
        print(f"  - {b}")
    sys.exit(2)
missing = [r[0] for r in rows if r[1] in ("缺失", "未安装")]
if missing:
    print(f"可降级：{', '.join(missing)} 缺失。免登录下载器可先跑，转录需扫码登录。")
    sys.exit(1)
print("齐备，可直接入库。")
sys.exit(0)
