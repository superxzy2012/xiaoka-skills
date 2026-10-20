---
name: web-clone-mirror
description: Use when 要把某个网站完整克隆成本地可跑的静态站。SPA/SSG 全量镜像 + 像素验收。
---

# 网站克隆（镜像法）

对 Vite/React/Next 这类有真实构建产物的站，**镜像优于 AI 重生成**：保住逐像素一致。
AI 重写（open-lovable 路线）只适合拿不到源码的站。

## 流程

1. 侦察：确认框架（看 `index.html` 里 hash 化文件名 = Vite/React SPA）
2. 从 DOM 的 `a[href]` 提取同站路由，别猜 sitemap
3. 逐路由滚动采集（懒加载 chunk 只在滚动后请求），资源量通常是首页的 2 倍以上
4. 下载同源资源 + CDN 素材，把 CDN 绝对地址改写成站内相对路径 `/web-assets/cdn/<host>/<path>`
5. 每条路由单独抓 `<route>/index.html`（SSG 站每个入口有独立 HTML，SPA fallback 会渲染错）
6. 切追踪：GTM / GA / Clarity / 百度 / Bing / DoubleClick
7. 本地起 SPA 服务器验证，再部署
8. 逐路由像素比对（1440×900 首屏 + 整页高度），高度 delta 必须为 0

## 三个必踩的坑

### gzip 未解压（最隐蔽）
`urllib` 不发 `Accept-Encoding` 时，CDN 对 `.json` 可能直接返回 gzip 字节。落盘后 nginx 以 `application/json` 明文返回，浏览器解析失败 → **某块内容静默塌陷**，页面高度少几百 px 但无任何报错。

检测：文件头 `1f 8b` 就是 gzip。修：`gzip.decompress` 后覆盖。
扫描所有 `.json/.js/.css/.html/.svg`，不要只看报错的。

### 中文文件名被存成百分号字面名
`%E4%B8%8D...webp` 落盘成字面名，但 HTTP 请求解码成中文名 → 404。
修：`p.rename(urllib.parse.unquote(p.name))`。

### bind mount 目录被删重建后容器 500
`rm -rf` + `mkdir` 同一路径后，容器仍指向旧 inode，`nginx -s reload` 没用，**必须 `docker restart`**。

## 验收判据

- 每条路由：`document.body.scrollHeight` 与原站 **delta = 0**
- 像素 diff：`diffPixelRatio` 多数为 0，少数 <1%（轮播/动图帧差，非布局错误）
- 滚动到底后：0 破图、0 HTTP≥400、0 console error
- 破图检测必须在**滚动到底之后**统计，否则懒加载未进视口的图全是假阳性

## 部署

先加一个包装器，否则后台/定时任务必挂：

```sh
#!/bin/sh
export PLAYWRIGHT_BROWSERS_PATH=/opt/data/.playwright-browsers
cd "$(dirname "$0")" || exit 1
exec node "$@"
```

后台进程与 cron **不继承** shell 的 `PLAYWRIGHT_BROWSERS_PATH`，Playwright 会去 `/opt/hermes/tools/` 找浏览器并报 `Executable doesn't exist`。前台跑得好好的、后台全挂就是这个原因。

nginx:alpine + 自定义 `try_files`：

```nginx
location / {
    try_files $uri $uri/index.html /index.html;
}
```

不要写 `$uri/` —— 匹配到目录会 301 加斜杠，改变 URL。

## 参考

方法论来源 `Jane-xiaoer/claude-skill-web-clone`（含 `recon-site.mjs` / `mirror-site.mjs` / `visual-diff.mjs`）。
实测案例：linkfox.com 10 路由 82MB 619 文件，7 路由像素零差异。工程在 `/opt/data/projects/website-clones/`。
