#!/usr/bin/env bash
# 知识星球每日入库 —— 默认走 NAS 宿主机 headless Chrome(192.168.199.2:9222)。
# Windows(super) 只在 NAS cookie 失效(401)时用一次：经 SSH 隧道从它已登录的 Chrome 抽
# 新鲜 zsxq cookie 回注 NAS，然后仍由 NAS 抓取入库。日常不依赖 Windows 开机。
set -u
LIMIT="${1:-20}"
PY=python3
INGEST=/opt/data/memories/zsxq_ingest3.py
LOG=/opt/data/cache/scratch/zsxq_last.log

export CDP_HOST=192.168.199.2
export CDP_PORT=9222

run_ingest() { $PY "$INGEST" "$LIMIT" >"$LOG" 2>&1; echo $?; }

echo "== 在 NAS 宿主机 CDP(9222) 抓取 ==" >&2
code=$(run_ingest)
cat "$LOG" >&2

# 401 = NAS 里星球登录态失效 → 去 Windows 抽新 cookie 回注后重试一次
if grep -q "code=401" "$LOG"; then
  echo "⚠️ NAS cookie 失效(401)，尝试从 Windows 抽取新鲜登录态回注…" >&2
  if $PY /opt/data/memories/zsxq_refresh_cookie.py >/opt/data/cache/scratch/zsxq_refresh.log 2>&1; then
    echo "✅ cookie 已刷新，NAS 重新抓取：" >&2
    code=$(run_ingest); cat "$LOG" >&2
  else
    echo "❌ 无法从 Windows 刷新 cookie（机器没开/Chrome 9223 没开/登录态掉），今日入库失败" >&2
    cat /opt/data/cache/scratch/zsxq_refresh.log >&2
    exit 5
  fi
fi
exit "$code"
