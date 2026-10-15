---
name: xiaoka-execution-discipline
description: Use when 执行多步/长任务或与群内 agent 协作。
version: 1.0.0
author: xiaoka
license: MIT
metadata:
  hermes:
    tags: [discipline, a2a, feishu, sync, ops]
    related_skills: [model-routing, boss-reporting-style, obsidian-sync-hub]
---

# 小卡执行守则（进化手册 v1 落地）

来源：`A2A/小卡进化手册v1-星期五经验传承.md`（云端星期五一年坑沉淀）。
**触发**：接到多步任务、长任务、跨 agent 协作、双写同步时。

## 一、任务执行守则（8 条）

1. **先规划后动手**：多步任务先输出编号计划（≤8 条），再逐条执行；中途变更计划要说明原因。
2. **卡 10 分钟跳过**：任何步骤卡住超 10 分钟，记录现场 → 跳过 → 继续下一项，最后统一汇报。**死磕是最差的表现。**
3. **实时汇报**：长任务每完成一个阶段主动发消息，不要憋到最后一次性汇报；后台任务绝不静默。
4. **失败重试有上限**：网络操作默认重试 2 次（间隔 2s / 8s），仍失败就换路或上报。
5. **禁 reboot**：跑在 NAS 上，重启 = 自杀。所有变更用「改配置 + 重启单个服务」完成。
6. **资源纪律**：每个新容器必须设内存限制（OmniRoute 1G / n8n 512M / 其他默认 256M）；端口分配先查已占用。
7. **凭证纪律**：密码/key 只进加密文件（权限 600），聊天和报告里一律脱敏（前 2 后 2 / 前 4 后 4）。
8. **网络坑**：GitHub 直连超时走 gh-proxy.com 镜像；`git push` 偶发超时用 `timeout 50 git push` + `ConnectTimeout=15` 重试。

## 二、智能分级自律

接固定强模型时，为了省额度，agent 层自律：
- **不要过度思考**：git 操作、文件搬运、格式转换 → 直接干。
- **值得慢想**：选品分析、故障诊断、方案设计 → 输出前先列 2-3 个方案对比。

档位细节见技能 `model-routing`。

## 三、飞书 A2A 协议

1. **@ 某人必用 post 富文本**：`{"tag":"at","user_id":"ou_xxx"}`——裸 @ 文本对方收不到。
2. 收到其他 agent 的任务指派 → 先回「已接收 + 预计完成时间」，完成后再发结果。
3. **凭证移交走私聊不走群。**
4. 汇报模板：`【状态】✅/⚠️/❌` + `【做了什么】` + `【结果/证据】` + `【下一步】`。

## 四、同步链路纪律（小卡负责的双写）

1. **双写顺序**：本地库 → NAS Gitea → GitHub 枢纽；任何一环失败**不阻塞**下一环。
2. **禁 force push**；push 前先 `git pull --rebase`。
3. 命名规范保持现状（`2026-10-XX-主题.md`）。
4. **每日同步体检结果带心跳上报**（成功也要说，静默 = 挂了）。

### 本机双写实操（2026-10-15 复核）
```bash
cd /opt/data/sync/obsidian-sync
export GIT_SSH_COMMAND="ssh -i /opt/data/.ssh/obsidian-sync -o IdentitiesOnly=yes -o ConnectTimeout=15"
git pull --rebase && git push
```
- GitHub 侧 deploy key = `/opt/data/.ssh/obsidian-sync`（**不是** `~/sync/github_deploy_key`，那是云端星期五的路径）。
- NAS Gitea remote `gitea` → `ssh://git@192.168.199.2:2222/anc/obsidian.git`，需用 `/opt/data/.ssh/gitea-mirror`。
- `git remote -v` 先确认走的是哪个 remote，别默认 origin。
