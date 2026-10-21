#!/usr/bin/env bash
# 把本机已装的技能铺到蜂群各节点：共享库 / 云端星期五 / NAS 贾维斯容器。
# 用法：distribute_skill.sh <skill> [skill...]
#   例：distribute_skill.sh caveman caveman-compress caveman-review
# 前提：技能已在本机 /opt/data/skills 下（任意分类子目录）；NAS/云端 SSH 可用。
set -euo pipefail

SRC=/opt/data/skills
SHARED=/opt/nas/volume2/2-AI/skills
CLOUD=agentuser@100.66.1.6
NAS=DY@192.168.199.2
KEY=/opt/data/.ssh/id_ed25519
SSHOPT="-o ConnectTimeout=12 -o BatchMode=yes -i $KEY"

[ $# -ge 1 ] || { echo "用法: $0 <skill> [skill...]"; exit 2; }

for name in "$@"; do
  dir=$(find "$SRC" -maxdepth 2 -type d -name "$name" | head -1)
  [ -n "$dir" ] || { echo "❌ 本机找不到技能 $name"; exit 1; }
  echo "== $name ← $dir"

  # 1) 共享库（扁平结构，无分类子目录）
  rm -rf "$SHARED/$name"
  cp -a "$dir" "$SHARED/$name"

  # 2) 云端：打包传，云端未必有 node/gh
  tar czf /tmp/_sk.tgz -C "$(dirname "$dir")" "$name"
  scp $SSHOPT /tmp/_sk.tgz "$CLOUD:/tmp/" >/dev/null
  ssh $SSHOPT "$CLOUD" "mkdir -p ~/.hermes/skills/productivity && tar xzf /tmp/_sk.tgz -C ~/.hermes/skills/productivity && rm -f /tmp/_sk.tgz"

  # 3) NAS 贾维斯容器（容器内挂载了 /opt/nas/volume2，直接从共享库取）
  ssh $SSHOPT "$NAS" "sudo -n docker exec hermes-ancgm sh -c 'rm -rf /opt/data/skills/$name && cp -a $SHARED/$name /opt/data/skills/$name'"

  rm -f /tmp/_sk.tgz
  echo "   ✅ 共享库 / 云端 / 贾维斯"
done

# 云端技能是启动时扫描的，必须重启 gateway；本机每次会话扫盘，不用重启
ssh $SSHOPT "$CLOUD" 'systemctl --user restart hermes-gateway.service; sleep 6; systemctl --user is-active hermes-gateway.service'
echo "云端 gateway 已重启；记得跑一次真实验证（普通模式 vs 技能模式对比输出），别只看文件存在"
