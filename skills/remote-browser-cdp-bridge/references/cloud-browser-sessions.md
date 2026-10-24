# 租用云浏览器会话（换出口国家 + 一次性浏览器）

用于两类任务：

1. **目标服务按国家封锁**（「not available in your country」），本机/机场代理的出口过不了国家判定。
2. **需要一次性隔离环境**走注册流程，不想污染用户自己的浏览器，也不想让主账号沾上脏指纹。

前提：用户已经在该平台上登录（例如他本人在自己 Chrome 里注册过账号），你只需要从
**他的登录态**里取出 API key —— 取 key 的手法见 `in-page-secret-recovery.md`。

## API 形状（Hyperbrowser 实测）

```
POST https://api.hyperbrowser.ai/api/session
Authorization: Bearer <key>
{"useProxy": false, "useStealth": true, "adblock": true}
→ 200 {"id": "<uuid>", "wsEndpoint": "wss://…/cdp/devtools/browser/<uuid>"}

DELETE https://api.hyperbrowser.ai/api/session/<id>     # 结束会话，别让它挂着烧额度
```

- `wsEndpoint` 直接喂 `playwright.chromium.connect_over_cdp(ws)`；连上后页面挂在 `b.contexts[0]`。
- 猜路径的端点会返回 HTML `Cannot GET /api/team`。**404 证明服务可达，不证明 key 无效** ——
  先跑一次真正的建会话请求再判 key 死活。

## 三条硬规则

### 1. 建会话和用会话必须在同一个脚本里

会话在两次工具调用之间就会过期。把 `wsEndpoint` 存文件、下一轮再连，得到的是

```
404 {"code":"not_found","message":"session not found"}
```

这个报错长得像 key 失效或路径写错，其实只是会话没了。**一个脚本：建 → 连 → 干完所有事 → DELETE。**
中途需要人给验证码时，不要在两次调用之间断，而是在脚本里轮询一个本地文件（见下）。

### 2. 先最小 payload 探能力，别用「完整参数」一次梭哈

计划档位不支持某个字段时，接口回 **402 并在 message 里点名那个字段**：

```
402 {"error": "{\"message\":\"Free plan does not support use of proxies…\"}"}
402 {"error": "{\"message\":\"Free plan does not support solving captchas…\"}"}
```

去掉被点名的字段重试一次即可；**不要**在参数组合上反复试错，402 已经把答案写清楚了。

### 3. 出口国家必须自己验，不能靠假设

免费档没有代理时，出口来自**服务商自己的机房池**，不是住宅 IP。这仍然是一个真实国家：
实测某次落在 `datapacket.com` 圣何塞（US），足以让「按国家判定」的门槛放行，
而机房 IP（`hosting=true`）会被风控更严的站（支付、反欺诈、金融）继续拒绝。

先加载一个 IP 查询页读结果，再判定目标站是不是还封：

```python
page.goto("https://ipinfo.io/json")
print(page.inner_text("body"))     # 看 country / org
```

顺序是 **先验出口 → 再开目标站**。反了会把「IP 还是中国的」误读成「这个方案不行」。

## 换地区的判定标准

同一个目标页，在两个出口下对比：

| 出口 | 预期 |
|---|---|
| 封锁国家 | 出现地区限制提示 / 直接跳走 |
| 允许国家 | 正常渲染，出现注册表单或 Continue |

提示消失 = 国家门槛已过。**不要**在没做这个对比之前就断言方案不可行。

## 验证码类步骤：把会话挂在原地，轮询本地文件

验证码发到用户的邮箱/手机，你读不到。不要在两次工具调用之间断开重连（会话会死、码会过期），
而是让脚本停在验证码输入页等一个文件：

```python
for _ in range(90):                 # ~7.5 分钟
    if os.path.exists(CODE_FILE):
        code = open(CODE_FILE).read().strip()
        if len(code) >= 4:
            break
    time.sleep(5)
    page.title()                    # 轻量保活，顺便探测会话是否已死
```

**发起验证码之前就要把「我需要什么、多久失效」告诉用户**，然后才阻塞。反过来（先阻塞再等人问
「进度呢」）会把一次顺利的推进变成一次催促。

## 清理

会话按时间计费/计额度，`finally` 里无条件 `DELETE`：

```python
finally:
    if sid:
        api("DELETE", f"{API}/{sid}")
```

调试阶段可以先用 `useProxy:false` 建一个短会话只验出口，别拿正式流程试参数。

## 边界（别把没验过的当结论）

本文件覆盖的是「换出口 → 过国家门槛 → 走到验证码页」这一段，**已实测**。
之后的年龄验证、支付绑卡属于用户本人的物理动作或金融决策，不能替做，也不要在没有实测的情况下
写成流程。这类步骤的正确姿势是：把页面推到那一步 → 截图/读文本告诉用户有哪些选项 → 由他决定。
