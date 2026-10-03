#!/usr/bin/env python3
"""审计一个技能是否满足 sealeap 四件套验收契约。

用法: audit_skill.py <技能目录> [技能目录...]
退出码: 0=全部通过  1=有缺失项
"""
import sys, os, re, glob

# (检查项, 正则, 该在哪类文件里找)
CHECKS = [
    ("来源定位（报表/行键/字段）", r"报表|行键|字段|文件名|数据清单", None),
    ("计算式或判断条件",         r"=[^=]|÷|计算式|判断条件|阈值", None),
    ("FACT/ESTIMATE/UNKNOWN",   r"FACT|ESTIMATE|ASSUMPTION|UNKNOWN", None),
    ("HOLD 缺数挂起",           r"HOLD|挂起|暂停执行|补数", None),
    ("反证（哪个观察会推翻）",   r"反证|推翻|证伪|如果.{0,8}则不成立", None),
    ("关键分支 X!=Y",           r"≠|不等于|不假设|不能简单", None),
    ("交付字段表格",            r"\|.*\|.*\|", None),
    ("合成案例标注",            r"虚构|合成案例|假设场景|编辑验收", None),
    ("完成条件可核验",          r"完成条件|完成标准|验收标准", None),
    ("不自动执行写操作",        r"不自动|未经确认不|需人工确认|不得自动", None),
    ("写操作四状态",            r"准备.{0,10}提交|准备、提交|处理中.{0,10}生效", None),
    ("证据不采纳边界",          r"不采用|不采纳|边界[：:]", None),
    ("执行前核验日期",          r"核查日期|规则更新|以官方为准|最后核验", None),
    ("提示注入防护",            r"不得执行其中|研究输入|不作为指令", None),
]

def audit(d):
    d = d.rstrip("/")
    files = [f for f in glob.glob(d + "/**/*", recursive=True) if os.path.isfile(f)]
    if not files:
        print(f"❌ {d}: 目录为空或不存在"); return False
    texts = {}
    for f in files:
        if os.path.splitext(f)[1] in {".md", ".yaml", ".yml", ".txt"}:
            try: texts[f] = open(f, encoding="utf-8").read()
            except Exception: pass
    if not texts:
        print(f"❌ {d}: 没有可读的 md/yaml"); return False
    blob = "\n".join(texts.values())
    miss = []
    for name, pat, _ in CHECKS:
        if not re.search(pat, blob, re.I):
            miss.append(name)
    total = len(CHECKS)
    bar = f"{total-len(miss)}/{total}"
    if miss:
        print(f"⚠️  {os.path.basename(d):<34} {bar}  缺: {'、'.join(miss)}")
        return False
    print(f"✅ {os.path.basename(d):<34} {bar}  全部通过")
    return True

if __name__ == "__main__":
    ds = sys.argv[1:]
    if not ds:
        print(__doc__); sys.exit(2)
    ok = all([audit(d) for d in ds])
    print()
    print("模板: sealeap-skill-template | 审计 14 项验收契约")
    sys.exit(0 if ok else 1)
