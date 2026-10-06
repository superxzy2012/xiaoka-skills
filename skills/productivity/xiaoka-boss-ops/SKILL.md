---
name: xiaoka-boss-ops
description: 小卡 BOSS 运维：A股播报/抖音入库/天气/知识库。
version: 1.0.0
author: 小卡 (Hermes)
license: MIT
metadata:
  hermes:
    tags: [A股, 抖音, Obsidian, cron, NAS]
    related_skills: [obsidian]
---

# 小卡 · BOSS 日常运维

## When to Use
写 NAS Obsidian 库、抓 A股 行情、抖音视频入库、建/调 cron 定时任务时，先读本 skill。
关键坑：写 NAS 要两步、东方财富源不可用、cronjob_manage 不支持 skills 参数与本地工具批量。

## 关键路径
| 用途 | 路径 |
|---|---|
| Hermes home（可写） | `/opt/data` |
| Obsidian vault（NAS） | `/opt/nas/volume2/2-AI/obsidian_vault` |
| 小卡工作区 | `<vault>/15-小卡工作区/{A股实盘,抖音采集,生活服务,记忆快照}` |
| 4 层记忆 | `/opt/data/memories/{AGENT_SOUL,USER_PROFILE,PROTOCOLS,KB_INDEX}.md` |
| A股脚本 | `/opt/data/memories/astock_reporter.py` |
| 抖音模板 | `/opt/data/memories/templates/douyin_note.md` |

## ⚠️ 写 NAS 必须走两步
`HERMES_WRITE_SAFE_ROOT=/opt/data`，`write_file`/`patch` 直接写 NAS 会被拒。
**规则**：先 `write_file` 到 `/opt/data/...`，再 `cp` 到 NAS。`terminal` 直接写 NAS 不受此限。
旧库写权限已验证 OK（`1000:uucp` 全权）。

## 音频转写（2026-10-01 建成并实测）

### 🔴 云端转写三条硬约束（2026-10-05 实测补充）

1. **选型：`whisper-large-v3-turbo`（`--model turbo`）是默认正解** —— 最便宜且准确率够用。
   实测 41 分钟音频 = **$0.0082**（约 $0.0000033/秒），139 条 12 小时内容约 **$0.14**。
   本地 `small` 免费但**错 3 字**（证→正、十一→亿、深证→深圳），专有名词不可用。
2. **HTTP 413 Payload Too Large** —— OpenRouter 单请求上限约 25MB，长音频必炸。
   `transcribe.py` 已内置切片（`MAX_UPLOAD=20MB` / `SEG_SEC=600`），超长自动分段转写再拼接，
   日志显示 `cloud/turbo x5`。**新增长音频需求不需要自己写分段。**
3. **不要用「转写字数 > 150」当成功判据** —— 1 分 19 秒的短视频转出来只有 79 字，
   是完全正常的结果。阈值定 150 会把正常短片误判为失败。
   用 **> 60 字**（实测 1 分钟以下的口播片约 50-80 字）。

### 批量入库脚本（2026-10-05 新增）

| 脚本 | 作用 |
|---|---|
| `memories/bili_mercado.py` | B站多关键词搜索 + 年份过滤 → 候选池 JSON |
| `memories/mercado_batch.py` | 批量下载 → 字幕优先/turbo兜底 → 写 vault 笔记（断点续跑）|

