#!/usr/bin/env python3
"""任务分档器：JEV 决策模型打 5 个二分类 → 档位 → pick_model 选模型。

用法：
    python3 route_task.py "读一张发票截图，提取金额"
    python3 route_task.py "排查 NAS 容器反复重启" --json

设计：JEV 只负责「这活属于哪档」，不负责记模型名（避免它编造 model id）。
失败链：OmniRoute(jevd) → 直连 8082 → 关键词兜底。任何一环挂都不阻塞。
"""
import json, os, re, sys, urllib.request, urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pick_model

OMNI = os.environ.get("OMNIROUTE_BASE", "http://192.168.199.2:20128/v1")
JEV_DIRECT = os.environ.get("JEV_BASE", "http://192.168.199.2:8082/v1")

QUESTIONS = {
    "needs_vision": {"type": "noul", "instructions": "任务是否需要看图片、截图、扫描件或视频画面才能完成？"},
    "needs_long_context": {"type": "noul", "instructions": "任务是否涉及超长文本，例如十万字以上的文档、整个代码库、大量日志？"},
    "is_code_task": {"type": "noul", "instructions": "任务的核心产出是否是代码：写代码、改代码、调试、代码审查？"},
    "is_trivial": {"type": "noul", "instructions": "任务是否简单到一句话就能答完，不需要多步推理或工具？"},
    "needs_hard_reasoning": {"type": "noul", "instructions": "任务是否需要多步推理、权衡多个方案、做复杂诊断或计算？"},
}

# 分数 → 档位（顺序即优先级）
RULES = [
    ("vision", "needs_vision", 0.5),
    ("longctx", "needs_long_context", 0.5),
    ("coding", "is_code_task", 0.5),
    ("reasoning", "needs_hard_reasoning", 0.5),
    ("fast", "is_trivial", 0.5),
]
DEFAULT_TIER = "reasoning"

KW = [
    ("vision", r"图|截图|照片|扫描|OCR|看图|画面|视频帧|发票|证件"),
    ("longctx", r"万字|长文档|整个代码库|全书|年报|全部日志"),
    ("coding", r"代码|脚本|函数|报错|编译|重构|debug|bug|接口"),
    ("fast", r"^(回一句|说一句|翻译|改写|总结一下)$|简单"),
]


def _key():
    k = os.environ.get("OMNIROUTE_API_KEY")
    if k:
        return k
    for path in ("/opt/data/.env", os.path.expanduser("~/.hermes/.env")):
        if not os.path.exists(path):
            continue
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line.startswith(("CUSTOM:192-168-199-2-20128_API_KEY=", "OMNIROUTE_API_KEY=")):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _post(url, payload, key=None, timeout=45):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    if key:
        req.add_header("Authorization", "Bearer " + key)
    j = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    msg = (j.get("choices") or [{}])[0].get("message", {}) or {}
    ans = msg.get("jev_answers")
    if ans:
        return {k: float(v.get("noul", 0)) for k, v in ans.items()}
    # 兜底：从 content 里抠 JSON
    txt = msg.get("content") or ""
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        raise ValueError("no jev_answers")
    d = json.loads(m.group(0))
    return {k: float(v.get("noul", 0)) if isinstance(v, dict) else float(v) for k, v in d.items()}


def classify(task, timeout=45):
    """返回 (tier, scores, via)"""
    # 1) 走 OmniRoute：questions 塞进 system message（网关不转发顶层 questions）
    sysmsg = json.dumps({"questions": QUESTIONS}, ensure_ascii=False)
    msgs = [{"role": "system", "content": sysmsg}, {"role": "user", "content": task}]
    for via, url, key, extra in (
        ("direct", JEV_DIRECT + "/chat/completions", None, {"model": "jev-latest", "questions": QUESTIONS}),
        ("omniroute", OMNI + "/chat/completions", _key(), {"model": "jevd/jev-latest"}),
    ):
        try:
            payload = dict(extra, messages=msgs, max_tokens=200, temperature=0)
            sc = _post(url, payload, key, timeout)
            return _to_tier(sc), sc, via
        except Exception:
            continue
    return _kw_tier(task), {}, "keyword"


def _to_tier(scores):
    for tier, q, th in RULES:
        if scores.get(q, 0) >= th:
            return tier
    return DEFAULT_TIER


def _kw_tier(task):
    for tier, pat in KW:
        if re.search(pat, task, re.I):
            return tier
    return DEFAULT_TIER


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if not a:
        print(__doc__)
        return 0
    task = " ".join(a)
    tier, scores, via = classify(task)
    model = pick_model.pick(tier)["model"]
    out = {"task": task, "tier": tier, "model": model, "via": via, "scores": scores}
    if "--json" in sys.argv:
        print(json.dumps(out, ensure_ascii=False))
    else:
        print(f"档位: {tier}  (判定来源: {via})")
        print(f"模型: {model}")
        if scores:
            print("分数: " + "  ".join(f"{k}={v:.2f}" for k, v in sorted(scores.items())))
    return 0 if model else 1


if __name__ == "__main__":
    sys.exit(main())
