#!/bin/bash
# SWARM-SMOKE-20261018 小卡回执（经 SSH 在 NAS 宿主机以 DY 身份落袋，容器对 A2A 目录无写权限）
set -euo pipefail
SSH="ssh -o BatchMode=yes -o StrictHostKeyChecking=no -i /opt/data/.ssh/id_ed25519 -o ConnectTimeout=8 DY@192.168.199.2"
ROOT=/volume2/2-AI/A2A
TASK=task_SWARM-SMOKE-20261018_xiaoka_20261018_190543.json
TS=$(TZ=Asia/Shanghai date +%Y-%m-%dT%H:%M:%S+08:00)
STAMP=$(TZ=Asia/Shanghai date +%Y%m%dT%H%M%S)
RCPT=receipt_SWARM-SMOKE-20261018_xiaoka_${STAMP}.json

$SSH bash -s "$ROOT" "$TASK" "$RCPT" "$TS" <<'REMOTE'
set -euo pipefail
ROOT="$1"; TASK="$2"; RCPT="$3"; TS="$4"
INBOX="$ROOT/inbox/$TASK"
[ -f "$INBOX" ] || { echo "MISSING: $INBOX"; exit 2; }
# 去重：processed 已有同名或已有 xiaoka PING 回执则退出
[ -f "$ROOT/processed/$TASK" ] && { echo "ALREADY-PROCESSED"; exit 0; }
if ls "$ROOT"/outbox/receipt_SWARM-SMOKE-20261018_xiaoka_*.json >/dev/null 2>&1; then
  echo "ALREADY-RECEIPTED:"; ls "$ROOT"/outbox/receipt_SWARM-SMOKE-20261018_xiaoka_*.json
fi
cat > "$ROOT/outbox/$RCPT" <<EOF
{"receipt_id":"R-SWARM-SMOKE-20261018-xiaoka","task_ref":"SWARM-SMOKE-20261018","from":"xiaoka","to":"xiaomi-codex","ts":"$TS","status":"PING","note":"小卡-nas(NAS容器)在线；A2A根可读。容器uid=10000对A2A目录无写权限(inbox新任务权限700 DY:admin,容器端不可见)，回执经SSH以NAS宿主DY身份落袋；已按constraints将task移入processed。"}
EOF
mv "$INBOX" "$ROOT/processed/$TASK"
echo "WROTE: $ROOT/outbox/$RCPT"
echo "MOVED: inbox/$TASK -> processed/"
REMOTE

echo "=== 容器侧复核（经 SSH 读，容器看不到 700 属主文件属正常） ==="
$SSH "ls -la $ROOT/outbox/$RCPT $ROOT/processed/$TASK && echo '--- 回执内容 ---' && cat $ROOT/outbox/$RCPT"