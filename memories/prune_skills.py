#!/usr/bin/env python3
"""精简技能目录：把长尾技能从常驻提示里摘掉（skills.disabled），
生成离线索引，保留按名加载能力（skill_view 不受 disabled 影响）。"""
import os, re, json, shutil, time, sys

DIRS = ['/opt/data/skills', '/opt/nas/volume2/2-AI/skills']
CFG = '/opt/data/config.yaml'
INDEX = '/opt/data/memories/SKILL_INDEX_OFF.md'

KEEP = set("""
xiaoka-boss-ops xiaoka-execution-discipline boss-personal-assistant boss-reporting-style
communication-style model-routing self-evolving skill-creator skill-finder find-skills-xiaoka
ground-truth-discipline opc-guardrails routine-handoff autolearn workflow-architect-reporting
feishu-group-bot-bridge feishu-bot-group-mentions feishu-13bots-tester a2a-file-bus
multi-agent-collaboration agent-down-doctor agent-governance multi-agent-roles
nas-manager nas-docker-deploy nas-proxy-sidecar nas-smb-mount nodebabylink-mesh-troubleshoot
lan-proxy-gateway omniroute-gateway-ops hermes-agent hermes-tool-execution tools-terminal-usage
cdp-browser-automation remote-browser-cdp-bridge mac-cdp-chrome-9222 windows-remote-access
chat2api-gateway-doctor n8n-nas-ops proxy-split-routing-ops
video-ingest-pipeline video-ingest-to-obsidian media-import douyin-obsidian douyin-bilibili-ingest
douyin-video-downloader openai-whisper transcription-routing obsidian obsidian-sync-hub
zsxq zsxq-import book-note-taking local-image-ocr markitdown-skill convert-documents-to-markdown
wechat-formatter yuanliuwei-writer ai-trending-topics content-planner wechat-cover-generator
wechat-autopilot-main-account humanizer
ozon-mastery ozon-store-ops-runbook ozon-product-to-listing ozon-seller-ops ozon-listing-publish
ozon-price-index-green ozon-price-archive-ops ozon-compliance-gate ozon-cert-selfcheck
ozon-product-copywriter ozon-2026-framework product-selection crossborder-ecommerce
ml-duplicate-listing-audit quality-audit risk-playbook data-monitoring 1688-supplier-outreach
docx xlsx powerpoint pdf mermaid-skill
astock-market-data subtitle-pack-downloader file-organizer find github systematic-debugging
115网盘电影字幕匹配 (xiaoka-115-subtitle)
""".split('\n'))
KEEP = {k.strip() for line in KEEP for k in line.split() if k.strip()}
# 上面按空白拆分会把带空格的名字拆开，单独补回
KEEP.discard('(xiaoka-115-subtitle)')
KEEP.add('115网盘电影字幕匹配 (xiaoka-115-subtitle)')

rows = {}
for d in DIRS:
    for root, _, files in os.walk(d):
        if 'SKILL.md' in files:
            p = os.path.join(root, 'SKILL.md')
            try:
                txt = open(p, encoding='utf-8', errors='replace').read()
            except Exception:
                continue
            m = re.match(r'^---\s*\n(.*?)\n---', txt, re.S)
            fm = m.group(1) if m else ''
            n = re.search(r'^name:\s*(.+)$', fm, re.M)
            de = re.search(r'^description:\s*(.+)$', fm, re.M)
            n = n.group(1).strip().strip('"\'') if n else os.path.basename(root)
            de = de.group(1).strip().strip('"\'') if de else ''
            rows.setdefault(n, de if len(de) > len(rows.get(n, '')) else rows.get(n, ''))

all_names = set(rows)
missing = sorted(KEEP - all_names)
keep = sorted(KEEP & all_names)
disable = sorted(all_names - set(keep))

kept_chars = sum(len(rows[n]) for n in keep)
dis_chars = sum(len(rows[n]) for n in disable)
print(f"总技能 {len(all_names)} | 保留 {len(keep)} | 禁用 {len(disable)}")
print(f"描述字符 保留 {kept_chars} / 禁用 {dis_chars} / 总 {kept_chars+dis_chars}")
if missing:
    print("KEEP 里不存在的名字:", missing)

# ---- 1. 写索引（按前缀分组，给每个禁用技能一行短触发词）
def short(d, n):
    d = re.sub(r'\s+', ' ', d).strip()
    d = d.split('。')[0]
    return d[:46]

groups = {}
for n in disable:
    pre = n.split('-')[0] if '-' in n else '其他'
    groups.setdefault(pre, []).append(n)

lines = ["# 技能离线索引（已从常驻提示摘除，按需 skill_view 加载）",
         "",
         f"共 {len(disable)} 个技能被 `skills.disabled` 隐藏；**skill_view(name=...) 仍可正常加载**。",
         "用法：任务落在某个域 → 在下表找名字 → `skill_view(name='...')`。",
         ""]
for pre in sorted(groups, key=lambda p: (-len(groups[p]), p)):
    names = sorted(groups[pre])
    lines.append(f"## {pre}（{len(names)}）")
    for n in names:
        lines.append(f"- `{n}` — {short(rows[n], n)}")
    lines.append("")
open(INDEX, 'w', encoding='utf-8').write("\n".join(lines))
print(f"索引已写 {INDEX}（{len(disable)} 行）")

# ---- 2. 改 config.yaml
txt = open(CFG, encoding='utf-8').read()
shutil.copy2(CFG, CFG + '.bak-skills-prune-' + time.strftime('%Y%m%d%H%M%S'))
if 'disabled:' in txt.split('onboarding:')[0].split('skills:')[-1]:
    print("config 已有 skills.disabled，请手工检查，未改动")
    sys.exit(0)

block = "  disabled:\n" + "".join(f"    - {json.dumps(n, ensure_ascii=False)}\n" for n in disable)
anchor = "    - /opt/nas/volume2/2-AI/skills\n"
assert txt.count(anchor) == 1, "锚点不唯一"
txt = txt.replace(anchor, anchor + block)
open(CFG, 'w', encoding='utf-8').write(txt)

try:
    import yaml
    y = yaml.safe_load(open(CFG, encoding='utf-8'))
    d = y['skills']['disabled']
    print(f"YAML 校验 OK，skills.disabled = {len(d)} 条；保留 external_dirs={len(y['skills']['external_dirs'])}")
except Exception as e:
    print("YAML 校验失败，回滚:", e)
    shutil.copy2(sorted([f for f in os.listdir('/opt/data') if f.startswith('config.yaml.bak-skills-prune-')])[-1], CFG)
    sys.exit(1)
