# grok.com Automations 内部 REST 接口

免费 xAI 账号实测全部可用。**所有调用都在已登录页面内用同源 `fetch` 执行**（cookie 在 context 里，不用自己拼 Authorization）：

```python
page.evaluate("""async ([p,m,b]) => {
    const o = {method:m, headers:{'content-type':'application/json'}};
    if (b !== null) o.body = JSON.stringify(b);
    const r = await fetch(p, o);
    return {s:r.status, t:(await r.text()).slice(0,4000)};
}""", [path, method, body])
```

## 端点

| 动作 | 方法 + 路径 | 说明 |
|---|---|---|
| 列表 | `GET /rest/automations` | 返回 `{automations:[{taskId, content:{name,prompt}, isActive, schedules, triggers}]}` |
| 建任务 | `POST /rest/automations` | body 见下；成功返回完整任务对象（含 `taskId`） |
| 立即跑 | `POST /rest/automations/{taskId}/run` | 200 即已入队；不等结果 |
| 查运行 | `GET /rest/automations/{taskId}/runs` | `{runs:[{taskResultId, status, conversationId, createTime, title}]}` |
| 取正文 | `GET /rest/app-chat/conversations/{conversationId}/responses` | `{responses:[{sender:'ASSISTANT', message:'...'}]}` |
| 删除 | `DELETE /rest/automations/{taskId}` | 200 即删 |

`GET /rest/automations/{id}/runs/{taskResultId}`、`/rest/conversations/{cid}` 都是 **404**，别试。答案正文只能走 `app-chat/conversations/{cid}/responses`。

## 建任务请求体

```json
{
  "content": {
    "name": "FS-xxxx",
    "prompt": "任务正文",
    "notificationMethod": "DEFAULT",
    "modeId": "fast",
    "icon": "l:zap:inherit",
    "workspaceId": ""
  },
  "triggers": [],
  "schedules": [{
    "taskCadence": "TASK_CADENCE_ONCE",
    "isEnabled": true,
    "timezone": "UTC",
    "timeOfDay": "09:00",
    "dayOfYear": "2026-10-29"
  }]
}
```

- `schedules` 不能为空数组：报 `an automation needs a schedule, triggers, or both`。只想立即跑也要塞一个未来的 ONCE 占位。
- 缺 `content` 包装：报 `content is required [WKE=automation:missing-field:content]`。
- 周期值：`TASK_CADENCE_ONCE` / `TASK_CADENCE_DAILY` / 以及 hourly/weekly/monthly/yearly 同族命名；daily 用 `timeOfDay`，once 用 `timeOfDay` + `dayOfYear`。
- `timezone` 填 `UTC`，`timeOfDay` 按 UTC 给，别塞北京时间。

## 运行状态

`TASK_RESULT_PENDING` → `TASK_RESULT_SUCCESS`（失败是 `TASK_RESULT_FAIL*`）。`execTime` 单位毫秒。

成功 run 的字段只有：`taskResultId / title / conversationId / status / createTime / updateTime / isRead / execTime / notificationDecision / taskId`。**没有正文字段。**

## 触发器

`triggers:[]` 时走纯 schedule。UI 支持的触发器类型（如需程序化建，抓一次 UI 的 POST body 照抄结构）：Once / Hourly / Daily / Weekly / Monthly / Yearly、Gmail 新邮件、Outlook、GitHub PR。

## 任务菜单等价操作

UI 的 `More automation actions` 菜单 = Edit / Pause / Run now / Delete，对应 REST 就是 PATCH（未逆向）/ 改 `isActive` / `/run` / DELETE。
