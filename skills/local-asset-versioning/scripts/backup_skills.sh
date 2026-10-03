#!/usr/bin/env bash
# 私有资产备份：脱敏 → 校验 → 提交 → push
# 详细规则与坑见 ../SKILL.md 与 ../references/redaction-and-publish.md
set -uo pipefail

SRC_SKILLS=/opt/data/skills
SRC_MEM=/opt/data/memories
STAGE=/opt/data/cache/scratch/backup-stage
LOCAL="${LOCAL_REPO:-/opt/nas/volume2/2-AI/obsidian_vault/15-小卡工作区/技能仓库}"
REMOTE_URL="${REMOTE_URL:-https://github.com/<owner>/<repo>.git}"
BRANCH=main
MSG="${1:-chore: sync $(date +%Y-%m-%d\ %H:%M)}"

export HOME=/opt/data/home
export GH_CONFIG_DIR=/opt/data/home/.config/gh

echo "→ 1/4 脱敏暂存"
rm -rf "$STAGE"; mkdir -p "$STAGE"
python3 - <<'PY'
import os, glob, re, shutil
STAGE = "/opt/data/cache/scratch/backup-stage"
SKIP_DIRS  = {".git", "__pycache__", "node_modules", ".cache", ".venv", ".venv-browser", ".playwright-browsers"}
SKIP_PARTS = {"cookies"}                              # 登录态绝不上网
SKIP_NAMES = {"MEMORY.md", "USER.md", "USER_PROFILE.md"}
RULES = [(re.compile(r'1[3-9]\d{9}'), '【手机号】'),
         (re.compile(r'【BOSS姓名】'), '【BOSS姓名】'),
         (re.compile(r'【BOSS英文名】|【BOSS英文名】'), '【BOSS英文名】'),
         (re.compile(r'【城市区】'), '【城市区】'),
         (re.compile(r'【大厦】'), '【大厦】')]
n = s = 0
for src, top in [("/opt/data/skills", "skills"), ("/opt/data/memories", "memories")]:
    for f in glob.glob(src + "/**/*", recursive=True):
        if not os.path.isfile(f):
            continue
        rel = os.path.relpath(f, src)
        parts = set(rel.split(os.sep))
        if (parts & SKIP_DIRS) or (parts & SKIP_PARTS) or os.path.basename(f) in SKIP_NAMES:
            continue
        try:
            t = open(f, encoding="utf-8").read()
        except Exception:
            continue
        o = t
        for rx, rep in RULES:
            t = rx.sub(rep, t)
        d = os.path.join(STAGE, top, rel)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        if os.path.splitext(f)[1] in {".py", ".sh", ".md", ".txt", ".json", ".yaml", ".yml", ""}:
            open(d, "w", encoding="utf-8").write(t)
        else:
            shutil.copy2(f, d)
        n += 1
        s += (t != o)
print(f"   {n} 文件暂存, {s} 个脱敏")
PY

echo "→ 2/4 校验无敏感信息残留（提交前硬门）"
if grep -rlE '1[3-9][0-9]{9}|【BOSS姓名】|【城市区】|【大厦】|【BOSS英文名】' "$STAGE" 2>/dev/null | grep -q .; then
  echo "   ❌ 仍有敏感信息，中止"; exit 1
fi
echo "   ✅ 干净"

echo "→ 3/4 同步到本地仓"
mkdir -p "$LOCAL"
# 注意：--exclude='.git' 不够，必须带斜杠，否则会删掉 .git/config 里的 remote
rsync -a --delete --exclude='.git/' "$STAGE"/ "$LOCAL"/ 2>/dev/null \
  || { find "$LOCAL" -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} + 2>/dev/null; cp -r "$STAGE"/. "$LOCAL"/; }
if [ ! -d "$LOCAL/.git" ]; then
  git -C "$LOCAL" init -q -b "$BRANCH"
  git -C "$LOCAL" config user.name  xiaoka-bot
  git -C "$LOCAL" config user.email xiaoka@local
fi
git -C "$LOCAL" remote get-url origin >/dev/null 2>&1 \
  || git -C "$LOCAL" remote add origin "$REMOTE_URL"
git -C "$LOCAL" add -A
if ! git -C "$LOCAL" diff --cached --quiet; then
  git -C "$LOCAL" commit -q -m "$MSG"
  echo "   本地已提交: $(git -C "$LOCAL" log --oneline -1)"
else
  echo "   本地无变化"
fi

echo "→ 4/4 push"
# 网页域名可能间歇不可达而 API 域名正常，先探活再推
for i in 1 2 3; do
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 10 https://github.com 2>/dev/null)
  if [ "$code" = "200" ] && git -C "$LOCAL" push -q origin "$BRANCH" 2>/dev/null; then
    echo "   ✅ pushed (第${i}次)"; exit 0
  fi
  sleep 20
done
echo "   ⚠️ push 失败（网络），本地仓已保存，下次自动重试"
exit 0