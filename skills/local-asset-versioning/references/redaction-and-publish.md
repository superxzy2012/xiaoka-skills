# 脱敏与发布配方

## 占位符表

替换必须用**统一中文占位符**，便于日后对照原值核查：

| 类别 | 占位符 |
|---|---|
| 手机号 | `【手机号】` |
| 姓名 | `【BOSS姓名】` |
| 英文名 | `【BOSS英文名】` |
| 城区 | `【城市区】` |
| 写字楼 | `【大厦】` |

正则参考：`1[3-9]\d{9}`。注意账号类数字（如订单号、仓库 ID）不要误伤——
只脱敏明确识别为人名的字段，宁可漏脱敏也不要破坏技术内容。

## 目录排除清单

按路径片段或文件名排除，**整目录排除优先于逐文件脱敏**：

```
cookies/                      ← 登录态，永不上网
__pycache__/  .cache/  node_modules/
.venv/  .venv-browser/  .playwright-browsers/
*.pyc
任何嵌套的 .git/              ← 见 SKILL.md 的 rsync 坑
```

单文件排除（个人信息密度最高）：`MEMORY.md`、`USER.md`、`USER_PROFILE.md`。

## 远端二次校验

本地暂存区干净不代表远端干净。上线后抽查：

```bash
# 列出远端文件树，确认被排除的目录确实不存在
gh api "repos/<owner>/<repo>/git/trees/main?recursive=1" \
  --jq '.tree[] | select(.type=="blob") | .path' | grep -E 'cookies/|MEMORY\.md'

# 抽查内容脱敏（读回再验，不是信任本地）
gh api repos/<owner>/<repo>/contents/<path> \
  | python3 -c "import sys,json,base64;print(base64.b64decode(json.load(sys.stdin)['content']).decode())" \
  | grep -nE '1[3-9][0-9]{9}'
```

## 仓库门面

公开仓要自带说明，否则未来自己都看不懂：

- `README.md`：备份范围（写明排出了什么）、脱敏规则表、关键技能表、校验命令
- `.gitignore`：`__pycache__/`、`*.pyc`、`.DS_Store`

README 里**不要**写原始个人信息，只写「原件在 NAS 本地私有仓，不公开」。

## 首次建仓的顺序

1. 先在本地建仓并提交（此时没有任何远端风险）
2. 配 remote（`git remote add`），确认 `git remote get-url origin` 有输出
3. 配 `credential.helper store`，凭据写 `~/.git-credentials`（600）
4. `gh api repos/... --jq '.size'` 确认 push 真的生效
5. 建公开仓：`gh repo create <name> --public --source <local> --remote origin --push`
   （若 remote 已存在，改用 `git remote add` + `git push -u origin main`）

## 已知 scope 限制下的替代路径

`public_repo` 无法建私有库时，不要索要更高权限 token。替代方案：

- 双份仓（NAS 原件 + 公开脱敏件），本 SKILL.md 的默认策略
- 需要更强隐私时，请用户在网页建好**空的私有仓**，再由脚本 push 进去