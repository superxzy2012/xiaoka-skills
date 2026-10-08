#!/bin/bash
# 轮式同步：写入节点（NAS）推 → 订阅者（Mac/其他）各自 pull。
#
# 铁律：先拉后推，冲突即中止，绝不强推。工作副本在本地盘，不在共享盘。
#
# 改造时改这 6 个变量：WORK / KEY / REPO / VAULT / SCOPE / MSG
#
# 用法：
#   sync-subscribe.sh            # dry-run：只体检，报体积，不提交不推送
#   sync-subscribe.sh --push     # 真同步
set -u

WORK=/opt/data/sync/<repo>
KEY=/opt/data/.ssh/<repo-key>
REPO=git@github.com:<owner>/<repo>.git
VAULT=/opt/nas/volume2/<space>/<vault>
SCOPE="<只同步这一个目录，不要用 vault 根>"
MSG="sync: $(date +%F\ %H:%M) <范围>"

DO_PUSH=0
[ "${1:-}" = "--push" ] && DO_PUSH=1

log(){ echo "[$(date +%H:%M:%S)] $*"; }

# ── 1. 工作副本（本地盘）──────────────────────────────────
# 共享盘上跑 git checkout 慢一到两个数量级，所以复制到本地盘再操作。
if [ ! -d "$WORK" ]; then
  log "初始化工作副本 $WORK"
  mkdir -p "$WORK"
  cp -a "$VAULT/$SCOPE" "$WORK/" 2>/dev/null
  git -C "$WORK" init -q -b main
  git -C "$WORK" config user.name <bot-name>
  git -C "$WORK" config user.email <bot-email>
  git -C "$WORK" config core.compression 1
  git -C "$WORK" config http.version HTTP/1.1
  git -C "$WORK" remote add origin "$REPO"
fi

# ── 2. 增量刷新 NAS 上的最新成果 ──────────────────────────
if [ -d "$VAULT/$SCOPE" ]; then
  mkdir -p "$WORK/$SCOPE"
  cp -a "$VAULT/$SCOPE/." "$WORK/$SCOPE/" 2>/dev/null
fi

# ── 3. 先拉后推 ─────────────────────────────────────────
log "git fetch/merge"
git -C "$WORK" fetch origin main 2>&1 | sed 's/^/    /'
if git -C "$WORK" rev-parse --verify origin/main >/dev/null 2>&1; then
  git -C "$WORK" merge --no-edit origin/main 2>&1 | sed 's/^/    /'
  if git -C "$WORK" diff --name-only --diff-filter=U | grep -q .; then
    log "❌ 有冲突文件，已中止，未推送："
    git -C "$WORK" diff --name-only --diff-filter=U | sed 's/^/    /'
    exit 2
  fi
else
  log "远端还没有该分支（首次同步）"
fi

# ── 4. 提交前必须报体积 ─────────────────────────────────
git -C "$WORK" add -A
if git -C "$WORK" diff --cached --quiet; then
  log "无变化，无需提交"
else
  MB=$(git -C "$WORK" diff --cached --name-only -z | xargs -0 stat -c%s 2>/dev/null \
       | awk '{s+=$1} END{printf "%.1f", s/1048576}')
  N=$(git -C "$WORK" diff --cached --name-only | wc -l)
  log "待提交 $N 个文件 / ${MB} MB   ← 数量级不对就是 scope 写错了"
  if [ "$DO_PUSH" = 1 ]; then
    git -C "$WORK" commit -q -m "$MSG"
    log "已提交: $(git -C "$WORK" log --oneline -1)"
  else
    log "[dry-run] 未提交，加 --push 才真正执行"
  fi
fi

# ── 5. 推送 ─────────────────────────────────────────────
if [ "$DO_PUSH" = 1 ]; then
  log "push → $REPO"
  if GIT_SSH_COMMAND="ssh -i $KEY -o IdentitiesOnly=yes" \
     git -C "$WORK" push origin main 2>&1 | sed 's/^/    /'; then
    log "✅ 推送成功"
  else
    log "❌ 推送失败 —— 多半是 deploy key 没被加进 repo，或没勾 Allow write access"
    exit 3
  fi
else
  log "[dry-run] 未推送，加 --push 才真正执行"
fi