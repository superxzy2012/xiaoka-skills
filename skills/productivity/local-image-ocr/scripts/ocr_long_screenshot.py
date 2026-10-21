#!/usr/bin/env python3
"""超长截图 OCR：按高度切段 → 视觉模型逐段转录 → 按序拼回 Markdown。

用法:
    ocr_long_screenshot.py <图片> [-o out.md] [--seg-h 1500] [--overlap 60]
                          [--model NAME] [--base URL] [--prompt TEXT]
                          [--env-file ~/.hermes/.env]

为什么不能缩图:
    1260x24284 缩到长边 1600 只剩 83px 宽，文字全毁。宽度承载文字，只能切高度。

为什么必须后台跑:
    17 段约 15 分钟。前台 420s 硬超时会把它掐死，日志里只剩「段 1」，
    看起来像卡住，其实只是没跑完。用 background=True + timeout 900 以上。

凭据:
    key  依次取 OCR_API_KEY / OMNIROUTE_API_KEY / OPENROUTER_API_KEY
    base 取 OCR_BASE / OMNIROUTE_BASE，默认 https://openrouter.ai/api/v1
    --env-file 指定的文件会先被加载（setdefault，不覆盖已有环境变量）。
    不要把 key 写进命令行或本脚本 —— 它只从环境读。
"""
import argparse
import base64
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_PROMPT = (
    "逐字抄出这张图里的全部文字，保持原有的换行和先后顺序。"
    "不要总结、不要解释、不要补全、不要加评论。看不清的字用 [?] 代替。"
)


def load_env_file(path):
    if not path or not os.path.exists(path):
        return
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def first_env(*names, default=None):
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    return default


def segment(img, seg_h, overlap):
    """按高度切段，保持原始宽度。返回 [(index, top, bottom, jpeg_bytes)]"""
    w, h = img.size
    step = max(seg_h - overlap, 1)
    out = []
    top = 0
    idx = 0
    while top < h:
        bottom = min(top + seg_h, h)
        band = img.crop((0, top, w, bottom))
        buf = io.BytesIO()
        band.save(buf, format="JPEG", quality=88)
        out.append((idx, top, bottom, buf.getvalue()))
        idx += 1
        if bottom >= h:
            break
        top += step
    return out


def ask(base, key, model, prompt, jpeg, timeout=180, retries=2):
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {
                    "url": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()}},
            ],
        }],
        "max_tokens": 4000,
        "temperature": 0,
    }
    body = json.dumps(payload).encode()
    url = base.rstrip("/") + "/chat/completions"
    last = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + key},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"] or ""
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:300]
            last = "HTTP %s: %s" % (exc.code, detail)
        except Exception as exc:  # noqa: BLE001 - 逐段容错，不中断整批
            last = "%s: %s" % (type(exc).__name__, exc)
        if attempt < retries:
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(last)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--seg-h", type=int, default=1500)
    ap.add_argument("--overlap", type=int, default=60)
    ap.add_argument("--model", default=None)
    ap.add_argument("--base", default=None)
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--env-file", default=None)
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()

    load_env_file(args.env_file)
    key = first_env("OCR_API_KEY", "OMNIROUTE_API_KEY", "OPENROUTER_API_KEY")
    base = args.base or first_env("OCR_BASE", "OMNIROUTE_BASE",
                                  default="https://openrouter.ai/api/v1")
    model = args.model or first_env("OCR_MODEL",
                                    default="nvidia/nemotron-3.5-super-vl:free")
    if not key:
        sys.exit("缺少 API key：设置 OCR_API_KEY / OMNIROUTE_API_KEY / OPENROUTER_API_KEY，"
                 "或用 --env-file 指向 env 文件")

    from PIL import Image  # 延迟导入，缺包时报错更清楚
    img = Image.open(args.image).convert("RGB")
    w, h = img.size
    bands = segment(img, args.seg_h, args.overlap)
    print("# %dx%d -> %d 段 (seg_h=%d overlap=%d)" % (w, h, len(bands), args.seg_h, args.overlap),
          file=sys.stderr)

    parts = []
    for idx, top, bottom, jpeg in bands:
        t0 = time.time()
        try:
            text = ask(base, key, model, args.prompt, jpeg, timeout=args.timeout)
            tag = ""
        except Exception as exc:  # noqa: BLE001
            text = ""
            tag = "   [FAILED %s]" % exc
        dt = time.time() - t0
        print("  段 %d/%d (y=%d-%d) %dB %.0fs%s"
              % (idx + 1, len(bands), top, bottom, len(jpeg), dt, tag), file=sys.stderr)
        if text.strip():
            parts.append((top, text.strip()))

    header = "# 长截图 OCR: %s (%dx%d, %d 段)\n" % (os.path.basename(args.image), w, h, len(bands))
    body = header + "\n" + "\n\n".join("===== y=%d =====\n%s" % (y, t) for y, t in parts)
    out = args.out or os.path.splitext(args.image)[0] + ".ocr.md"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(body)
    print("saved: %s (%d chars, %d/%d 段有内容)"
          % (out, len(body), len(parts), len(bands)), file=sys.stderr)
    # stdout 只留路径，方便 background 任务里 grep
    print(out)


if __name__ == "__main__":
    main()
