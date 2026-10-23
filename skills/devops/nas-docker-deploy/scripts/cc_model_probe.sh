#!/usr/bin/env bash
# 验证「某个模型能否真正驱动 Claude Code 的工具」，在 claude-code 容器内执行。
#
# 用法：
#   docker cp cc_model_probe.sh <container>:/tmp/cc_model_probe.sh
#   docker exec <container> bash /tmp/cc_model_probe.sh <model_id> [<model_id> ...]
#
# 判据只有一条：文件是否真的落盘。API 层 /v1/messages 返回 tool_use 不算数。
# 先跑 CONTROL_MODEL（已知可用）作对照：对照也 NO_TOOL = 容器环境问题，不是模型问题。
set -u

PROBE_TIMEOUT="${PROBE_TIMEOUT:-180}"

probe() {
  local m="$1"
  local tag f t0 t1 out
  tag=$(printf '%s' "$m" | tr '/:.' '____')
  f="/tmp/ccprobe_${tag}_$$.txt"
  out="/tmp/ccprobe_${tag}_$$.log"
  rm -f "$f"
  t0=$(date +%s)
  timeout "$PROBE_TIMEOUT" claude -p "Use the Bash tool to run exactly this command: echo TOOL_OK > $f
Then reply with only: done" --model "$m" --dangerously-skip-permissions >"$out" 2>&1
  t1=$(date +%s)
  if [ -s "$f" ]; then
    printf '%-54s TOOL_OK  %4ss  %s\n' "$m" "$((t1 - t0))" "$(cat "$f")"
  else
    printf '%-54s NO_TOOL  %4ss\n' "$m" "$((t1 - t0))"
    # 尾部一行有助于区分「权限被拦」和「模型不会用工具」
    [ -s "$out" ] && printf '    %s\n' "$(tail -1 "$out" | cut -c1-160)"
  fi
  rm -f "$f" "$out"
}

if [ "$#" -eq 0 ]; then
  echo "usage: $0 <model_id> [<model_id> ...]" >&2
  exit 2
fi

echo "--- control (known-good) ---"
probe "${CONTROL_MODEL:-vecp/glm-5.2}"

echo "--- candidates ---"
for m in "$@"; do probe "$m"; done

echo
 echo "TOOL_OK = 能驱动 Claude Code 工具；NO_TOOL = 只会聊天，不要写进 ANTHROPIC_MODEL"
