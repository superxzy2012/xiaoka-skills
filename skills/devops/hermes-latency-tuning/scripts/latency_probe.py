#!/usr/bin/env python3
"""Hermes 延迟分层探针：一次性量出「模型裸延迟」这一层（小 prompt vs 大 prompt）。

启动开销与工具往返用 SKILL.md 第一节的命令量，本脚本不覆盖。

用法:
    python3 latency_probe.py --base-url http://HOST:PORT/v1 --model MODEL_ID

Key 来源（按优先级）:
    1. 环境变量 $PROBE_API_KEY
    2. --env-file 指定的文件里第一个 *API_KEY* 行（默认 /opt/data/.env）
       —— 逐行 split("=", 1) 解析，不用 shell source：带冒号的键名 source 会失败。
"""
import argparse, json, os, statistics, sys, time, urllib.request


def load_key(env_file: str) -> str:
    key = os.environ.get("PROBE_API_KEY")
    if key:
        return key
    try:
        for line in open(env_file, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if "API_KEY" in line and "=" in line and not line.startswith("#"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError as e:
        sys.exit(f"cannot read {env_file}: {e}")
    sys.exit("no API key found (set $PROBE_API_KEY or --env-file)")


def probe(base_url, model, key, filler_chars, n, max_tokens=64):
    msgs = [{"role": "system", "content": "You are a terse assistant."}]
    if filler_chars:
        msgs.append({"role": "user", "content": "Background: " + ("filler text. " * (filler_chars // 13))})
    msgs.append({"role": "user", "content": "What time is it?"})
    body = json.dumps({"model": model, "messages": msgs,
                       "max_tokens": max_tokens, "stream": False}).encode()
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + key})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            usage = json.loads(r.read()).get("usage", {}) or {}
        return time.time() - t0, usage.get("prompt_tokens"), usage.get("completion_tokens")
    except Exception as e:
        return time.time() - t0, f"ERR {e}", None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--env-file", default="/opt/data/.env")
    ap.add_argument("--runs", type=int, default=3)
    a = ap.parse_args()
    key = load_key(a.env_file)

    for label, filler in (("small prompt", 0), ("large prompt (~70k tok)", 200000)):
        rows = []
        print(f"=== {label} ===")
        for i in range(a.runs):
            dt, pt, ct = probe(a.base_url, a.model, key, filler, a.runs)
            rows.append(dt)
            print(f"  #{i+1} {dt:6.2f}s  prompt_tokens={pt} completion={ct}")
        print(f"  median={statistics.median(rows):.2f}s  min={min(rows):.2f}s\n")
    print("判读：模型裸延迟若远小于端到端墙钟，瓶颈在上下文装配或工具链路，"
          "不要靠换模型档位提速。")


if __name__ == "__main__":
    main()
