# Octop 能力面（摸排结果 + 复现命令）

BOSS 说「想最大化利用」时要的不是功能罗列，是**这张面 + 缺口清单**。每次大版本升级后重跑一遍摸排。

## 1. 复现摸排

```bash
# 全量路由（容器内）
ssh DY@192.168.199.2 "sudo -n docker exec octop sh -c 'grep -rhoE \"(router|app)\\.(get|post|put|delete)\\(\\\"/[^\\\"]*\\\"\" /app/src/octop/api | sort -u | wc -l'"
# 各面数量
GET /api/subagent-catalog/divisions      # 子代理按 division 计数
GET /api/connectors/catalog              # 连接器 + auth_kind
GET /api/plugins/market                  # 插件（已装标 INSTALLED）
GET /api/acp                             # ACP runner 状态
GET /api/usage/summary                   # 真实 token 成本
```

## 2. 量级基线（1.0.2 实测）

| 面 | 数量 | 说明 |
|---|---|---|
| API 路由 | 270 | 能力上限远大于控制台暴露的菜单 |
| 子代理 | 272 | 按 division 分组，需逐个 install 才可用 |
| 连接器 | 27 | 分 OAuth / API Key 两类鉴权 |
| 插件 | 27 | 可全装，互不冲突 |
| ACP runner | 7 | 默认全关，装 Node 后可开 |

## 3. 子代理 divisions

工程 42、营销 40、专业 57、销售 9、产品 5、学术 6、设计 9，另有金融/法务/供应链/研究/运营分组。

**挂载原则：按岗位挂，不全挂。** 272 个全挂会把每个专家的 prompt 撑爆，且大量条目与业务无关。业务对口的优先：

| 专家 | 已挂 |
|---|---|
| 小安（合规） | 合同审查 / 制度文件 / 风险评估 / AI 治理 / Ozon 工厂货源适配 |
| 小热（热点） | 中国市场本地化 / TikTok / SEO |
| 老钱（证券） | 投资研究 / 财务分析 / 金融风控 |
| 小办（办公） | 会议效率 / ZK 知识管家 |
| 阿文（一文多发） | 内容创作 / 中国电商运营 / 完美复刻写作 |
| 小维（运维） | MCP 构建者 |
| 小调（编排） | 供应商评估 / 库存预测 / 动态定价 / 中国电商全平台搜索 |

## 4. 连接器鉴权分型（决定能不能用）

`GET /api/connectors/catalog` 看两个字段：`auth_kind`、`oauth_ready`。

- **OAuth 型**（企查查 / 元典 / 飞书 / 腾讯文档 / 微信读书 / 出行类）：回调必须公网 HTTPS 或 localhost。**NAS 无公网 → 优先走同厂 API Key 路线**，别在 OAuth 上耗时间。
- **API Key 型**：直接填，最省事。
- **同一飞书应用只能有一个长连接**：Octop 要接飞书必须另建 app_id/secret，不能复用现有 bot。

## 5. 缺口清单的三段式（交付形态）

| 段 | 内容 |
|---|---|
| 我自己装好的 | Node / 插件 / Chromium / 决策模型 / 子代理 / 技能 —— 附实测结论，不写「应该可以」 |
| 必须 BOSS 出手 | 按 🔴 阻塞业务 / 🟡 提升效率 / 🟢 锦上添花 分级，每条写「不给会缺什么」 |
| 建议不做 | 开公网、装桌面 VNC、把个人信息灌进专家 —— 附理由，别默认全上 |

## 6. 成本真相

`GET /api/usage/summary` → 62,399 tokens/轮，缓存命中 77%，真新增约 7k/轮。**Octop 不比蜂群便宜**，它的价值在「不占主上下文 + 共享知识库 + 按需雇专家」，不在省 token。对外论证按这个口径讲，别拿成本当卖点。