`mercado_batch.py` 判成功看**笔记文件是否落盘**（`*-{bvid}.md`），不看进程退出码。
**路由器** = `/opt/data/memories/transcribe.py`（云端主力 + 本地兜底，自动降级）
```bash
/opt/data/.venv-browser/bin/python /opt/data/memories/transcribe.py <音频> [--model auto|turbo|qwen|whisper1|local] [--json]
```
- `auto`（默认）= 云端 turbo 失败自动切本地 small
- 云端成本：turbo $0.0000237/7秒；qwen 准确率最高但贵 10 倍
- **实测对比同一段中文**：turbo 错 1 字（成指→城指）；qwen 零错；本地 small 错 3 字（证→正、十一→亿、深证→深圳）。**本地 small 准确率不够，专有名词必须校对。**
- 本地依赖：venv 在 `/opt/data/.venv-browser`，模型缓存 `HF_HOME=/opt/data/.cache/huggingface`
- **av 库坑**：faster-whisper 自带解码器与新版 PyAV 冲突（`metadata_errors` 报错）→ 脚本绕开：ffmpeg 转裸 PCM → numpy 读入 → 传数组给 transcribe()
- omniroute **不校验 api_key**（坏 key 也能调通），所以测降级要靠改 BASE 到不可达地址，不能伪造 key

## ⚠️ HuggingFace 必须走镜像（踩过坑）
`huggingface.co` 的 DNS 被污染到 Facebook IPv6 段（`2a03:2880:...`），强制 IPv4 也 000。
**解法**：`/opt/data/memories/env.sh` 已设 `HF_ENDPOINT=https://hf-mirror.com` + `HF_HOME`，并挂进 `.bashrc`/`.profile`。
新开 shell 记得 `. /opt/data/memories/env.sh`，或直接用里面的 python 绝对路径。

## 抖音入库管线（小豆/阿正资产）
| 资产 | 位置 |
|---|---|
| 小豆经验交接（最全） | `obsidian_vault/10-Agent共享记忆/小豆经验交接-通用工作流与踩坑.md` |
| 完整链路（Windows版） | `obsidian_vault/08-抖音/抖音入库完整链路_Windows版.md` |
| 权威入库规范 | 共享库 `douyin-bilibili-ingest`（铁律：转录必须真实） |

**铁律（历史教训）**：
- 2026-08-04 抖音 10 篇笔记是 LLM 幻觉，2026-08-07 B站 35 篇里 20 篇字幕错位 → **绝不用 LLM 凭空生成口播稿**
- 抖音别走裸 yt-dlp（412 风控），要用带 cookie 的方式
- 目录：抖音 → `08-抖音视频学习/`，B站 → `07-B站视频学习/`
- 文件名用连字符无空格（防 wikilink 断裂）

**本容器现状**：yt-dlp 2026.08.19 ✅、ffmpeg ✅、faster-whisper ✅、Chromium ✅（`/opt/data/.playwright-browsers`）、profile 目录 `/opt/data/browser-profile`（挂 volume2 不丢）
**卡点**：抖音网页版对本机 IP 风控（标题「验证码中间页」，DOM 全空）→ 需代理或换出口 IP

## 🌐 浏览器：Windows Chrome CDP 桥接（2026-10-01 接通）
**关键架构**：NAS 容器 **不再自己开浏览器**，直接复用 BOSS 的 Windows Chrome 登录态。
```
Hermes(browser.cdp_url) ──> 192.168.199.184:9222 (Windows 反向代理) ──> 127.0.0.1:9222 (Win Chrome)
```
- `config.yaml`：`browser.cdp_url: http://192.168.199.184:9222` + `use_real_profile: false`
- **依赖 Windows 开机**。Win 关机 → 浏览器就断（这是已知架构约束，不是 bug）
- 登录态已核实四站全部有效：抖音 62 cookie（含 sessionid/sid_tt）、B站 19（SESSDATA/DedeUserID）、知识星球 2（zsxq_access_token）、12306 16（JSESSIONID）
- cookie 已落盘：`/opt/data/memories/cookies/{site}.json`（playwright）+ `{site}_cookies.txt`（Netscape，给 yt-dlp）
- 重新导出：`/opt/data/.venv-browser/bin/python /opt/data/memories/extract_cookies.py`
- **踩坑**：`connect_over_cdp` 后 `Browser` 对象**没有** `.pages`，要用 `b.contexts[0].pages`
- **踩坑**：browser_exec 的 `js()` 多次返回 `{}`（序列化不可靠）；读页面真实内容改用直连 playwright `pg.inner_text("body")`，它正常
- 本会话**没有 vision provider**，`vision_analyze` 不可用（别再试，看图需求请让 BOSS 自己看）

