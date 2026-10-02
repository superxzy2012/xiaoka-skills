#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""女娲 Skill 造人术 · Hermes 路径迁移补丁

把 nuwa-skill 里写死的 `.claude/skills/` 改成 Hermes 的技能根目录，
并让目录创建遵循 Hermes 的 external_dirs 约定。

原版 nuwa-skill 来自 Claude Code，Phase 0.5 硬编码 `.claude/skills/`，
在 Hermes 上直接跑会把文件建到错误位置、skill-loader 找不到。

幂等：可重复运行。
"""
import os, re, sys

NUXA_DIR = "/opt/nas/volume2/2-AI/skills/nuwa-skill"
STATE_FILE = os.path.join(NUXA_DIR, ".hermes-paths.json")

# Hermes 技能根：优先共享库（其他 agent 也能用），本地 profile 作为私有补充
SHARED = "/opt/nas/volume2/2-AI/skills"
LOCAL = "/opt/data/skills"

REPLACEMENTS = [
    # SKILL.md 正文
    ("检查 `.claude/skills/` 目录",
     "检查 Hermes 技能根目录（见下方「技能落盘位置」）"),
    ("扫描 `.claude/skills/*-perspective/` 目录",
     "扫描 Hermes 技能根目录下的 `*-perspective/`"),
    (".claude/skills/[person-name]-perspective/\n├── SKILL.md",
     "[Hermes技能根]/[person-name]-perspective/\n├── SKILL.md"),
    ("**主动扫描 `.claude/skills/` 目录**",
     "**主动扫描 Hermes 技能根目录**"),
    ("将完成的SKILL.md写入 `.claude/skills/[person-name]-perspective/SKILL.md`。",
     "将完成的SKILL.md写入 `[Hermes技能根]/[person-name]-perspective/SKILL.md`"
     "（技能根见「技能落盘位置」）。"),
    # scripts docstring
    ("python3 merge_research.py .claude/skills/elon-musk-perspective",
     "python3 merge_research.py <技能根>/elon-musk-perspective"),
    ("python3 quality_check.py .claude/skills/elon-musk-perspective/SKILL.md",
     "python3 quality_check.py <技能根>/elon-musk-perspective/SKILL.md"),
]


def migrate(verbose=True):
    changes = []
    for rel in ["SKILL.md", "scripts/merge_research.py", "scripts/quality_check.py"]:
        fp = os.path.join(NUXA_DIR, rel)
        if not os.path.exists(fp):
            continue
        t = orig = open(fp, encoding="utf-8").read()
        for old, new in REPLACEMENTS:
            t = t.replace(old, new)
        if t != orig:
            open(fp, "w", encoding="utf-8").write(t)
            changes.append(rel)
    if verbose:
        for c in changes:
            print(f"  ✅ 已迁移: {c}")
        if not changes:
            print("  ℹ️  无需改动（已是最新）")
    return changes


def write_state():
    os.makedirs(NUXA_DIR, exist_ok=True)
    import json
    json.dump({
        "skill_root_shared": SHARED,
        "skill_root_local": LOCAL,
        "naming": "[person-name]-perspective",
        "platform": "Hermes Agent",
        "migrated_by": "xiaoka",
    }, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    print("女娲 → Hermes 路径迁移")
    migrate()
    write_state()
    print(f"\n技能根（共享）: {SHARED}")
    print(f"技能根（本地）: {LOCAL}")
    print(f"命名约定: [person-name]-perspective")