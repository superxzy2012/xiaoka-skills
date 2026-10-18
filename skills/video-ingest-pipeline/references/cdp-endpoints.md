# CDP 端点：选哪个、怎么自检、什么时候会失败

抖音解析只有一条活路——借真浏览器的页面上下文发 `aweme/detail`。端点选择因此是整条管线的单点。

## 端点表

| 端点 | 载体 | 登录态 | 解析耗时 | 适用 |
|---|---|---|---|---|
| `http://192.168.199.2:9222` | NAS 上 `cdp-chrome` 容器，headless Chrome 124 | 有（profile 持久化，与 Windows 同一个号） | ~9s | **默认**，不依赖用户机器 |
| `http://192.168.199.184:9224` | 用户 Windows 上的 Chrome | 有 | ~5.2s | 兜底 |
| `$CDP_URL` | 任意 | — | — | 临时覆盖，优先级最高 |

`memories/cdp.py` 的 `pick_url()` 按上表顺序探测 `/json/version`（2.5s 超时），选中即用；
`dy_cdp._capture_detail()` 在端点上再套一层重试，一个端点抛错自动换下一个。**别在调用处写死 URL。**

## 登录态：先探测，别先登出

profile 挂在 `/volume2/2-AI/cdp-profile`，扫码一次之后**跨容器重启、跨 NAS 重启都在**。所以
「用户说要扫码」时第一步是**验证是否已经登录**，不是直接去开登录框 —— 先登出会把这份持久化状态清掉。

```python
c = CDP(); c.new_tab("about:blank", background=True)
c.goto("https://www.douyin.com/user/self", wait=9)
c.eval_js("(()=>location.href)()")      # 停在 /user/self = 已登录；跳登录页 = 未登录
c.eval_js("(()=>document.title)()")     # 已登录时标题就是本人昵称
ck = c.cookies("douyin.com")            # dict；含 sessionid / sid_tt / uid_tt = 会话有效
```

判定顺序：`/user/self` 是否渲染本人主页 → cookie 里有没有 `sessionid` → 才考虑重新扫码。
两个端点一起比（NAS vs Windows）能立刻看出是不是同一个号。

cookie 文件（给 yt-dlp 用）从当前 CDP 端点重导：

```bash
/opt/data/.venv-browser/bin/python /opt/data/memories/refresh_douyin_cookies.py
# 期望：导出 70+ 条，含 sessionid / sid_guard / uid_tt
```

**首页不能用来判断登录态。** `https://www.douyin.com/` 302 到 `https://www.douyin.com/jingxuan`
（抖音精选电脑版），该页既无「登录」按钮也无二维码元素 —— 在这里找 `img[src^="data:"]` / canvas
只会得到空列表，据此报「未登录且找不到入口」是假结论。

换号（换成用户的另一个抖音号）属于另一件事：不要登出当前 profile，另开一个 browser context 扫码再
把 cookie 注入默认 context；这条路径未实测，动手前先小样本验证，别直接在生产 profile 上试。

## 自检

```bash
curl -s -m 8 http://192.168.199.2:9222/json/version   # 要看到 Browser + webSocketDebuggerUrl
curl -s -m 8 http://192.168.199.2:9222/json/list | head -c 300
```

容器本身（NAS 走 SSH，`sudo -n` 只免密 docker）：

```bash
ssh -i /opt/data/.ssh/id_ed25519 DY@192.168.199.2 \
  "sudo -n /usr/bin/docker inspect cdp-chrome --format 'restart={{.HostConfig.RestartPolicy.Name}} cmd={{.Config.Cmd}} mounts={{range .Mounts}}{{.Source}}:{{.Destination}} {{end}}'"
```

已知良好配置：`restart=unless-stopped`，`--remote-debugging-address=0.0.0.0 --remote-debugging-port=9222`，
`--user-data-dir=/data` 挂到 `/volume2/2-AI/cdp-profile`（登录态跨重启保留），
`--disable-blink-features=AutomationControlled`，`--user-agent` 设成桌面 Windows Chrome。
镜像 `zenika/alpine-chrome`（NAS 上已有三个源的同标签镜像）。

## 能力边界

- **公开视频：无需登录。** 页面 JS 自己生成 ttwid/msToken，headless 一样 200。
- **登录态解锁的是「自己账号能看的」，不是「别人的私密作品」。** 登录成任何号都拿不到
  别人设为私密/仅自己可见的作品——`filter_reason: status_self_see` 是作品权限，不是登录缺失，
  换端点、换 cookie、重试全部无效。判据始终是 `filter_detail.filter_reason` 有没有值。
- **后台标签必须 `background=True` 且开 focus emulation**，否则 Chrome 节流渲染，主页虚拟列表停在第一屏。
- headless 渲染比带界面 Chrome 慢，列表滚动每轮新增更少（18 vs 36~54 条），但结果一致。