## ⭐ 知识星球入库（2026-10-02 打通，v3 可用）
**脚本** = `/opt/data/memories/zsxq_ingest3.py`（**v1/v2 已废弃**）
```bash
source /opt/data/memories/env.sh
/opt/data/.venv-browser/bin/python /opt/data/memories/zsxq_ingest3.py 20
```
**定时任务**：cron `1b15c555a30e`，每天 08:10，跑完飞书汇报。

**两个目标星球**（BOSS 确认）：
| 星球 | group_id | 现有 |
|---|---|---|
| Workbuddy一人公司营 | 88884585518442 | 257 篇 |
| AI创收私研社 | 88882458154112 | 199 篇 |
- ⚠️ **`AI创收私研社` 和 `跟着叶秋学AI` 是同一个星球**（group_id 都是 88882458154112，改名前后）。只写前者，后者保留不动。
- 目录：`12-知识星球/<星球名>/YYYY-MM/`

### 🔑 三个关键坑（都花时间才定位）
1. **CDP page 级 WebSocket 会被掐断** → 必须用 **browser 级** `wss://.../devtools/browser/<id>`，再用 `Target.attachToTarget({flatten:true})` 开平面会话（带 `sessionId`）。playwright 的 `connect_over_cdp` 在这台机器上 180s 超时，同样因为这个。
2. **那个反向代理有 10 秒空闲超时** —— `proxy9222.py` 里 `socket.create_connection(..., timeout=10)`，relay 的 `recv` 一抛 timeout 就进 `finally` 关掉双方 socket。**所以任何 `time.sleep(>8)` 都会导致连接被重置**。解法：写 `keepalive_wait()`，每 3.5 秒发一条 `Runtime.evaluate`（读 `document.readyState`）保活，等页面 `complete` 再 fetch。星球间隔的退避也必须用发消息代替 sleep。
3. **API 结构**：
   - 作者在 **`talk.owner.name`**，`topic.owner` 是 `null`（第一版没抓对，全写成"未知"）
   - 正文里混排 `<e type="text_bold" title="%E9%9B%B6token...">` —— 要先 `unquote` 提取 `title` 再剥标签
   - 字段还有 `likes_count` / `comments_count` / `create_time` / `sticky` / `digested`，值得入 frontmatter
   - `cookie` 里的 `zsxq_access_token` 直连 API 返回 **401**；但**页面内 fetch 照常可用** → 永远走页面 fetch

### 抓取规范（来自共享库 zsxq-import 技能，务必遵守）
- 直连 api.zsxq.com 必被 1059/19301 拦 → 必须在 CDP 页面上下文 fetch，带 `x-version:2.56.0` + 随机 `x-request-id` + `Referer: https://wx.zsxq.com/` + `credentials:include`
- **首页 20 条稳定；翻页(`end_time`)易触发 1059** → 只抓首页
- 限流 code：`1007`/`1059`/`1004`/`1008`/`19301` → 跳过该星球 + 退避，**不硬刷**
- 去重靠 `topic_id`（文件名就是 `{topic_id} - {标题}.md`）
- **BOSS 要求：每个网站最多开 2 个标签页**，脚本必须用完即 `Target.closeTarget` + `/json/close`

### 历史教训
- **v1 用 DOM 抓取失败**（拿不到 topic_id，文件名退化成时间戳；还把评论区当主帖）→ 产出 166 篇碎片。**必须用 API fetch 拿结构化数据，不要抓 DOM**
- 碎片隔离在 `/opt/data/quarantine/zsxq_bad_20261002/`（未删除，可回滚）

## 🌐 浏览器：Windows Chrome CDP 桥接（2026-10-01 接通）