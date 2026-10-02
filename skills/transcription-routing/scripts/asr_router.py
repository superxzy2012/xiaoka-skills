#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cloud-primary / local-fallback ASR router.

Design notes (the non-obvious parts):
  * Failure injection for the fallback path must break the NETWORK (unreachable base URL),
    not the credential -- some aggregators do not validate API keys and return 200 anyway.
  * Aggregator model ids usually need a "provider/model" prefix.
  * The local path bypasses the bundled audio decoder (ffmpeg -> raw PCM -> numpy) because
    faster-whisper's decoder can be built against an incompatible PyAV.

Usage:
    python3 asr_router.py <audio> [--primary turbo|qwen|whisper1] [--json]

Env:
    ASR_API_KEY, ASR_BASE_URL, ASR_MODEL_PREFIX
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

BASE = os.environ.get("ASR_BASE_URL", "http://127.0.0.1:8000/v1")
KEY = os.environ.get("ASR_API_KEY", "")
PREFIX = os.environ.get("ASR_MODEL_PREFIX", "openrouter/openai/")
MODELS = {
    "turbo": "whisper-large-v3-turbo",   # cheapest, small error rate
    "qwen": "qwen3-asr-flash-2026-02-10",  # highest accuracy, ~10x cost
    "whisper1": "whisper-1",              # most expensive
}
LOCAL_PY = os.environ.get("LOCAL_ASR_PYTHON", "python3")
LOCAL_MODEL = os.environ.get("LOCAL_ASR_MODEL", "small")


def to_wav(src, dst):
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", src,
         "-ar", "16000", "-ac", "1", dst, "-y"],
        check=True, timeout=300)
    return dst


def _multipart(fields, filepath):
    boundary = "----asr-router-boundary"
    out = []
    for k, v in fields.items():
        out.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    with open(filepath, "rb") as fh:
        out.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
            f'filename="audio.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode()
            + fh.read() + b"\r\n")
    out.append(f"--{boundary}--\r\n".encode())
    return b"".join(out), f"multipart/form-data; boundary={boundary}"


def cloud(wav, model_key, language="zh", retries=2):
    if not KEY:
        raise RuntimeError("ASR_API_KEY not set")
    model = PREFIX + MODELS[model_key]
    for attempt in range(retries):
        try:
            body, ctype = _multipart(
                {"model": model, "language": language} if language else {"model": model}, wav)
            req = urllib.request.Request(
                f"{BASE}/audio/transcriptions", data=body, method="POST",
                headers={"Authorization": f"Bearer {KEY}", "Content-Type": ctype})
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.loads(r.read().decode("utf-8"))
            text = (data.get("text") or "").strip()
            if not text:
                # Empty on a real clip means the model is not actually transcribing.
                raise RuntimeError("empty transcription")
            cost = (data.get("usage") or {}).get("cost", 0)
            return text, f"cloud/{model_key} {time.time()-t0:.1f}s cost={cost}"
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2)


def local(wav, language="zh"):
    """ffmpeg -> raw PCM -> numpy -> faster-whisper (avoids the broken decoder)."""
    with tempfile.TemporaryDirectory() as td:
        pcm = os.path.join(td, "a.pcm")
        script = os.path.join(td, "a.py")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", wav,
                        "-f", "s16le", "-ar", "16000", "-ac", "1", pcm, "-y"],
                       check=True, timeout=180)
        with open(script, "w") as fh:
            fh.write(
                "import numpy as np\n"
                "from faster_whisper import WhisperModel\n"
                f"a=np.fromfile({pcm!r},dtype=np.int16).astype(np.float32)/32768.0\n"
                f"m=WhisperModel({LOCAL_MODEL!r},device='cpu',compute_type='int8')\n"
                f"s,i=m.transcribe(a,language={language!r},beam_size=5)\n"
                "print(''.join(x.text for x in s))\n")
        t0 = time.time()
        r = subprocess.run([LOCAL_PY, script], capture_output=True, text=True,
                           timeout=3600,
                           env=dict(os.environ, OMP_NUM_THREADS="4"))
        if r.returncode != 0:
            raise RuntimeError(f"local failed: {r.stderr[-300:]}")
        text = (r.stdout or "").strip()
        if not text:
            raise RuntimeError("local returned empty text")
        return text, f"local/{LOCAL_MODEL} {time.time()-t0:.1f}s"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--primary", default="turbo", choices=list(MODELS))
    ap.add_argument("--no-fallback", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if not os.path.exists(a.audio):
        print(f"file not found: {a.audio}", file=sys.stderr)
        return 1

    tmpd = tempfile.mkdtemp()
    wav = to_wav(a.audio, os.path.join(tmpd, "a.wav"))

    chain = [a.primary] + ([] if a.no_fallback else ["local"])
    last = None
    for step in chain:
        try:
            text, meta = cloud(wav, step) if step in MODELS else local(wav)
            if a.json:
                print(json.dumps({"text": text, "via": meta}, ensure_ascii=False))
            else:
                print(text)
                print(f"[via {meta}]", file=sys.stderr)
            return 0
        except Exception as e:
            last = e
            print(f"[warn] {step} failed: {e}", file=sys.stderr)
    print(f"all backends failed: {last}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
