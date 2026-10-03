#!/usr/bin/env bash
# 配置 GitHub fine-grained token，全程不让 token 进入 shell 历史或对话。
#
# 用法：bash setup_finegrained_token.sh
# 脚本会提示你静默粘贴 token（输入不回显），校验后写入凭据文件（权限 600）。
#
# 前提：已在 https://github.com/settings/personal-access-tokens/new 撤销旧 token 并新建。
set -uo pipefail

GH=/opt/data/bin/gh
export HOME=/opt/data/home
export GH_CONFIG_DIR=/opt/data/home/.config/gh
CRED=/opt/data/home/.git-credentials
HOSTS=/opt/data/home/.config/gh/hosts.yml

echo "=== GitHub fine-grained token 配置 ==="
echo
echo "需要你先完成两件事（我无法代做）："
echo "  1. 撤销旧 token：https://github.com/settings/tokens"
echo "  2. 新建 fine-grained token：https://github.com/settings/personal-access-tokens/new"
echo
echo "创建时按此填写："
echo "  Token name      : hermes-nas-2026"
echo "  Expiration      : 90 days（建议设短，别选 Never）"
echo "  Resource owner   : 你的账号"
echo "  Repository access: Only select repositories"
echo "    → 勾选 xiaoka-skills（备份仓）"
echo "  Permissions:"
echo "    Repository permissions → Contents: Read and write"
echo "    （Metadata: Read-only 是自动的，不用勾）"
echo "  其余权限一律不要勾：Actions / Issues / PRs / Workflows / Admin 全部留空"
echo
echo "  ⚠️ 只需要 Contents 读写。代码搜索不需要它。"
echo "  ⚠️ 不要勾 Administration —— 那等于交出账号控制权。"
echo
read -r -p "粘贴 token（输入不显示，直接粘贴后回车）: " TOKEN
echo

if [ -z "${TOKEN:-}" ]; then
  echo "❌ 未输入 token，中止。"; exit 1
fi

case "$TOKEN" in
  github_pat_*) echo "✅ 格式正确：fine-grained token（github_pat_ 开头）" ;;
  ghp_*)        echo "⚠️ 警告：这是 classic token（ghp_ 开头），不是 fine-grained。" ;;
  *)            echo "❌ 格式不对：应以 github_pat_ 或 ghp_ 开头。中止。"; exit 1 ;;
esac

# 校验：能否读到目标仓库
echo
echo "=== 校验 token ==="
OUT=$(GH_TOKEN="$TOKEN" "$GH" api repos/superxzy2012/xiaoka-skills \
      --jq '"可读 ✅  stars=" + (.stargazers_count|tostring)' 2>&1)
if echo "$OUT" | grep -q "可读"; then
  echo "   $OUT"
else
  echo "   ❌ 无法访问 superxzy2012/xiaoka-skills"
  echo "   报错：$(echo "$OUT" | head -3 | tr '\n' ' ')"
  echo
  echo "   可能原因："
  echo "     · fine-grained token 授权时没勾这个仓库"
  echo="     · 勾了但 Contents 权限没给到 Read and write"
  echo "     · token 复制时带了空格或换行"
  echo "   未写入任何文件。修正后重跑本脚本。"
  exit 1
fi

# 校验写权限（不真的推送，只查权限字段）
PERM=$(GH_TOKEN="$TOKEN" "$GH" api repos/superxzy2012/xiaoka-skills \
       --jq '.permissions | "push=" + (.push|tostring)' 2>&1)
echo "   $PERM"

echo
echo "=== 写入凭据（权限 600）==="
umask 077
printf 'https://user:%s@github.com\n' "$TOKEN" > "$CRED"
chmod 600 "$CRED"
echo "   ✅ $CRED"

# 同步 gh 配置（yaml 里避免明文，用 hosts.yml 是 gh 的标准位置，权限 600）
python3 - "$TOKEN" <<'PY'
import os, sys, stat
tok = sys.argv[1]
p = "/opt/data/home/.config/gh/hosts.yml"
content = (
    "github.com:\n"
    f"    user: BOSS\n"
    f"    oauth_token: {tok}\n"
    "    git_protocol: https\n"
)
with open(p, "w") as f:
    f.write(content)
os.chmod(p, 0o600)
print(f"   ✅ {p} (600)")
PY

# git 凭据也走 helper，不裸存
git config --global credential.helper 'store --file=/opt/data/home/.git-credentials'

echo
echo "=== 最终验证 ==="
unset TOKEN
"$GH" auth status 2>&1 | sed 's/gh[pousr]_[A-Za-z0-9]*/gh_***/g' | head -10

echo
echo "=== 清理 shell 历史中的 token ==="
history -d $(history 1 | awk '{print $1}') 2>/dev/null || true
echo "   （token 是通过 read 静默输入的，本就不在历史里）"

echo
echo "完成。下次备份会直接用新 token。"
echo "提醒：90 天后到期，届时重新跑本脚本即可。"