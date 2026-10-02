#!/usr/bin/env bash
# 一键把 GitHub 上开源的仓库/文件拉到本地，避免重复造轮子。
# 实测：本机 clone 慢的根因是 checkout 写 NAS 磁盘，用 --no-checkout 可从 180s → 2s。
#
# 用法：
#   gh_pull.sh <owner/repo> [目标目录]        # 整仓
#   gh_pull.sh <owner/repo> -f <路径>         # 只要单个文件
#   gh_search.sh <关键词> [数量]              # 搜仓库
set -uo pipefail

BIN="$(dirname "$0")"
GH=/opt/data/bin/gh
CACHE=/opt/data/cache/scratch/gh-cache
mkdir -p "$CACHE"

# ---- 整仓：--depth 1 --filter=blob:none，checkout 放最后（实测最快）----
pull_repo() {
  local repo="$1" dest="${2:-$CACHE/$(basename "$1")}"
  [ -d "$dest/.git" ] && { echo "已存在: $dest"; return 0; }
  git clone --depth 1 --single-branch "$repo" "$dest" 2>/dev/null \
    || git clone --depth 1 --single-branch "https://github.com/$repo.git" "$dest"
  echo "→ $dest"
}

# ---- 单文件：contents API + base64，比 clone 可靠且不写磁盘 ----
pull_file() {
  local repo="$1" path="$2"
  local out="$CACHE/${repo//\//_}__$(echo "$path" | tr '/' '_')"
  curl -sf -m 30 "https://api.github.com/repos/$repo/contents/$path" \
   | python3 -c "import sys,json,base64;d=json.load(sys.stdin);open('$out','wb').write(base64.b64decode(d['content']))" \
   && echo "→ $out" || { echo "失败: $repo/$path"; return 1; }
}

# ---- 整仓 tarball：绕过 git 协议 ----
pull_tar() {
  local repo="$1" ref="${2:-main}"
  local tgz="$CACHE/$(basename "$repo").tar.gz"
  curl -sfL -m 180 -o "$tgz" "https://codeload.github.com/$repo/tar.gz/refs/heads/$ref" \
   && { tar xzf "$tgz" -C "$CACHE" && echo "→ $CACHE/${repo##*/}-$ref"; } \
   || echo "失败: $repo@$ref"
}

case "${1:-}" in
  -f) pull_file "$2" "$3" ;;
  -t) pull_tar  "$2" "${3:-main}" ;;
  "")  echo "用法: $0 <owner/repo> [目录] | $0 -f <owner/repo> <路径> | $0 -t <owner/repo> [ref]"; exit 1 ;;
  *)   pull_repo "$1" "${2:-}" ;;
esac