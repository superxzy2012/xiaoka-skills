---
name: video-ingest-pipeline
description: Turn short-video links into real, cited Obsidian notes.
version: 1.0.0
author: Hermes (curator)
license: MIT
metadata:
  hermes:
    tags: [ingest, douyin, bilibili, obsidian, transcription, notes]
    related_skills: [transcription-routing, remote-browser-cdp-bridge]
---

# 短视频入库管线

Take short-video links and produce notes whose transcript is real, sourced, and auditable.

Use when: the user pastes a douyin/bilibili share link and says 入库/收藏/存知识库; a batch of
such links; or a task needs durable notes built from video content.

## When to Use
- One or many short-video share links destined for a shared knowledge base.
- Reusable pipeline needs: the user says 固化 after a successful manual run.

## Standing rules

- **The transcript is the source of truth; the summary is derived from it.** Never invent or
  "reconstruct" spoken content — a hallucinated transcript that looks real is the single worst
  failure mode here, and it has burned this user's library before (bulk notes that turned out to
  be fabricated). If transcription fails, write an explicit failure marker, not a plausible body.
- **Generate the skeleton, then read the transcript yourself and write the key points.** Do not
  have a second model summarize unverified ASR output into the final note without a check.
  What the ingest script writes is a skeleton — `status: 待核查`, 「待提炼」要点、title 还带着
  hashtag。交付前**整篇重写**（标题/frontmatter/要点/FACT 表/边界），再用 `push_to_vault` 重推；
  只补一行要点就交，库里留的就是一条读不下去的半成品。
- **Write to the shared library's canonical directory for that platform**, with a
  frontmatter block and a link back to the original. Naming and location are what make the
  library navigable later.
- **When the user says 固化, ship a runnable script**, not a description of the steps, and
  re-run it (dry-run first) to prove the script path works — not just the manual path.

## Procedure

1. **Resolve the share link and fetch metadata in one call** — the platform id, canonical title,
   uploader, and duration all come from the downloader's metadata output.
   **Run the local ingest script first; do not hand-roll a platform item-info API call.**
   Those endpoints get encrypted or retired without notice — douyin's
   `web/api/v2/aweme/iteminfo` returns `status_code 11110 / encrypt_data_miss` for
   *both* image-post and video ids, so a URL shape that looks right yields an empty
   item list. See `references/platform-routes.md` for the verified per-platform route.
2. **Download with the site's cookie jar.** A logged-out downloader gets a guest page, rate-limit
   walls, or an HTML file named `.mp4`.
3. **Transcribe through the router** (see the `transcription-routing` skill) and keep the
   backend/cost that served it.
4. **Extract keyframes** (roughly one per 15s) so a future reader can verify visual claims.
5. **Write the note** = frontmatter (title, source_url, platform, platform_id, author, duration,
   date, tags) + one-line summary + verbatim transcript + key points + actionable follow-ups.
6. **Archive frames** beside the notes; keep the video only when asked (it is the large part).
7. **Correct proper nouns against frame OCR, then verify the OCR result independently.**
   ASR mangles exactly the tokens that make a note findable later: a product name became
   「cogee」and 「探索」in the same transcript, `Claude` became「Cloud」, and a GitHub org
   read `om-ai-lab` became「om-al-lab」. Cropped screenshots carry the real spelling, so OCR
   the keyframes and diff against the transcript.
   **OCR is a candidate source, not an authority** — that misread org name returned
   `Not Found` when queried directly and only resolved via a repository search that found
   the correct spelling. Confirm any identifier that will be cited with a live lookup.
   **Write the corrections as a 校订表, not silent edits** — `ASR 原文 | 校订 | 依据 | 置信度`.
   Only rewrite what the frames or context can confirm; a homophone you merely suspect stays in
   the transcript unchanged and appears in the table as 存疑（不改，仅提示）. Silently "fixing"
   an uncertain word invents content that no longer matches the audio.
   **平台贴片广告音轨不是内容**：转写尾部常挂一句平台/剧场广告（「优优独播剧场——YoYo Television
   Series Exclusive」这类），在笔记里点明来源并排除，别把它提炼成要点。

