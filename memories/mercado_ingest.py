#!/usr/bin/env python3
"""
B站美客多教程：下载音频 → 优先用B站自动字幕 / 否则 faster-whisper 转写 → 写入 Obsidian vault。
支持断点续跑（已有 transcript.txt + note.md 则跳过）。
"""
import json, os, re, subprocess, sys, time, datetime, html, hashlib

CK       = "/opt/data/memories/cookies/bilibili_cookies.txt"
BASE     = "/opt/data/cache/scratch/mercado"
VAULT    = "/opt/nas/volume2/2-AI/obsidian_vault/07-B站视频学习"
CAND     = "/opt/data/cache/scratch/mercado_sel.json"
LOG      = f"{BASE}/logs/run.log"
UA       = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36")
PY       = "/opt/data/.venv-browser/bin/python"
MODEL    = "small"          # 中文够用且快；large-v3-turbo 更准但慢 4 倍
MAX_SEC  = 60 * 90          # 单条上限 90 分钟，超了跳过

os.makedirs(f"{BASE}/audio", exist_ok=True)
os.makedirs(f"{BASE}/subs", exist_ok=True)
os.makedirs(f"{BASE}/logs", exist_ok=True)
os.makedirs(VAULT, exist_ok=True)

def log(msg):
    line = f"[{datetime.datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def slug(s, n=40):
    s = re.sub(r'[\\/:*?"<>|\r\n]+', "", s).strip()
    s = re.sub(r"\s+", "-", s)
    return s[:n] or "untitled"

def done(bvid):
    d = f"{BASE}/audio/{bvid}"
    return os.path.exists(f"{d}/transcript.txt") and os.path.exists(f"{d}/note.md")

