#!/usr/bin/env bash
# 沙箱无 root 装 libmagic：从清华 Debian 镜像下 deb 解包到 /opt/data/local/libmagic。
# neonize import 时需要 libmagic.so.1；脚本本身不改系统，纯用户态。
set -e
DEST=/opt/data/local/libmagic
MIRROR=https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/f/file/
# 版本号会变，从目录页抓当前可用的 amd64 deb（优先非 t64 的稳定版）
URL=$(curl -sSL "$MIRROR" --max-time 30 | grep -oE 'libmagic1_[^"]*amd64\.deb' | sort -u | tail -1)
[ -n "$URL" ] || { echo "no libmagic deb found"; exit 1; }
mkdir -p "$DEST"
curl -sSL -o /tmp/libmagic.deb "${MIRROR}${URL}" --max-time 60
dpkg-deb -x /tmp/libmagic.deb "$DEST"
find "$DEST" -name 'libmagic.so*'
echo "OK — Python 侧用 ctypes.CDLL 预加载（见 wa_pair_local.py 开头）"