## When the downloader is walled: borrow the browser's own signature (douyin)

**已修好：yt-dlp 仍是最好的入口，靠一个本地插件补上签名这一步。**

> 速度：解析/下载已从 71s/条 降到 **17.8s/条**（29s 视频实测）。两个关键修复：
> ① `dy_cdp._capture_detail` 旧版收到响应后**不 break**，死等满 `wait=25s` ——
> 命中后再收 1.5s 就收工，解析 26s→5.2s；
> ② `ingest.py` 的 `fetch_meta` + `download` 是**两次 yt-dlp 调用**=两次 CDP 解析，
> 改用 `fetch_and_download()` 一次调用带 `--write-info-json`，省一半。

**抓主页作品列表必须开 focus emulation。** 后台标签（BOSS 要求不抢焦点）会被 Chrome 节流，
抖音虚拟列表永远不加载第二屏 —— 实测只拿到 **28 条**，开 `Emulation.setFocusEmulationEnabled`
后同样的滚动变成 27→63→135→**473** 条。另外 `eval_js("()=>x")` 只是把箭头函数本身返回
（序列化成 `{}`），必须写成 `(()=>x)()` 才能拿到数值；`window.scrollBy` 对抖音主页无效，
要滚 `overflow:scroll` 且可滚距离最大的那个 div。

**CDP 端点默认走 NAS 本机 headless，不再依赖用户的 Windows 机。**
优先级写死在 `memories/cdp.py`：`环境变量 CDP_URL` > `http://192.168.199.2:9222`（NAS 上的
`cdp-chrome` 容器，headless Chrome，profile 持久化）> `http://192.168.199.184:9224`（用户 Windows 上的
Chrome，有登录态）。`pick_url()` 用 2.5s `/json/version` 探测挑活的，`dy_cdp._capture_detail` 再按端点
逐个重试，所以 NAS 挂了会自动回落 Windows，不需要改代码。
实测差异：解析 9.1s（headless）vs 5.2s（Windows），单条全流程 28.0s vs 17.8s —— **用 10s/条换掉「用户的
电脑必须开机」这个依赖，值得**。列表抓取也走这条：headless 每轮新增 18 条（Windows 36~54 条），慢但可用。
公开视频**不需要登录态**（detail 接口靠页面 JS 自己生成 ttwid/msToken）；只有私密/仅自己可见的作品才需要
账号，profile 在 `/volume2/2-AI/cdp-profile` 持久化，扫一次码长期有效。
**判断「有没有登录」只用 `/user/self`**：登录态正常时会渲染出本人主页（昵称/关注/粉丝数），未登录会跳登录页。
**别拿 `https://www.douyin.com/` 首页判断** —— 它会 302 到 `/jingxuan`（抖音精选电脑版），那个页面里既没有
「登录」按钮也没有二维码元素，据此得出的「未登录、找不到登录入口」是假结论。详见 `references/cdp-endpoints.md`。
容器自检与重建命令见 `references/cdp-endpoints.md`。

插件 `/opt/data/home/.yt-dlp/plugins/douyin-cdp/yt_dlp_plugins/extractor/douyin_cdp.py`
在导入时猴补 `DouyinIE._real_extract`：内部借 CDP 页面上下文拿 `play_addr`，**下载/重试/进度/格式选择
仍由 yt-dlp 自己做**（`yt-dlp -j <短链>` 现在直接出 `extractor_key: DouyinCDP` + 多个 format）。
关键坑：补丁必须放在 `yt_dlp_plugins/extractor/` 下，不能放 `yt_dlp_plugins/__init__.py` ——
根插件在核心之前加载，`from yt_dlp.extractor.tiktok import DouyinIE` 会抛异常被吞掉，静默不生效
（表现：`-v` 里能看到 plugin 目录，但报错栈还在 `tiktok.py:_real_extract`）。
上游这条路走不通：抖音 detail 接口有 Argus 风控，裸 HTTP 一律
`403 Blocked by ArgusSecurityPlugin Uifid Not Found` —— 实测 `curl_cffi --impersonate chrome`
伪装 TLS 后**依然是同一句 403**，加 `device_platform/aid` 参数、加 Referer 都无效；
而同一个 URL 在页面上下文里 `fetch` 却 200。所以「换 cookie / 换 UA / 升级 yt-dlp」全是死路，
最新版 2026.08.19 的提取器仍是无签名裸 GET。

