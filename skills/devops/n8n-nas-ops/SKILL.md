---
name: n8n-nas-ops
description: Use when 运维 NAS n8n：建改跑 workflow、写文件报错、激活/删除 400。
version: 1.0.0
license: MIT
author: 小卡
metadata:
  hermes:
    tags: [n8n, nas, docker, workflow, omniroute, automation]
    related_skills: [omniroute-gateway-ops, nas-docker-deploy]
---

# NAS n8n 无头运维（REST API 操作 + 三坑）

## When to Use

- 要在 NAS n8n（`http://192.168.199.2:5679`）建/改/跑 workflow，且不想开浏览器点。
- n8n 写文件节点报 `Access to the file is not allowed` 或 `The file or directory does not exist`。
- 激活 workflow 报 `invalid_type versionId`，或删除 workflow 报 `Workflow must be archived before it can be deleted`。
- 探测网关模型可用性、做定时健康快照。

## 环境坐标

| 项 | 值 |
|---|---|
| n8n | `http://192.168.199.2:5679`（容器 `n8n`，镜像 `n8nio/n8n:2.43.5`） |
| compose | 宿主 `/volume2/2-AI/n8n/docker-compose.yml` |
| 数据卷 | `/volume2/2-AI/n8n/data:/home/node/.n8n` |
| 输出卷 | `/volume2/2-AI/n8n/pool-health:/files` |
| OmniRoute 凭据 | 名 `OmniRoute NAS (xiaoka)`，id `NdDNAN4JHTOK5eq5`，类型 `httpHeaderAuth` |
| 登录 | `n8n-admin@xiaoka.local` + 密码取自容器 env `N8N_BASIC_AUTH_PASSWORD` |

## 无头操作骨架

```python
PW = subprocess.run(SSH + ["sudo -n docker exec n8n printenv N8N_BASIC_AUTH_PASSWORD"],
                    capture_output=True, text=True).stdout.strip()
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj),
                                 urllib.request.ProxyHandler({}))  # 必须禁代理
op.open(Request(N8N+"/rest/login", data=json.dumps(
    {"emailOrLdapLoginId":"n8n-admin@xiaoka.local","password":PW}).encode(),
    headers={"Content-Type":"application/json"}))
```

- 建：`POST /rest/workflows` body `{name, nodes, connections, settings:{executionOrder:"v1"}}` → `data.id`
- 跑：`POST /rest/workflows/{id}/run` body `{workflowData: <GET /rest/workflows/{id} 的 data 字段>, runData: {}, triggerToStartFrom: {name: "<触发器节点名>"}}` → `data.executionId`
- 读执行：`GET /rest/executions/{eid}?includeData=true`，返回 `data.data` 是 **n8n 压缩格式**（数组 + 字符串下标引用），需递归解析才能看节点结果。
- **列表接口返回形状不一致**：`/rest/workflows` 的 `data` 直接是 list，`/rest/executions` 的 `data.results` 才是 list。解析要兼容两者，否则 `'list' object has no attribute 'get'`。

## 三个必踩坑

1. **写文件被沙箱拦**：n8n 2.x 默认禁止 Code/File 节点访问 `.n8n` 目录，报 `Access to the file is not allowed`。
   - ❌ 别写 `/home/node/.n8n/...`
   - ✅ 挂独立卷 + 加白名单：compose 加 `- /volume2/2-AI/n8n/pool-health:/files` 与环境变量 `N8N_RESTRICT_FILE_ACCESS_TO: "/files"`，然后 `docker compose up -d --force-recreate`。
   - 卷目录**必须先在宿主存在**（`mkdir` + `chown 1000:1000`），readWriteFile 不建目录，否则报 `ENOENT / The file or directory does not exist`。
2. **Code 节点禁 `require`**：`Module 'fs' is disallowed [line 2]`。写文件一律走 `n8n-nodes-base.convertToFile`(toText) → `n8n-nodes-base.readWriteFile`(write, dataPropertyName="data")，别在 Code 里 `require('fs')`。
3. **HTTP 节点吞掉上游字段**：HTTP Request 默认只输出响应体，上游 `model`/`label` 会丢；`options.response.response.includeInputFields` 实测**不生效**。
   - ✅ 最稳做法：上游 Code 用带前缀字段名（`target_model`），下游 Code 里用**静态清单按索引配对**（`MODELS[i]`），不依赖节点选项。

## 生命周期端点（2.43.5 实测）

| 操作 | 端点 | 坑 |
|---|---|---|
| 激活 | `POST /rest/workflows/{id}/activate` body `{versionId: "<当前 versionId>"}` | 不传 versionId → 400 `invalid_type` |
| 删除 | `DELETE /rest/workflows/{id}` | 必须先 `POST /rest/workflows/{id}/archive`，否则 400 `must be archived` |

## 验证纪律

- 改完 workflow 一定**真跑一次**（`/run`）并读执行记录，别只看 `create -> 200`。
- 产物要落到可核对的物理位置（`/files/snapshot-*.md`），用 `cat` 看内容，别信节点返回的 `success`。
- 幂等：建之前先按 name 扫一遍，删旧的（归档+删除），否则会攒一堆同名 workflow。
