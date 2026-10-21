#!/usr/bin/env python3
"""按任务类型选 OmniRoute 免费模型 —— 给任何 agent 调用。

用法：
    python3 pick_model.py coding          # 打印该任务该用的模型 id
    python3 pick_model.py reasoning --json
    python3 pick_model.py vision --probe  # 先探活再返回（默认探活）
    python3 pick_model.py --list          # 全部档位

设计：每个档位是**有序候选表**，从上往下取第一个探活通过的。
探活 = 真打一发 1-token 请求；结果缓存 120 秒，避免每次调用都打网关。

退出码：0 拿到可用模型；1 该档全挂（调用方应降级到 auto/free-pool）。
"""
import json, os, sys, time, urllib.request

BASE = os.environ.get("OMNIROUTE_BASE", "http://192.168.199.2:20128/v1")
CACHE = "/opt/data/cache/scratch/.pick_model_cache.json"
TTL = 120


def _key():
    k = os.environ.get("OMNIROUTE_API_KEY")
    if k:
        return k
    for line in open("/opt/data/.env", encoding="utf-8"):
        line = line.strip()
        if line.startswith("CUSTOM:192-168-199-2-20128_API_KEY=") or line.startswith("OMNIROUTE_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("找不到 OmniRoute key")


# 档位 → 有序候选（2026-10-20 实测：逻辑题 / 数学题 / 工具调用 / 延迟）
TIERS = {
    "reasoning": [   # 硬推理、故障诊断、方案对比
        "openrouter/nvidia/nemotron-3.5-lightning:free",       # ✓✓✓  8.6s 1M
        "openrouter/minimax/minimax-m3.1-flash:free",          # ✓✓✓  4.3s 1M
        "openrouter/dots-studio/dots-3-note-preview:free",     # ✓✓✓ 11.7s 512K
    ],
    "coding": [      # 写代码、改仓库
        "openrouter/nvidia/nemotron-3.5-lightning:free",
        "openrouter/cohere/north-mini-code:free",              # 代码向，逻辑题弱
    ],
    "vision": [      # 看图、OCR、截图
        "openrouter/nvidia/nemotron-3.5-super-vl:free",        # 1M，实测读图正常
    ],
    "fast": [        # 摘要、格式转换、巡检、群聊
        "openrouter/minimax/minimax-m3.1-flash:free",          # 4.3s
        "openrouter/nvidia/nemotron-3.5-lightning:free",
    ],
    "longctx": [     # 长文档、大代码库
        "openrouter/minimax/minimax-m3.1-flash:free",          # 1M
        "openrouter/nvidia/nemotron-3.5-lightning:free",       # 1M
        "openrouter/dots-studio/dots-3-note-preview:free",     # 512K
    ],
}


def _load_cache():
    try:
        return json.load(open(CACHE))
    except Exception:
        return {}


def _save_cache(c):
    try:
        json.dump(c, open(CACHE, "w"))
    except Exception:
        pass


def probe(model, timeout=90):
    """真打一发，返回 (ok, 延迟ms 或 错误串)。"""
    c = _load_cache()
    hit = c.get(model)
    if hit and time.time() - hit["ts"] < TTL:
        return hit["ok"], hit["info"]

    body = json.dumps({"model": model, "messages": [{"role": "user", "content": "OK"}],
                       "max_tokens": 4, "temperature": 0}).encode()
    req = urllib.request.Request(BASE + "/chat/completions", data=body, method="POST")
    req.add_header("Authorization", "Bearer " + _key())
    req.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        j = json.loads(resp.read())
        msg = (j.get("choices") or [{}])[0].get("message", {}) or {}
        ok = bool((msg.get("content") or "").strip() or msg.get("reasoning_content"))
        info = f"{int((time.time()-t0)*1000)}ms" if ok else "空返回"
    except urllib.error.HTTPError as ex:
        ok, info = False, f"HTTP{ex.code}"
    except Exception as ex:
        ok, info = False, type(ex).__name__

    c[model] = {"ok": ok, "info": info, "ts": time.time()}
    _save_cache(c)
    return ok, info


def pick(tier, do_probe=True, timeout=90):
    models = TIERS.get(tier)
    if not models:
        raise SystemExit(f"未知档位 {tier}，可选：{', '.join(TIERS)}")
    trace = []
    for m in models:
        if not do_probe:
            return {"tier": tier, "model": m, "probed": False, "trace": trace}
        ok, info = probe(m, timeout)
        trace.append(f"{m} -> {'OK ' + info if ok else info}")
        if ok:
            return {"tier": tier, "model": m, "probed": True, "info": info, "trace": trace}
    return {"tier": tier, "model": None, "probed": True, "trace": trace}


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if a[0] == "--list":
        for t, ms in TIERS.items():
            print(f"{t:<10} " + " > ".join(m.split("/")[-1] for m in ms))
        return 0
    tier = a[0]
    as_json = "--json" in a
    do_probe = "--no-probe" not in a
    r = pick(tier, do_probe)
    if as_json:
        print(json.dumps(r, ensure_ascii=False))
    else:
        if r["model"]:
            print(r["model"])
            for t in r["trace"][:-1]:
                print(f"  skip {t}", file=sys.stderr)
        else:
            print(f"档位 {tier} 全部不可用", file=sys.stderr)
            for t in r["trace"]:
                print(f"  {t}", file=sys.stderr)
    return 0 if r["model"] else 1


if __name__ == "__main__":
    sys.exit(main())
