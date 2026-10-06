#!/usr/bin/env python3
"""
B站美客多教程批量入库：下载音频 → 转写（优先B站字幕，其次云端 whisper-large-v3-turbo）→ 写 Obsidian 笔记。
断点续跑：已存在 note.md 即跳过。
"""
import json, os, re, subprocess, sys, time, datetime, html, threading

CK    = "/opt/data/memories/cookies/bilibili_cookies.txt"
BASE  = "/opt/data/cache/scratch/mercado"
VAULT = "/opt/nas/volume2/2-AI/obsidian_vault/07-B站视频学习"
CAND  = "/opt/data/cache/scratch/mercado_sel.json"
PY    = "/opt/data/.venv-browser/bin/python"
UA    = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
         "(KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36")
LOGF  = f"{BASE}/logs/run.log"
_lock = threading.Lock()

os.makedirs(f"{BASE}/audio", exist_ok=True)
os.makedirs(f"{BASE}/logs", exist_ok=True)
os.makedirs(VAULT, exist_ok=True)


def log(m):
    line = f"[{datetime.datetime.now():%H:%M:%S}] {m}"
    with _lock:
        print(line, flush=True)
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def slug(s, n=40):
    s = re.sub(r'[\\/:*?"<>|\r\n]+', "", s).strip()
    return re.sub(r"\s+", "-", s)[:n] or "untitled"


def note_path(bvid):
    for f in os.listdir(VAULT):
        if f.endswith(f"-{bvid}.md"):
            return os.path.join(VAULT, f)
    return None


def srt_to_text(p):
    out = []
    for ln in open(p, encoding="utf-8", errors="ignore"):
        ln = ln.strip()
        if not ln or "-->" in ln or ln.isdigit():
            continue
        out.append(ln)
    return " ".join(out)


def get_sub(bvid):
    """先试 B站自动字幕（免费且准）"""
    d = f"{BASE}/audio/{bvid}"
    cmd = [PY, "-m", "yt_dlp", "--ignore-config", "--cookies", CK,
           "--skip-download", "--write-auto-subs", "--write-subs",
           "--sub-langs", "ai-zh,zh-Hans,zh-CN",
           "-o", f"{d}/audio.%(ext)s",
           f"https://www.bilibili.com/video/{bvid}"]
    subprocess.run(cmd, capture_output=True, text=True, timeout=240)
    for f in os.listdir(d):
        if f.endswith((".srt", ".vtt", ".ass")):
            t = srt_to_text(os.path.join(d, f))
            if len(t) > 60:
                return t, f"bili-subs({f})"
    return "", ""


def get_audio(bvid):
    d = f"{BASE}/audio/{bvid}"
    os.makedirs(d, exist_ok=True)
    cmd = [PY, "-m", "yt_dlp", "--ignore-config", "--cookies", CK,
           "--ffmpeg-location", "/usr/bin/ffmpeg", "-k", "-x",
           "--audio-format", "mp3", "-o", f"{d}/audio.%(ext)s",
           f"https://www.bilibili.com/video/{bvid}"]
    subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    for f in os.listdir(d):
        if f.endswith((".mp3", ".m4a", ".opus", ".wav")):
            return os.path.join(d, f)
    return None


def cloud_transcribe(path):
    """复用 transcribe.py（已内置切片，超大文件不会 413）。
    transcribe.py 末尾输出格式: <正文>\n[via cloud/turbo 12.3s $0.000262]
    正文可能极短（短视频），故只要非空即接受。"""
    r = subprocess.run([PY, "/opt/data/memories/transcribe.py", path,
                        "--model", "turbo"], capture_output=True, text=True,
                       timeout=3000)
    raw = (r.stdout or "").strip()
    m = re.search(r"\[via ([^\]]+)\]", raw)
    engine = m.group(1) if m else "cloud/turbo"
    body = raw.split("[via")[0].strip()
    # 去掉可能混入的 [info]/[warn] 前缀行
    body = "\n".join(l for l in body.splitlines()
                     if not l.startswith(("[info]", "[warn]", "❌"))).strip()
    return body, engine