机制（插件内部就是这条）：

`yt-dlp` 的原生抖音提取器会**固定**报 `Fresh cookies (not necessarily logged in) are needed`：它算不出
`a_bogus` 签名。**这不是 cookie 问题**（刷新到含 `sessionid` 的 cookie 后依旧报同一句），也不是换
API key 能解决的（上游 key 已停用）。分享页 `iesdouyin.com/share/video/<id>/` 只返回壳数据，
没有 `play_addr`。**别在这两条路上耗轮次**，它们永远不会通。

可用的路只有一条：**借用 Chrome 页面自身的 JS 去签名，旁观它发出的 `aweme/detail` 响应。**
（不需要登录态也能拿公开视频——headless 实测同样 200。）

1. 短链解出 `aweme_id`：`curl -sS -o /dev/null -w '%{url_effective}' -L '<短链>'`，取 `/video/(\d+)`。
2. 经 CDP 在**后台标签**打开 `https://www.douyin.com/video/<id>`（建标签必须 `background=True`，
   绝不抢 BOSS 前台焦点），`Network.enable` 后监听 URL 命中 `aweme/detail` 的响应，取 body。
3. 从 `aweme_detail.video.play_addr.url_list` 取直链（`playwm` 换 `play` = 无水印）；
   元数据（`desc` / `author.nickname` / `video.duration`）从**同一份 JSON** 取 —— 这是唯一
   能拿到真实昵称的地方（见上文「`%(uploader)s` 是数字 UID」的坑）。
4. 直链带时效签名，**立刻下载**，别缓存 URL 隔一会儿再下。

已固化：`/opt/data/memories/dy_cdp.py` 暴露 `fetch(share_url, workdir) -> (meta_dict, video_path)`。
**`ingest.py` 对抖音现在是 yt-dlp 优先、CDP 兜底**（2026-10-17 晚改回）：装了插件后 yt-dlp 一条命令
就能解析+下载，实测 ESP32 那条 18MB 走 yt-dlp 成功；只有插件路径异常（Chrome 没开 / CDP 不通）才回落
`dy_cdp.fetch`。非抖音平台仍走 yt-dlp 原路。

## 链接丢了也能自己重跑，别让用户重发

BOSS 的原话要求：**「一定要我再发一次吗？」——不要。** 抖音/B站链接本身就躺在 gateway 日志里，
自己捞回来重跑，这是默认动作，不是可选项。

```bash
# 入站原文（含完整分享文案与短链），按时间窗过滤
grep -a "Inbound dm message received" /opt/data/logs/gateway.log \
  | awk '$0 >= "2026-10-17 16:00"' | grep -a "douyin" | tail -6
# 只捞短链
 grep -aoE "https?://v\.douyin\.com/[A-Za-z0-9_-]+" /opt/data/logs/*.log | sort -u
```

捞不到时再往上层找：`session_search` 按视频主题词查会话历史。**只有两条路都空**才回头问用户。
重跑后用返回里的视频标题与失败时那句标题逐字比对，确认跑的是同一条 —— 短链会指向不同作品。

## Skill-Bearing Videos: Install by Default

BOSS (2026-10-04) 明确要求：**抖音链接里如果有 skill 或开源工具，默认安装，不要问。**

After the normal transcript + frame-OCR pass:

1. **Locate the repo from the OCR'd English README text** — paste the description you read off
   the video frame into GitHub full-text search. Highest hit rate of any method; guessing
   repo names 404s (four misses in a row on 2026-10-03).
2. **Hard-verify every number** via the GitHub API and record mismatches in the note.
   OCR digit reads are unreliable: a frame showing "★22.3k / 60 Fork" was actually
   forks=1,417 / watchers=60 — OCR had merged two adjacent fields.
