#!/usr/bin/env bash
# 技能库自动备份 + 版本管理
#   A: GitHub 公开仓 superxzy2012/xiaoka-skills（脱敏后）
#   C: NAS 本地私有仓 15-小卡工作区/技能仓库（原样，不上传）
#
# 用法: backup_skills.sh [commit-msg]
set -uo pipefail

SRC_SKILLS=/opt/data/skills
SRC_MEM=/opt/data/memories
STAGE=/opt/data/cache/scratch/backup-stage
LOCAL=/opt/nas/volume2/2-AI/obsidian_vault/15-小卡工作区/技能仓库
REMOTE=origin
MSG="${1:-chore: sync $(date +%Y-%m-%d\ %H:%M)}"

export HOME=/opt/data/home
export GH_CONFIG_DIR=/opt/data/home/.config/gh

echo "→ 1/4 脱敏暂存"
rm -rf "$STAGE"; mkdir -p "$STAGE"
python3 <<'PY'
import os,glob,re,shutil
STAGE="/opt/data/cache/scratch/backup-stage"
SKIP_DIRS={".git","__pycache__","node_modules",".cache",".venv",".venv-browser",".playwright-browsers"}
SKIP_PARTS={"cookies"}                      # 登录态绝不上网
SKIP_NAMES={"MEMORY.md","USER.md","USER_PROFILE.md"}   # 含个人信息
# research 区只收笔记与配图：音视频体积大且可重新生成，不入库
RESEARCH_EXT={".md",".png",".jpg",".jpeg",".webp",".gif",".json",".py",".txt"}
RULES=[(re.compile(r'1[3-9]\d{9}'),'【手机号】'),
       (re.compile(r'【城市区】'),'【城市区】'),
       (re.compile(r'【大厦】'),'【大厦】'),
       (re.compile(r'【BOSS姓名】'),'【BOSS姓名】'),
       (re.compile(r'【BOSS英文名】|【BOSS英文名】'),'【BOSS英文名】')]
n=s=0
for src,top in [("/opt/data/skills","skills"),("/opt/data/memories","memories"),
                 ("/opt/nas/volume2/2-AI/obsidian_vault/15-小卡工作区/学习输出","research/学习输出"),
                 ("/opt/nas/volume2/2-AI/obsidian_vault/08-抖音视频学习","research/抖音视频学习")]:
    for f in glob.glob(src+"/**/*",recursive=True):
        if not os.path.isfile(f): continue
        rel=os.path.relpath(f,src); parts=set(rel.split(os.sep))
        if (parts&SKIP_DIRS) or (parts&SKIP_PARTS) or os.path.basename(f) in SKIP_NAMES: continue
        if top.startswith("research/") and os.path.splitext(f)[1].lower() not in RESEARCH_EXT: continue
        try: t=open(f,encoding="utf-8").read()
        except Exception: continue
        o=t
        for rx,rep in RULES: t=rx.sub(rep,t)
        d=os.path.join(STAGE,top,rel); os.makedirs(os.path.dirname(d),exist_ok=True)
        if os.path.splitext(f)[1] in {".py",".sh",".md",".txt",".json",".yaml",".yml",""}:
            open(d,"w",encoding="utf-8").write(t)
        else: shutil.copy2(f,d)
        n+=1; s+= (t!=o)
print(f"   {n} 文件暂存, {s} 个脱敏")
PY

# README 与 .gitignore 由本脚本维护（rsync --delete 会删掉手工放的文件）
cat > "$STAGE/.gitignore" <<'EOF'
.DS_Store
*.pyc
__pycache__/
EOF
if [ ! -f "$STAGE/README.md" ]; then cp /opt/data/skills/find-skills-xiaoka/README.md "$STAGE/README.md" 2>/dev/null || true; fi

echo "→ 2/4 校验无敏感信息残留"
if grep -rlE '1[3-9][0-9]{9}|【城市区】|【大厦】|【BOSS姓名】|【BOSS英文名】' "$STAGE" 2>/dev/null | grep -q .; then
  echo "   ❌ 仍有敏感信息，中止"; exit 1
fi
echo "   ✅ 干净"

echo "→ 3/4 同步到本地仓（NAS）"
mkdir -p "$LOCAL"
# 只同步工作区文件，绝不动 .git（rsync --delete 会连带删掉 .git/config 里的 remote）
rsync -a --delete --exclude='.git/' "$STAGE"/ "$LOCAL"/ 2>/dev/null \
  || { find "$LOCAL" -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} + 2>/dev/null; cp -r "$STAGE"/. "$LOCAL"/; }
if [ ! -d "$LOCAL/.git" ]; then
  git -C "$LOCAL" init -q -b main
  git -C "$LOCAL" remote add origin https://github.com/superxzy2012/xiaoka-skills.git
  git -C "$LOCAL" config user.name xiaoka-bot
  git -C "$LOCAL" config user.email xiaoka@local
fi
git -C "$LOCAL" add -A
if ! git -C "$LOCAL" diff --cached --quiet; then
  git -C "$LOCAL" commit -q -m "$MSG"
  echo "   本地已提交: $(git -C "$LOCAL" log --oneline -1)"
else
  echo "   本地无变化"
fi

echo "→ 4/4 push 到 GitHub"
if ! git -C "$LOCAL" remote get-url "$REMOTE" >/dev/null 2>&1; then
  git -C "$LOCAL" remote add "$REMOTE" https://github.com/superxzy2012/xiaoka-skills.git 2>/dev/null
fi
if git -C "$LOCAL" remote get-url "$REMOTE" >/dev/null 2>&1; then
  for i in 1 2 3; do
    if git -C "$LOCAL" push -q "$REMOTE" main 2>/dev/null; then
      echo "   ✅ pushed (第${i}次)"; exit 0
    fi
    sleep 20   # github.com 间歇性不可达，实测恢复需 45-75s
  done
  echo "   ⚠️ push 失败（网络），本地仓已保存，下次自动重试"
else
  echo "   ⏭ 未配置 remote"
fi