def fetch_meta(bvid):
    r = subprocess.run(["curl", "-s", "--noproxy", "*", "-m", "20", "-b", CK,
                        "-H", f"User-Agent: {UA}",
                        "-H", f"Referer: https://www.bilibili.com/video/{bvid}",
                        f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout).get("data") or {}
    except Exception:
        return {}


def write_note(bvid, meta, cand, text, engine):
    title = html.unescape(re.sub(r"<[^>]+>", "",
              meta.get("title") or cand.get("title") or bvid))
    author = (meta.get("owner") or {}).get("name") or cand.get("author") or "?"
    pub = meta.get("pubdate") or cand.get("pubdate") or 0
    dt = (datetime.datetime.fromtimestamp(pub, datetime.UTC).strftime("%Y-%m-%d")
          if pub else "?")
    dur = meta.get("duration") or cand.get("duration") or "?"
    view = (meta.get("stat") or {}).get("view") or cand.get("play") or 0
    body = text.strip()
    fn = f"{dt}-{slug(title)}-{bvid}.md"
    fp = os.path.join(VAULT, fn)
    md = f"""---
title: {title}
source: https://www.bilibili.com/video/{bvid}
platform: B站
bvid: {bvid}
author: {author}
published: {dt}
duration_sec: {dur}
play: {view}
captured: {datetime.datetime.now().strftime("%Y-%m-%d")}
transcribe_engine: {engine}
tags: [B站视频学习, 美客多, MercadoLibre, 跨境电商, 拉美电商]
---

# {title}

> UP主：**{author}** ｜ 发布：{dt} ｜ 时长：{dur}s ｜ 播放：{view}
> 原视频：https://www.bilibili.com/video/{bvid}
> 转写方式：{engine}

## 内容摘要（供 agent 快速检索）

{body[:1500]}

## 完整转写

{body}

---
*由小卡自动采集转写（{engine}），供其他 agent 学习使用。*
"""
    open(fp, "w", encoding="utf-8").write(md)
    return fp


def process(c, i, total):
    bvid = c["bvid"]
    if note_path(bvid):
        return "skip", 0
    d = f"{BASE}/audio/{bvid}"
    os.makedirs(d, exist_ok=True)
    try:
        # ① B站字幕
        t, eng = get_sub(bvid)
        src = "subs"
        if len(t) < 150:
            # ② 云端 turbo
            ap = get_audio(bvid)
            if not ap:
                return "fail", 0
            t, eng = cloud_transcribe(ap)
            src = "audio"
        if len(t) < 60:
            return "fail", 0
        meta = fetch_meta(bvid)
        fp = write_note(bvid, meta, c, t, eng)
        # 省空间：删音频
        if src == "audio":
            for f in os.listdir(d):
                if f.endswith((".mp3", ".m4a", ".opus", ".wav", ".mp4")):
                    try:
                        os.remove(os.path.join(d, f))
                    except OSError:
                        pass
        return "ok", len(t)
    except Exception as e:
        return f"fail:{type(e).__name__}", 0


def main():
    cands = json.load(open(CAND, encoding="utf-8"))
    total = len(cands)
    stat = {"ok": 0, "skip": 0, "fail": 0}
    errs = []
    t0 = time.time()
    for i, c in enumerate(cands, 1):
        st, n = process(c, i, total)
        stat["skip" if st == "skip" else ("ok" if st == "ok" else "fail")] += 1
        if st == "ok":
            log(f"[{i}/{total}] ✅ {c['bvid']} {n}字 | {c['title'][:36]}")
        elif st == "skip":
            log(f"[{i}/{total}] ⏭  已入库 {c['bvid']}")
        else:
            log(f"[{i}/{total}] ❌ {c['bvid']} {st} | {c['title'][:30]}")
            errs.append((c["bvid"], st, c.get("title", "")[:40]))
        if i % 10 == 0:
            el = time.time() - t0
            log(f"--- 进度 {i}/{total} 用时{el/60:.1f}min 剩{(el/i*(total-i))/60:.0f}min ---")
    log(f"===== 完成: 成功{stat['ok']} 跳过{stat['skip']} 失败{stat['fail']} / {total} "
        f"用时{(time.time()-t0)/60:.1f}min =====")
    json.dump(errs, open(f"{BASE}/errors.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()