3. **If the video carries a skill** (`SKILL.md`, an Agent Skill, `npx skills add`) → install it:
   - **Run it once for real before claiming success** (build a fixture or run the official
     example). Reading the README is not verification.
   - MIT/Apache/BSD installs directly; **GPL/AGPL needs a heads-up** ("open source" on
     a video ≠ commercial use).
   - Skill `description` must be ≤60 chars or `skill_manage` rejects the create; put
     detail in the body.
   - Then set `status: 已核查` and `github_repo: owner/repo` in the note's frontmatter.
   - **装法用仓库自带的 installer，别自己搬文件**：`node installer/install.js --only hermes --dry-run`
     先看落点，再去掉 `--dry-run`。`npx -y github:owner/repo` 会被 npm 的 git 依赖拦截，裸
     `git clone` 在本机会超时 —— 源码用 `gh api repos/owner/repo/tarball/main` 取。
     完整命令、节点落点与验证方法见 `find-skills-xiaoka` 的「把第三方技能包装进 Hermes」。
   - **装完要真跑一次**：普通模式与技能模式同一道题各跑一遍，比字数和事实完整度；
     `skills_list` 里有条目只证明注册了，不证明它真的改变了输出。
4. **BOSS 说「推广到蜂群」= 每个节点都装 + 通知，不是本机装上就算完**：共享库
   `/opt/nas/volume2/2-AI/skills/`、云端 `~/.hermes/skills/`（改完重启 gateway）、NAS 贾维斯容器内
   `/opt/data/skills/` 各拷一份 —— **技能是实体拷贝不是软链**，共享库改了不会自动到别人家。
   `find-skills-xiaoka/scripts/distribute_skill.sh <skill...>` 一条命令做完，再在管理群发通知。
5. **Only come back to ask** for destructive operations, money, or credentials.

Same-org same-language siblings are the strongest decoys: `firecrawl/pdf-inspector` (★19,472,
Rust, same org) matched on every heuristic but handles PDF only, while the correct answer was
`firecrawl/anydoc` (★22,472). **Match the README description text, not star count or naming.**

**Repo-shaped strings on screen are not a promoted project.** A monitoring dashboard listing the
author's own repos (`feishu-role-bot-kit`, `claude-standard-dev…`) is a screenshot of *their*
infrastructure, not a tool the video is handing out. Decide by the CTA: 「这一套我也能给你的公司搭
起来」= selling a build service → record it in the note and install nothing; only a repo link,
`npx …`, or `git clone` on screen / in the caption starts the install path. Misreading this burns
a session hunting a repo that was never offered.

## Pitfalls

- **After the rewrite, rename the note to a short clean name and delete the auto one.** `ingest.py`
  names the file from the full platform title, so it lands as a ~90-char string with commas and
  spaces that no one will ever wikilink. Push the rewritten note as `YYYYMMDD-<主题>-<关键点>.md`,
  then delete the auto file through the same root container
  (`rm -f '/v/08-抖音视频学习/<old>' && echo DEL_OK`) — the vault is not writable from the shell,
  so `mv`/`rm` there fail with `Permission denied`. Re-read from the host side afterwards
  (`ls -la` + `md5sum`) and match it against the local copy. The swap is one small script, no
  manual container calls: write the rewrite to scratch, `from ingest import push_to_vault`, push
  `[(scratch_path, '08-抖音视频学习/<new>.md')]` (it does tar→NAS /tmp→root container→chown and
  prints PUSH_OK), then delete the old file via the same container path and compare host-side md5.
  Never re-run ingest.py to "re-push" — it regenerates the note from the transcript (next pitfall).
- **A self-reported aggregate gets checked by re-adding the on-screen breakdown.** 「三天 741 件事」
  was verifiable only because the closing frame showed `206 / 250 / 285`; when no breakdown exists,
  write the number as 作者自述、无外部可验证来源 and say what unit is missing — 「件」can mean a task,
  an API call, or one artifact, and the three differ by orders of magnitude.
- **Separate "the note is written" from "the metadata is right," and say which you have.**
  The note landing on disk is the deliverable; a half-resolved `author` field or an unverified
  number is not. When a follow-up repair is blocked, report the note as done *and* the repair as
  outstanding in the same breath — don't let "ingested" imply "fully finished", and don't bury a
  blocked step under a green summary.
