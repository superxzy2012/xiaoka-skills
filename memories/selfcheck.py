#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小卡 · 共享链路自检
检查 external_dirs 是否被重置、软链是否悬空、技能数是否正常。
自愈：external_dirs 被清空 → 自动重写。
退出码：0=健康  1=已自愈  2=需人工
"""
import subprocess, os, sys, json, datetime

HERMES = "/opt/hermes/bin/hermes"
EXPECT = ["/opt/data/skills", "/opt/nas/volume2/2-AI/skills"]
SHARED = "/opt/nas/volume2/2-AI/skills"
VAULT_SNAP = "/opt/nas/volume2/2-AI/obsidian_vault/15-小卡工作区/记忆快照"
# 隐私：USER.md 明令「个人信息绝不共享给其他 agent——不建软链、不写入共享区」。
# 故共享区不挂 xiaoka-memories/，快照区也不放 USER_PROFILE.md。
# 二者是「按要求移除」，不是「链路损坏」，不得计入 LINKS。
MEM_LOCAL = "/opt/data/memories"
LINKS = [
    f"{SHARED}/xiaoka-boss-ops",
    f"{VAULT_SNAP}/AGENT_SOUL.md",
    f"{VAULT_SNAP}/PROTOCOLS.md",
    f"{VAULT_SNAP}/KB_INDEX.md",
]

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=90).stdout.strip()

# --- 浏览器卫生：每个站点最多 2 个标签页 ---
def check_browser_hygiene():
    """BOSS 要求：同一网站最多开 2 个标签页，避免拖垮 CDP 桥接"""
    import json, urllib.request
    try:
        with urllib.request.urlopen("http://192.168.199.70:9222/json/list", timeout=10) as r:
            targets = json.loads(r.read().decode())
    except Exception as e:
        print(f"⚠️  浏览器标签检查失败（CDP 不可达）: {e}")
        return 0
    pages = [t for t in targets if t.get("type") == "page"]
    buckets = {}
    for t in pages:
        u = t.get("url", "")
        for dom in ("douyin.com", "bilibili.com", "b23.tv", "zsxq.com", "12306.cn",
                    "meituan.com", "baidu.com", "feishu.cn"):
            if dom in u:
                buckets.setdefault(dom, []).append(t)
                break
        else:
            buckets.setdefault("其他", []).append(t)
    bad = 0
    for dom, ts in buckets.items():
        n = len(ts)
        flag = "❌" if n > 2 else "✅"
        if n > 2:
            bad += 1
        print(f"{flag} 标签页 {dom}: {n} 个")
    total = len(pages)
    print(f"   共 {total} 个 page" + ("（超过 8 个建议清理）" if total > 8 else ""))
    return bad


def main():
    report, healed, problems = [], False, []

    # 1. external_dirs
    cur = run(f"{HERMES} config get skills.external_dirs")
    if all(p in cur for p in EXPECT) and cur.strip() not in ("[]", ""):
        report.append(f"✅ external_dirs 正常（{len(EXPECT)} 个目录）")
    else:
        healed = True
        run(f"{HERMES} config set skills.external_dirs '{json.dumps(EXPECT)}'")
        check = run(f"{HERMES} config get skills.external_dirs")
        if all(p in check for p in EXPECT):
            report.append("🔧 external_dirs 被清空 → 已自动重写并验证")
        else:
            problems.append("external_dirs 重写失败")
            report.append("❌ external_dirs 重写失败")

    # 2. 软链/路径存在性
    # 旧判据 islink() and not exists() 只抓「悬空软链」，路径整个不存在时
    # islink 为 False → 被静默跳过 → 报假通过。改为两条都查。
    dangling = [l for l in LINKS if os.path.islink(l) and not os.path.exists(l)]
    absent = [l for l in LINKS if not os.path.exists(l)]
    if dangling or absent:
        for d in dangling:
            problems.append(f"悬空软链 {d}")
        for a in absent:
            problems.append(f"路径缺失 {a}")
        detail = []
        if dangling:
            detail.append(f"悬空 {len(dangling)}")
        if absent:
            detail.append(f"缺失 {len(absent)}")
        report.append(f"❌ 软链异常（{'，'.join(detail)}）")
    else:
        report.append(f"✅ 软链 {len(LINKS)} 条全部可达")

    # 3. 技能数
    n = len([x for x in run(f"{HERMES} skills list").splitlines() if x.strip()])
    if n >= 300:
        report.append(f"✅ 技能加载 {n} 条")
    elif n >= 50:
        report.append(f"⚠️ 技能仅 {n} 条（共享库可能未挂上）")
    else:
        problems.append(f"技能数异常低: {n}")
        report.append(f"❌ 技能仅 {n} 条")

    # 4. NAS 挂载
    if os.path.isdir(SHARED) and len(os.listdir(SHARED)) > 100:
        report.append("✅ NAS 共享库已挂载")
    else:
        problems.append("NAS 共享库未挂载或为空")
        report.append("❌ NAS 共享库未挂载")

    # 5. 记忆内容完整（读本地本体，共享区按隐私要求无此路径）
    up = f"{MEM_LOCAL}/USER_PROFILE.md"
    try:
        txt = open(up, encoding="utf-8").read()
        missing = [k for k in ("深圳", "美团") if k not in txt]
        if not missing:
            report.append(f"✅ 4层记忆内容完整（{up}）")
        else:
            report.append(f"❌ USER_PROFILE 缺字段: {'、'.join(missing)}")
            problems.append(f"USER_PROFILE 缺 BOSS 关键信息: {'、'.join(missing)}")
    except Exception as e:
        report.append(f"❌ 记忆读取失败: {e}")
        problems.append("记忆读取失败")

    # 6. 4 层记忆本体齐备（防止某层被清空/丢文件，此前无任何检查覆盖）
    layer_files = ["AGENT_SOUL.md", "USER_PROFILE.md", "PROTOCOLS.md", "KB_INDEX.md"]
    gone = [f for f in layer_files if not os.path.exists(f"{MEM_LOCAL}/{f}")]
    if gone:
        report.append(f"❌ 记忆本体缺失 {len(gone)} 个: {'、'.join(gone)}")
        problems.append(f"记忆本体缺失: {'、'.join(gone)}")
    else:
        report.append(f"✅ 记忆本体 4 层齐备")

    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    out = [f"🔎 小卡自检 {ts}", ""] + report
    if problems:
        out += ["", "⚠️ 需人工处理:"] + [f"  - {p}" for p in problems]
    print("\n".join(out))
    return 2 if problems else (1 if healed else 0)

if __name__ == "__main__":
    sys.exit(main())
