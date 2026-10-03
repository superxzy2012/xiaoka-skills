# 小卡技能库 · xiaoka-skills

Hermes agent「小卡」的技能与工作流备份仓库（脱敏后）。

## 备份范围
- `skills/` — 全部技能（Hermes SKILL.md 格式）
- `memories/` — 记忆与脚本

**已排除**：`memories/cookies/`（登录态）、`MEMORY.md` / `USER.md` / `USER_PROFILE.md`（含个人信息）。

## 脱敏规则
- 手机号 → `【手机号】`
- 城市/区/大厦 → `【城市区】` / `【大厦】`
- 姓名/英文名 → `【BOSS姓名】` / `【BOSS英文名】`

未脱敏原件只在 NAS 本地私有仓，不公开。

## 关键技能
| 技能 | 作用 |
|---|---|
| `find-skills-xiaoka` | **造轮子前先查本机 + GitHub 开源**（含 `gh_pull.sh`、`backup_skills.sh`）|
| `ground-truth-discipline` | 引文回源校验（`verify_quote.py --selftest` 必 3/3）|
| `maoxuan-jinghua` | 毛选方法论蒸馏（229 篇，双校验器 PASS）|
| `kb-course-factory` | WorkBuddy 做课全流程（14 个 prompt）|

## 脚本
```bash
scripts/gh_pull.sh <owner/repo>          # 拉开源仓库（比裸 clone 快 60×）
scripts/gh_pull.sh -f <owner/repo> <路径> # 拉单文件
scripts/backup_skills.sh "msg"           # 脱敏 → 校验 → 提交 → push
```

## 自检
```bash
python3 skills/ground-truth-discipline/scripts/verify_quote.py --selftest   # 须 3/3
```
