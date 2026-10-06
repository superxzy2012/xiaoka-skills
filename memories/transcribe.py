#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小卡 · 音频转写路由器
主力：云端 whisper-large-v3-turbo（快、准、便宜）
兜底：本地 faster-whisper small（断网/云端故障时）

用法:
  python3 transcribe.py <音频路径> [--model turbo|qwen|whisper1|local] [--lang zh]
输出: 打印转写文本；退出码 0=成功
"""
import sys, os, json, time, argparse, subprocess, urllib.request, urllib.error

CONFIG = "/opt/data/config.yaml"
BASE = "http://192.168.199.2:20128/v1"
CLOUD_MODELS = {
    "turbo": "openrouter/openai/whisper-large-v3-turbo",   # 默认主力，最便宜
    "qwen":   "openrouter/qwen/qwen3-asr-flash-2026-02-10",  # 准确率最高
    "whisper1": "openrouter/openai/whisper-1",             # 贵，不推荐
}
VENV_PY = "/opt/data/.venv-browser/bin/python"


def get_key():
    """从 config.yaml 读 api_key（不硬编码）"""
    try:
        lines = open(CONFIG, encoding="utf-8").read().splitlines()
        in_block = False
        for i, ln in enumerate(lines):
            if ln.strip().startswith("custom:192-168-199-2-20128:"):
                in_block = True
                continue
            if in_block and "api_key:" in ln:
                v = ln.split("api_key:", 1)[1].strip().strip('"').strip("'")
                if v and "redacted" not in v:
                    return v
            if in_block and ln.strip().startswith("custom:") and "192-168-199-2-20128" not in ln:
                break
    except Exception as e:
        print(f"[warn] 读 config 失败: {e}", file=sys.stderr)
    env = os.environ.get("CUSTOM_192_168_199_2_20128_API_KEY") or os.environ.get("OMNIROUTE_API_KEY")
    return env


def to_wav16k(src, dst="/opt/data/cache/scratch/_rt.wav"):
    """任何格式 → 16k 单声道 wav（云端+本地都吃这个）"""
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", src,
                    "-ar", "16000", "-ac", "1", dst, "-y"], check=True, timeout=180)
    return dst


# 🔴 OpenRouter 单请求上限约 25MB（2026-10-05 实测：18MB mp3 转 41 分钟音频 → HTTP 413）。
# 超过就按 SEG_SEC 切片逐段转写再拼接。留足余量用 20MB 阈值。
MAX_UPLOAD = 20 * 1024 * 1024
SEG_SEC = 600          # 每段 10 分钟（16k 单声道 ≈ 19MB，安全）


def split_wav(wav):
    """按 SEG_SEC 切片，返回 [(路径, 起始秒)]；无需切片时返回 [(wav, 0)]"""
    size = os.path.getsize(wav)
    if size <= MAX_UPLOAD:
        return [(wav, 0)]
    outdir = "/opt/data/cache/scratch/_segs"
    os.makedirs(outdir, exist_ok=True)
    for f in os.listdir(outdir):
        os.remove(os.path.join(outdir, f))
    dur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", wav],
        capture_output=True, text=True, timeout=60).stdout.strip() or 0)
    n = int(dur // SEG_SEC) + 1
    segs = []
    for i in range(n):
        p = os.path.join(outdir, f"seg{i:03d}.wav")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error",
                        "-ss", str(i * SEG_SEC), "-t", str(SEG_SEC),
                        "-i", wav, "-ar", "16000", "-ac", "1", p, "-y"],
                       check=True, timeout=180)
        if os.path.getsize(p) > 1024:      # 跳过空段
            segs.append((p, i * SEG_SEC))
    return segs


def cloud(wav, model_key="turbo", lang="zh", retries=2):
    key = get_key()
    if not key:
        raise RuntimeError("拿不到 API key")
    model = CLOUD_MODELS[model_key]
    # 超大文件先切片（否则 413）
    segs = split_wav(wav)
    if len(segs) > 1:
        print(f"[info] 文件超 {MAX_UPLOAD//1024//1024}MB，切成 {len(segs)} 段逐段转写")
    buf, cost_sum, parts_n = [], 0.0, 0
    for seg_path, _ in segs:
        txt, info = _cloud_one(seg_path, model, key, lang, retries)
        buf.append(txt)
        parts_n += 1
        c = info.rsplit("$", 1)[-1] if "$" in info else "0"
        try:
            cost_sum += float(c)
        except ValueError:
            pass
    joined = " ".join(t.strip() for t in buf if t.strip())
    engine = f"cloud/{model_key}" + (f" x{parts_n}" if parts_n > 1 else "")
    return joined, f"{engine} ${cost_sum:.6f}"


def _cloud_one(wav, model, key, lang, retries):
    for attempt in range(1, retries + 1):
        try:
            # multipart/form-data 手写（避免依赖 requests）
            boundary = "----XiaokaBoundary7MA4YWxkTrZu0gW"
            with open(wav, "rb") as f:
                audio = f.read()
            parts = []
            def field(n, v):
                parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{n}"\r\n\r\n{v}\r\n'.encode())
            field("model", model)
            if lang:
                field("language", lang)
            parts.append(
                f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="a.wav"\r\n'
                f'Content-Type: audio/wav\r\n\r\n'.encode() + audio + b"\r\n")
            parts.append(f"--{boundary}--\r\n".encode())
            body = b"".join(parts)

            req = urllib.request.Request(
                f"{BASE}/audio/transcriptions", data=body, method="POST",
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": f"multipart/form-data; boundary={boundary}"})
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read().decode("utf-8"))
            txt = (d.get("text") or "").strip()
            cost = (d.get("usage") or {}).get("cost", 0)
            if txt:
                return txt, f"{time.time()-t0:.1f}s ${cost}"
            raise RuntimeError("云端返回空文本")
        except Exception as e:
            if attempt == retries:
                raise
            time.sleep(2)


def local(wav, lang="zh"):
    """本地 faster-whisper。av 库与新版冲突 → 走裸 PCM 路径"""
    pcm = "/opt/data/cache/scratch/_rt.pcm"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", wav,
                    "-f", "s16le", "-ar", "16000", "-ac", "1", pcm, "-y"],
                   check=True, timeout=120)
    code = (
        "import numpy as np\n"
        "from faster_whisper import WhisperModel\n"
        f"a=np.fromfile({pcm!r},dtype=np.int16).astype(np.float32)/32768.0\n"
        "m=WhisperModel('small',device='cpu',compute_type='int8')\n"
        f"s,i=m.transcribe(a,language={lang!r},beam_size=5)\n"
        "print(''.join(x.text for x in s))\n"
    )
    tmp = "/opt/data/cache/scratch/_rt.py"
    open(tmp, "w").write(code)
    env = dict(os.environ, HF_ENDPOINT="https://hf-mirror.com",
               HF_HOME="/opt/data/.cache/huggingface",
               OMP_NUM_THREADS="4")
    t0 = time.time()
    out = subprocess.run([VENV_PY, tmp], capture_output=True, text=True,
                         timeout=1800, env=env)
    if out.returncode != 0:
        raise RuntimeError(f"本地转写失败: {out.stderr[-300:]}")
    txt = out.stdout.strip()
    if not txt:
        raise RuntimeError("本地返回空文本")
    return txt, f"local/small {time.time()-t0:.1f}s"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--model", default="auto",
                    choices=["auto", "turbo", "qwen", "whisper1", "local"])
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if not os.path.exists(a.audio):
        print(f"❌ 文件不存在: {a.audio}", file=sys.stderr)
        return 1
    wav = to_wav16k(a.audio)
    order = ["turbo", "local"] if a.model == "auto" else [a.model]
    last = None
    for m in order:
        try:
            txt, meta = (local(wav, a.lang) if m == "local" else cloud(wav, m, a.lang))
            if a.json:
                print(json.dumps({"text": txt, "via": meta}, ensure_ascii=False))
            else:
                print(txt)
                print(f"[via {meta}]", file=sys.stderr)
            return 0
        except Exception as e:
            last = e
            print(f"[warn] {m} 失败: {e}", file=sys.stderr)
    print(f"❌ 全部转写方案失败，最后错误: {last}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