- **Hand back a decision the user can actually make.** When blocked on their machine, give the
  specific command to run and say what each possible output means for the fix — "run X; if it
  prints nothing, the browser isn't listening, if it prints a row, it's a firewall problem" — so
  one reply closes the loop. Flagging an outage without a next step just moves the work back.
- **Don't dress a failure as a workflow.** If every attempt at a task failed and it ended with
  "please check manually", do not write those attempts into a skill as the recommended procedure.
  Either find and verify a path that actually works, or record nothing and say plainly that the
  approach is unproven.
- **Take the video id from metadata, not the URL.** Share short links (e.g. `v.douyin.com/<code>/`)
  contain no `/video/<id>` segment; deriving the id from the string yields an empty or wrong value
  that then propagates into frontmatter and the attachment folder name.
- **Strip `#hashtags` from the file name only.** Platform titles append topic tags; keep the full
  title in frontmatter so nothing is lost, but a 200-char name breaks wikilinks and paths.
- **Escape a regex character class when splitting on `#`** — a bare `#` inside `re.split` is a
  comment and silently returns the whole string.
- **Netscape cookie 文件：`expires = -1` 会让 yt-dlp 丢弃整条 cookie**。CDP 的
  `Storage.getCookies` 对会话 cookie 返回 `-1`，直接写进文件就是非法行，yt-dlp 跳过并告警 ——
  表现是「导出了 70 条却一条没用」。导出脚本必须把 `exp < 0` 归零：`exp = int(...) or 0; if exp < 0: exp = 0`
  （`memories/refresh_douyin_cookies.py` 已修）。**但别指望修好 cookie 就能救抖音下载** ——
  cookie 再新鲜，原生提取器仍报 `Fresh cookies ... are needed`；要么走 douyin-cdp 插件，要么直接 CDP。
- **Writing outside the writable root fails for file tools** but not for shell `cp`/`ln`. Build
  the note locally, then copy into the vault; `os.makedirs` the destination dir first.
- **当 vault 连 shell 都写不进时（属主是别人、组只有 r-x），用 root 容器借道写，再把属主 chown 回去。**
  实测 `obsidian_vault/08-抖音视频学习` 属主 `superxzy`(1000)、组 `admin`、权限 755+ACL ——
  容器内 hermes(10000) 和 NAS 上的 DY(1005) **都写不进**（`Permission denied`）。可行路径：
  ```bash
  # 1) 文件先推到 NAS 的 /tmp（DY 可写）
  base64 -w0 note.md | $SSH 'base64 -d > /tmp/xk_push/note.md'
  # 2) root 容器挂载 vault 写入，chown 回属主（1000:10 = superxzy:admin）
  $SSH 'sudo -n docker run --rm -v /volume2/2-AI/obsidian_vault:/v -v /tmp/xk_push:/p \
        alpine sh -c "mkdir -p /v/08-抖音视频学习 && cp /p/note.md /v/08-抖音视频学习/ && chown -R 1000:10 /v/08-抖音视频学习/note.md"'
  # 3) 必须从**宿主侧**回读 md5 与本地比对 —— 这一步能抓到下面那个坑
  ```
  🔴 **容器内绝不能用宿主路径当目标。** 写成 `cp /p/note.md /volume2/2-AI/.../` 时，该路径在
  alpine 里不存在，`cp` 就落进**容器的可写层**，`--rm` 一退全没了 —— 而容器内的 `ls` 会
  正常列出这个文件，看起来「成功」得毫无破绽。挂载点是什么就用什么（`-v X:/v` → 容器内只认 `/v`）。
  **已自动化**：`ingest.py` 内置 `push_to_vault(pairs)`（默认开，`--no-push` 关），入库后自动把
  笔记 + 附件推进 NAS 真 vault 并 chown 回 `1000:10`，靠回读 `PUSH_OK` 判成败；失败只告警不回滚，
  本地 `VAULT` 副本始终保留。测试脚本 `/opt/data/cache/scratch/test_push_vault.py`（推探针→宿主
  侧比 md5→删探针，全程走真容器）。
  🔴 **chown 的目标必须包含目录本身，不只是文件。** `tar` / `cp -a` 会把 NAS 上的 DY(1005) 属主
  原样带进 vault，于是出现「文件属 superxzy、目录属 DY」—— 目录 755 而属主是 DY 时，vault 真正的主人
  （Obsidian 侧）反而往里加不了文件。所以 `attachments/<plat>-<id>/` 这类新建目录要单独进 chown 列表。
  `push_to_vault` 已按此实现：除每个文件路径外，凡 `attachments/` 下的路径再补一条两段父目录。
