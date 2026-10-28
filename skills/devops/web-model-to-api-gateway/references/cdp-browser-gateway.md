# 浏览器型上游网关（容器内 Chromium + CDP）

已验证实例：`bynne2602/muse2api` → muse.ai 网页会话转 OpenAI 协议（NAS 端口 18610）。

## 选型判据

- 上游没有可用协议逆向时，选「容器内真浏览器 + CDP 接管」的实现：网页改版它跟着点，比硬编码协议稳。
- 同域名的协议逆向版（如 `manishkumar1601/muse-ai-api`，Noise 协议）作者自己标了 fragile，不要选。

## 部署骨架

- 端口 18610；管理页 `/admin`；OpenAI 兼容 `/v1`。
- compose：`network_mode: host`、`shm_size: 2gb`、`mem_limit: 900m`、`./data:/app/data`、`restart: always`。
- 镜像约 965MB（Chromium + 字体），构建 5-10 分钟，**放后台**别前台等。

## 出网代理必须打进启动参数

容器里 Chromium 不读 `HTTP_PROXY` 环境变量，必须在 `--proxy-server` 里给。要改的地方（`engine.py`）：

1. 全局 `PROXIES`（优先 `MUSE2API_PROXY`，回退 `HTTPS_PROXY/HTTP_PROXY`）。
2. 会话探测 `requests.get(.../api/session, proxies=PROXIES)`。
3. 唤醒 `requests.post(.../api/hatch/vm/wake, proxies=PROXIES)`。
4. Chromium 启动参数插 `--proxy-server=http://host:port`——**剥掉 scheme**，Chromium 不认带 `http://` 的写法。
5. 媒体下载的 `urllib` 改 `build_opener(ProxyHandler(PROXIES))`。

改完 `python3 -m py_compile engine.py config.py app.py` 再 build。容器内 `127.0.0.1` 是它自己，代理要写宿主的局域网 IP。

## 登录：导入 cookie，不是扫码

1. 从 BOSS 浏览器 CDP **只读**取：`ctx.cookies("https://muse.ai")`——不导航、不 `bringToFront`、不抢前台焦点。
2. `POST /admin/accounts`，body `{"cookies": {name: value}, "expires": {name: unix_ts}, "label": "..."}`；返回 `added[].id` 与 `essential_missing`（必须为空）。
3. `POST /admin/accounts/{id}/test` → 期望 `{"ok": true, "message": "会话有效，可正常生成"}`。这步会在容器内真开一次浏览器，等 1-3 分钟。
4. 只有 test 通过才去测业务接口。

**UA 绑定不用预先防**：cookie 从 Windows Chrome 搬到容器 headless Chromium 实测直接可用，别急着加 `--user-agent` 对齐——先测，失败再考虑。

## 验收顺序（少一步就会误判）

1. `/v1/models` 带 key → 出现真实模型名，**读列表别猜**（muse：`muse-spark` / `muse-image` / `muse-video`）。
2. chat 一条 → `content` 非空（muse-spark 约 30-40 秒）。
3. **images 一条 → 真拿到图**：返回的是 `/v1/media/<id>.webp` 相对 URL，**必须带 `Authorization: Bearer <key>` 才下得动**，裸 curl 拿不到。校验字节数并用 PIL 打开看尺寸（实测 1920×1280 / 511KB）。
4. video 只验模型已注册；真跑费额度，等用户点头。

## 坑

- **别把 chat 测通当成全通**：画图/视频走不同模型名，传错会静默降级或直接报错。
- **媒体是相对路径**：桥端要拼 base 并附 key，否则回传出去的是空图。
- **`sed -i` 改 JS/JSON body 时引号转义不匹配会静默不生效**，改完必须 `grep -n` 确认目标行真的变了。
- 桥把上游的 webp 图回传飞书时，`im.image.create` 对 webp 的兼容性**尚未实测**——真出问题先转 png 再传，别怀疑上游。