def fetch_meta(bvid):
    """B站 view API 补元数据"""
    import urllib.request
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                            "Referer": f"https://www.bilibili.com/video/{bvid}"})
    ck = subprocess.run(["sed","-n","s/^[^\\t]*\\t\\t\\t\\t\\t\\t\\t\\t\\t\\t\\t*\\(.*\\)\\t.*/\\1/p",CK],
                        capture_output=True, text=True).stdout
    # 直接用 curl 更稳
    r = subprocess.run(["curl","-s","--noproxy","*","-m","20","-b",CK,
                        "-H",f"User-Agent: {UA}",
                        "-H",f"Referer: https://www.bilibili.com/video/{bvid}",
                        url], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        return d.get("data") or {}
    except Exception:
        return {}

def download(bvid):
    """下载音频 + 自动字幕"""
    d = f"{BASE}/audio/{bvid}"
    os.makedirs(d, exist_ok=True)
    cmd = [PY, "-m", "yt_dlp", "--ignore-config",
           "--cookies", CK,
           "--ffmpeg-location", "/usr/bin/ffmpeg",
           "-k",
           "--write-info-json", "--write-auto-subs", "--write-subs",
           "--sub-langs", "ai-zh,zh-Hans,zh-CN,zh-Hans-CN",
           "--skip-download",
           "-o", f"{d}/audio.%(ext)s",
           f"https://www.bilibili.com/video/{bvid}"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=400)
    ok_audio = any(f.endswith((".m4a",".mp3",".mp4",".opus")) for f in os.listdir(d)) \
               or os.path.exists(f"{d}/audio.m4a")
    # yt-dlp --skip-download 只下字幕；音频要单独 -x
    if not any(f.endswith((".m4a",".mp3")) for f in os.listdir(d)):
        cmd2 = [PY, "-m", "yt_dlp", "--ignore-config", "--cookies", CK,
                "--ffmpeg-location", "/usr/bin/ffmpeg", "-k",
                "-x", "--audio-format", "mp3",
                "-o", f"{d}/audio.%(ext)s",
                f"https://www.bilibili.com/video/{bvid}"]
        subprocess.run(cmd2, capture_output=True, text=True, timeout=600)
    subs = [f for f in os.listdir(d) if f.endswith((".srt",".vtt",".ass"))]
    auds = [f for f in os.listdir(d) if f.endswith((".m4a",".mp3",".opus",".wav"))]
    return bool(auds), subs

def srt_to_text(path):
    txt = open(path, encoding="utf-8", errors="ignore").read()
    lines = []
    for ln in txt.splitlines():
        ln = ln.strip()
        if not ln or "-->" in ln or ln.isdigit():
            continue
        lines.append(ln)
    return " ".join(lines)

def transcribe(bvid):
    """返回 (transcript, engine)"""
    d = f"{BASE}/audio/{bvid}"
    # 1) B站自动字幕优先
    for f in os.listdir(d):
        if f.endswith((".srt", ".vtt", ".ass")):
            t = srt_to_text(os.path.join(d, f))
            if len(t) > 200:
                return t, f"bili-subs({f})"
    # 2) faster-whisper
    aud = [f for f in os.listdir(d) if f.endswith((".m4a", ".mp3", ".opus", ".wav"))]
    if not aud:
        return "", "no-audio"
    ap = os.path.join(d, aud[0])
    outp = os.path.join(d, "whisper_out.txt")
    code = f'''
import os
os.environ["OMP_NUM_THREADS"]="4"
from faster_whisper import WhisperModel
m = WhisperModel("{MODEL}", device="cpu", compute_type="int8", cpu_threads=4)
segs, info = m.transcribe("{ap}", language="zh", beam_size=1, vad_filter=True)
with open("{outp}","w",encoding="utf-8") as f:
    for s in segs:
        f.write(s.text.strip()+"\\n")
print("OK", info.language)
'''
    r = subprocess.run([PY, "-c", code], capture_output=True, text=True, timeout=3000)
    if os.path.exists(outp) and os.path.getsize(outp) > 200:
        t = open(outp, encoding="utf-8").read().strip()
        return " ".join(t.splitlines()), "whisper-small"
    return "", f"whisper-fail:{r.stderr[-160:]}"

def write_note(bvid, meta, cand, transcript, engine):
    title = meta.get("title") or cand.get("title") or bvid
    title = html.unescape(re.sub(r"<[^>]+>", "", title))
    author = (meta.get("owner") or {}).get("name") or cand.get("author") or "?"
    mid    = (meta.get("owner") or {}).get("mid") or cand.get("mid") or ""
    pub    = meta.get("pubdate") or cand.get("pubdate") or 0
    dt     = datetime.datetime.utcfromtimestamp(pub).strftime("%Y-%m-%d") if pub else "?"
    dur    = meta.get("duration") or cand.get("duration") or "?"
    view   = (meta.get("stat") or {}).get("view") or cand.get("play") or 0
    fn = f"{dt}-{slug(title)}-{bvid}.md"
    fp = os.path.join(VAULT, fn)
    tags = ["B站视频学习", "美客多", "MercadoLibre", "跨境电商"]
    body = transcript.strip()
    # 正文放前 3000 字，完整版落同目录 .txt
    full_fp = os.path.join(BASE, "audio", bvid, "transcript.txt")
    try:
        os.makedirs(os.path.dirname(full_fp), exist_ok=True)
        open(full_fp, "w", encoding="utf-8").write(body)
    except Exception:
        pass
    md = f"""---
title: {title}
source: https://www.bilibili.com/video/{bvid}
platform: B站
bvid: {bvid}
author: {author}
author_mid: {mid}
published: {dt}
duration: {dur}
play: {view}
captured: {datetime.datetime.now().strftime("%Y-%m-%d")}
transcribe_engine: {engine}
tags: [{', '.join(tags)}]
---

# {title}

> UP主：**{author}** ｜ 发布：{dt} ｜ 时长：{dur} ｜ 播放：{view}
> 原视频：https://www.bilibili.com/video/{bvid}
> 转写方式：{engine}

## 内容摘要（供 agent 检索）

{body[:1500]}

## 完整转写

{body}

---
*本笔记由小卡自动采集转写，供其他 agent 学习使用。*
"""
    open(fp, "w", encoding="utf-8").write(md)
    return fp

def main():
    cands = json.load(open(CAND, encoding="utf-8"))
    total = len(cands)
    ok = fail = skip = 0
    errs = []
    for i, c in enumerate(cands, 1):
        bvid = c["bvid"]
        if done(bvid):
            skip += 1; continue
        dur = str(c.get("duration") or "0:0").split(":")
        try:
            secs = int(float(dur[-1])) + (int(float(dur[-2]))*60 if len(dur) > 1 else 0)
        except Exception:
            secs = 0
        if secs > MAX_SEC:
            log(f"[{i}/{total}] {bvid} 跳过(超长 {secs//60}m)"); skip += 1; continue
        try:
            log(f"[{i}/{total}] {bvid} 下载中... {c['title'][:34]}")
            has_audio, subs = download(bvid)
            t, engine = transcribe(bvid)
            if len(t) < 150:
                log(f"   ⚠️ 转写内容过短({len(t)}字) engine={engine}")
                fail += 1; errs.append((bvid, engine, len(t))); continue
            meta = fetch_meta(bvid)
            fp = write_note(bvid, meta, c, t, engine)
            log(f"   ✅ 入库 {os.path.basename(fp)} ({len(t)}字, {engine})")
            ok += 1
            # 清音频省空间
            for f in os.listdir(f"{BASE}/audio/{bvid}"):
                if f.endswith((".m4a", ".mp3", ".opus", ".wav")):
                    os.remove(os.path.join(f"{BASE}/audio/{bvid}", f))
        except Exception as e:
            log(f"   ❌ 失败: {type(e).__name__} {str(e)[:100]}")
            fail += 1; errs.append((bvid, str(e)[:100], 0))
        time.sleep(1.5)
    log(f"\n===== 完成: 成功{ok} 失败{fail} 跳过{skip} / 共{total} =====")
    if errs:
        log("失败清单:")
        for e in errs[:30]:
            log("   " + " | ".join(str(x) for x in e))
    json.dump(errs, open(f"{BASE}/errors.json","w"), ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()