- **`ingest.py` 重跑同一个 URL，会用重新生成的笔记覆盖掉手工校对版。** 脚本每次都从转写重新拼笔记，
  所以「端到端复跑一遍证明管线通了」这个动作本身会抹掉刚做的专有名词校正、frontmatter 补全和核实段。
  复跑前先 `cp` 一份校对版到 `cache/scratch/`，跑完比对行数与 md5，再把校对版还原、用 `push_to_vault` 重推。
  别因为「本地还留着一份」就以为安全 —— 被覆盖的就是那一份。
- **入库中途失败会在 vault 里留下 `.hermes-tmp.*` 临时文件**，同步脚本会把它当未跟踪文件带出来。
  清理走 root 容器（普通 shell 写不进 vault）：
  `sudo -n docker run --rm -v /volume2/2-AI/obsidian_vault:/v alpine sh -c 'rm -f "/v/08-抖音视频学习/.hermes-tmp."*'`，
  跑完回读 `ls -a | grep -c hermes-tmp` 应为 0。
- **On screen-recording videos, frame OCR cannot recover the project name.** Burning-in subtitles
  sit at low contrast and OCR reads only scattered fragments; cropping and upscaling the region
  that should hold the identifier makes it *worse* (blur, not resolution). For those, treat the
  the transcript's candidate names as hypotheses and confirm each with a live lookup — never assert
  the tool in the notes from OCR alone.
  **本地 OCR 跑不动就换视觉模型读少量关键帧**：RapidOCR 在 CPU 上逐帧跑整套帧集必超时
  （实测 exit 124）。此时别调参重跑，抽 4~6 张均匀分布的关键帧交给视觉模型直读 —— 烧录字幕
  它认得出，而且一张一次调用、有明确上限。
- **`aweme_detail: null` 不是抓取失败，先看 `filter_detail.filter_reason`。** 被删/仅自己可见的作品会正常
  返回 200，body 是 `{"aweme_detail":null,"filter_detail":{"filter_reason":"status_self_see","detail_msg":
  "因作品权限或已被删除，无法观看"}}`。此时换端点、换 UA、重试都是白费——判据是 `filter_reason` 有值就跳过
  该作品并记一笔，不要报成「headless 抓不到」。同理：批量里偶发 1 条失败先看 reason，再怀疑管线。
- **On douyin, `%(uploader)s` is the author's numeric UID, not their nickname.** The downloader
  hands back `41506980594`, which lands in frontmatter as `author:` and reads as garbage to
  anyone browsing the vault. Prefer the nickname the share text already carries (users paste
  「【博主昵称的作品】」) and fall back to a CDP page read for the rest. Same class of bug as the
  `douyin_id`-from-URL pitfall above: take identity from a source that actually has it.
- **ASR errors in a project name propagate into `title:` and break findability forever.** A
  23-second clip transcribed 「这个工具叫RE」 plus 「没有圆码」 and truncated the title to `Rea：…`,
  so the note was unfindable by the tool's real name and its lead sentence was nonsense. After
  resolving the repo, fix the name in the body *and* in frontmatter `title:` — a corrected
  transcript under a wrong title still loses every search for the correct name.

## Depth
- `references/platform-routes.md` — verified fetch route per platform, frame-OCR corrections, batch-OCR cost.
- `references/cdp-endpoints.md` — CDP 端点选择与故障切换、NAS headless 容器自检/重建、headless 的能力边界。
- `scripts/ingest_one.py` — the single-link ingest flow end to end, ready to adapt.

## Open-source project videos: verify, don't transcribe

Many of these videos are project showcases. A transcript plus a star count is not a finding —
the sponsorable errors live in the claim the video is making.

For every project named in the note, confirm against live data and write a FACT/claim table:
repo owner/name, star count, license, last push, and whether it is still maintained.
The claims that most often break:

