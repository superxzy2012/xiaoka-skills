#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通道健康自检 channel_check.py — T-015 踩坑回写
背景：模型通道日变（OmniRoute 别名漂移 / 401 / 503），不能只看配置字面量，必须真实发一次请求。
用法：python3 channel_check.py            # 检查主通道 + fallback 链
      python3 channel_check.py --all      # 再加上所有已配置 provider
退出码：主通道或整条 fallback 全挂 = 1；否则 0（供 cron 判定）。
凭据一律从 /opt/data/config.yaml 读，绝不硬编码。
"""
import sys, json, time, urllib.request, urllib.error, re, os

CONFIG = "/opt/data/config.yaml"
TIMEOUT = 15

def load_config():
    txt = open(CONFIG, encoding="utf-8").read()
    try:
        import yaml
        return yaml.safe_load(txt)
    except Exception:
        return None

def parse_minimal(txt):
    """无 PyYAML 时的兜底：正则抽 providers / fallback_providers（结构稳定够用）。"""
    cfg = {"model": {}, "providers": {}, "fallback_providers": []}
    m = re.search(r"^model:\n((?:[ \t]+.*\n)*)", txt, re.M)
    if m:
        for k in ("provider", "default", "base_url"):
            mm = re.search(rf"^\s+{k}:\s*[\"']?([^\"'\n]+)[\"']?", m.group(1), re.M)
            if mm: cfg["model"][k] = mm.group(1).strip()
    # providers 块
    pm = re.search(r"^providers:\n((?:[ \t]+.*\n?)*)", txt, re.M)
    if pm:
        block = pm.group(1)
        for p in re.finditer(r"^  ([A-Za-z0-9:_\-]+):\n((?:[ \t]+.*\n?)*)", block, re.M):
            name, body = p.group(1), p.group(2)
            d = {}
            for k in ("base_url", "api_key"):
                mm = re.search(rf"^\s+{k}:\s*[\"']?([^\"'\n]+)[\"']?", body, re.M)
                if mm: d[k] = mm.group(1).strip()
            cfg["providers"][name] = d
    fm = re.search(r"^fallback_providers:\s*\n((?:[ \t\-]+.*\n?)*)", txt, re.M)
    if fm:
        for line in fm.group(1).splitlines():
            mm = re.search(r"-\s*[\"']?([^\"'\n#]+)[\"']?", line)
            if mm: cfg["fallback_providers"].append(mm.group(1).strip())
    return cfg

def ping(base_url, api_key, model):
    url = base_url.rstrip("/") + "/chat/completions"
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "ping，回复 ok"}],
        "max_tokens": 8,
    }).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    })
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = json.loads(r.read().decode())
            dt = time.time() - t0
            real = data.get("model", "?")
            return True, f"{dt*1000:.0f}ms 返回模型={real}", dict(r.headers)
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code} {e.reason}", {}
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:80]}", {}

def resolve(cfg, item):
    """把 fallback 项解析成 (base_url, key, model)。item 支持 dict{provider,model} 或字符串。"""
    if isinstance(item, dict):
        prov_name = item.get("provider", "")
        model = item.get("model", "")
    else:
        prov_name, model = item, cfg["model"].get("default", "")
        if "/" in prov_name and not prov_name.startswith("custom"):
            prov_name, model = prov_name.split("/", 1)
    p = cfg["providers"].get(prov_name)
    if not p:
        return None
    key = p.get("api_key")
    if not key and p.get("key_env"):
        key = os.environ.get(p["key_env"], "")
    return (p.get("base_url"), key, model or p.get("model", ""))

def main():
    txt = open(CONFIG, encoding="utf-8").read()
    cfg = load_config() or parse_minimal(txt)
    targets = []  # (标签, base, key, model, 是否主)
    main_prov = cfg["model"].get("provider")
    main_model = cfg["model"].get("default")
    mp = cfg["providers"].get(main_prov, {})
    targets.append((f"[主] {main_prov}/{main_model}", mp.get("base_url"), mp.get("api_key"), main_model, True))
    fb = cfg.get("fallback_providers") or []
    for f in fb:
        r = resolve(cfg, f)
        label = f"{f['provider']}/{f['model']}" if isinstance(f, dict) else f
        if r: targets.append((f"[降级] {label}", r[0], r[1], r[2], False))
    if "--all" in sys.argv:
        for name, p in cfg["providers"].items():
            if name == main_prov: continue
            targets.append((f"[provider] {name}", p.get("base_url"), p.get("api_key"), main_model, False))

    print(f"# 通道健康自检 {time.strftime('%Y-%m-%d %H:%M:%S')} (容器UTC)")
    main_ok = False
    fb_ok = False
    for label, base, key, model, is_main in targets:
        if not base or not key:
            print(f"- ⚠️ {label}：缺 base_url/api_key，跳过")
            continue
        ok, msg, hdr = ping(base, key, model)
        icon = "✅" if ok else "❌"
        extra = ""
        if ok and hdr.get("x-omniroute-model"):
            extra = f"（OmniRoute实际→{hdr.get('x-omniroute-model')}）"
        print(f"- {icon} {label}：{msg}{extra}")
        if is_main: main_ok = ok
        elif ok: fb_ok = True
    if not main_ok and not fb_ok:
        print("\n🔴 主通道与所有降级全挂，需立即处理！")
        return 1
    if not main_ok:
        print("\n🟡 主通道挂，但降级链可用。")
    else:
        print("\n🟢 主通道正常。")
    return 0

if __name__ == "__main__":
    sys.exit(main())