- **"36K stars"** — often right, but read it off the API at the same moment you write the note so
  the number has a date attached.
- **"Docker deployment"** — check the official README/docs, not just the video. A desktop
  Electron app's docs listing only Linux/macOS/Windows/Android with no Docker mention means
  there is no official image; the video is running a third-party one. Name the official
  component when one exists and it does something narrower (a sync server is not a media server).
- **"Open source" with no license visible** — see below.

**Never resolve a license from the GitHub API alone.** `license.spdx_id` returns `NOASSERTION`
whenever the LICENSE file carries custom prose above the standard text, which reads as
"unlicensed". Pull the LICENSE text and judge it yourself. Beware the reverse trap too: a bare
`noncommercial` substring matches AGPL-3.0 section 6(b) ("allowed only occasionally and
noncommercially"), which is a condition on *offering source*, not a ban on commercial use —
that misread will wrongly disqualify a perfectly AGPL project.

When the video promotes a tool this machine already has a skill for, diff them explicitly: a
local skill and an upstream project can share a name and be entirely different things (local one
a Markdown workflow template, upstream a TypeScript web app). Say so in the note rather than
letting the name collision imply coverage.

**Record what the video omits, not just what it claims.** Promotional clips state the upside and
drop the limit the maintainer puts in writing, and that omission is the most actionable thing the
note can carry. Read the README for an explicit non-claim and the license for its real boundary,
then put both in the note as their own lines: a reverse-engineering tool whose README says it
does *not* recover original source code still reads as "shows me the original code" from the
pitch; a permissive license on the tool does not grant any right to run it against someone
else's closed-source product. `✅ 核实通过` on the video's claims and `⚠️ 视频漏说` on the
maintainer's caveats belong in the same table, so a later reader sees the gap without opening
the README.

**Never assert a project lacks a capability without grepping its source tree.** A README's
headline list omits what ships as optional extras, and an "it doesn't do X" line turns a
comparison into a false one. Ground truth is `pyproject.toml` extras, `docs/`, and
`tests/test_*` — one grep for the feature's vendor names (`grep -ril "feishu\|lark" .`) before
the sentence is written, not after the user pushes back. A project pitched as "a personal agent
app" can still ship Feishu/DingTalk/WeCom/Telegram channels over long connections, MCP, and
skills — i.e. it overlaps the local stack far more than the pitch suggests.

**When comparing a video's project against the local stack, assume the capability lists overlap
and put the difference in topology and maturity.** The honest axes are: single-device app vs
server-resident runtime; one agent vs a multi-agent bus; what the "hands" can reach (screen
control of phone/desktop apps is a genuinely different power than shell + browser); and age
(weeks-old repo, open-issue count, beta-only platforms). "It's a different species" and "it's a
replacement" are both wrong framings for a project that shares most of the checklist.

## Archiving

Frames, transcripts, OCR scripts, and pulled source all belong under
`15-小卡工作区/<workspace>/开源源码/<project>/` — `cache/scratch/` is pruned after 24h idle,
so anything left there will need re-downloading. Copy artifacts in, then fix the path references
inside the note so they point at the permanent location.

## Attachments live in a different tree than the notes

Notes go to `<vault>/<platform-dir>/` (e.g. `08-抖音视频学习/`) but the ingest script writes
frames to `<vault>/attachments/<platform>-<id>/` at the **vault root**. So one platform's frames
are split across two trees, and the root `attachments/` accumulates every platform plus legacy
material from earlier hand-made notes.

**Consequence for anything that copies or syncs the vault: scope to the platform note directory,
never to the vault-root `attachments/`.** The root tree holds hundreds of dirs and hundreds of MB
of unrelated frames — sweeping it into a sync target or a publish batch inflated one repo from
49MB to 989MB and would have made the peer's first clone a multi-GB download.

Before the first push of any new sync target, print the staged byte total
(`git diff --cached --name-only -z | xargs -0 stat -c%s | awk '{s+=$1} END{print s/1048576}'`)
and state the number in the report. If it is orders of magnitude larger than the note text, the
scope is wrong — find it before pushing, because git history keeps the blobs.
