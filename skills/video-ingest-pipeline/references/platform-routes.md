# 平台抓取路由与校正

Per-platform verified routes, and the two-stage correction that keeps identifiers trustworthy.

## 路由表

| 平台 | 视频 | 图文（image post） |
|---|---|---|
| 抖音 | `ingest.py <short-link>` → `transcribe.py` | 同左；**不可用 item-info API** |
| B站 | `ingest.py <url>` | — |

**永远先跑本机脚本，不要手搓 item-info API。**
这些端点会加密或下线且不预告。抖音 `web/api/v2/aweme/iteminfo` 对图文和视频 id
**都**返回 `status_code 11110 / encrypt_data_miss`——URL 形状对也会得到空列表。

## 图文帖：yt-dlp 不支持

抖音图文是 `note/` 类型，yt-dlp 抓不到。但 `ingest.py` 仍能下到附件，
且 `detail.json` 里的 `images[].url_list` / `download_url_list` 含原图直链。

**附件下载后先 `ls` 看真实落盘名**，别猜子目录：实测图直接落在 `scratch/<id>/img1.jpg`，
不是 `images/` 下。按 JSON 里的字段取 URL，按实际文件名收集。

## 短链解析

短链 302 后的最终 URL 就是 id 载体：

```
https://v.douyin.com/<code>/  →  https://www.douyin.com/video/<19~22位数字>
```

正则要同时吃 `/video/` 和 `/note/`：
`r"/(?:video|note|slides)/(\d+)"`。只匹配 `aweme/(\d+)` 会一个都抓不到。

## 两段式校正：转写 → 帧 OCR → 实时核实

ASR 专把「以后要按它检索的名字」转错。实测一轮里：
`Khoj` → 「cogee」**和**「探索」（同一词两种错法）、`Claude` → 「Cloud」、
`VLX-Seek` 仓库 `om-ai-lab` → 「om-al-lab」。

1. **转写**：`transcribe.py <mp4> --json`，取 `{"text":...,"via":...}`。
   `--json` 输出在 stdout 里以 `{` 开头的那行，用 `grep -E '^\{'` 过滤。
2. **抽帧**：`ffmpeg -i V -vf fps=1/8,scale=720:-1 f_%02d.jpg`（每 8 秒一帧）。
   约 95 秒的视频得 12 帧，覆盖简介页、功能列表页、版本更新页。
3. **帧 OCR** 拿到屏幕上的真实拼写，diff 转写后在笔记里标注校正。
4. **实时核实**每个要引用的标识符：仓库名、模型 id、包名。
   OCR 把 `om-ai-lab` 读成 `om-al-lab`，直接查返回 `Not Found`，
   靠**仓库搜索**（不查直接路径）才找到真名。直接路径 404 时先搜再改。

## 批量 OCR 的成本闸

rapidocr（`uv pip install --python <venv>/bin/python rapidocr-onnxruntime`，纯 CPU）
在 720px 宽图上跑 12 张会**超时**（>420 秒）。**先把帧缩到 480px 宽再 OCR。**

```bash
for f in f_*.jpg; do ffmpeg -y -i "$f" -vf scale=480:-1 "s_${f}"; done
```

降分辨率不影响识别项目名/版本号这类大字，足够做校正。

## dry-run 仍可用

`ingest.py --dry-run` 会完整执行**下载 + 抽帧 + 转写**，只是不写库。
已修为 `(r.get('title') or '?')`（原先对 None 切片抛 TypeError）；
若旧版再现异常，读 stdout 前半段拿转写全文即可，**不代表转写失败**。

`yt-dlp` 不在本机 PATH（`FileNotFoundError`）—— 直接调
`transcribe.py <video> --json`，它是 ingest 内部用的同一个转写器。

## 录屏类视频：OCR 拿不到项目名

操作录屏（一边操作一边口播）的字幕是烧录在画面上的，字体极淡。
480px 帧 OCR 只能取到零散词，裁剪放大到 1200px 反而更糊。

**这类视频不要指望 OCR 锁定项目名**：把转写里的候选名当假设，
逐个用 API 验证（仓库搜索 → contents → README），并在笔记里写明
「无法从画面确认具体镜像」而不是猜一个。

## 许可回源判定

视频说「开源」不等于可用。**不要只看 GitHub API 的 `license.spdx_id`**：
LICENSE 顶部加了自定义措辞会让 licensee 识别失败、返回 `NOASSERTION`，
极易被读成「无许可证」。拉原文自行判定，并警惕反向误判——
裸 `noncommercial` 会命中 AGPL-3.0 第 6(b) 节的
「allowed only occasionally and noncommercially」，那是附源码的条件而非禁商用。

判定逻辑见 `find-skills-xiaoka/scripts/resolve_license.py`（带 `--selftest`）。
该脚本属用户所有技能，只作参考路径引用，不修改。

## 视频索引类长文件的误报

`姜胡说/00-姜胡说全部视频索引.md` 这类文件里密集出现 19-20 位数字
（抖音作品 ID），用 `\d{17}[\dXx]` 当身份证正则会得到上千条误报。
同理 `\d{11}` 手机号正则会命中 ID 后 10 位。**扫隐私信息时先确认数字来源**，
再决定是真泄露还是 ID 误报。

## 帧必存 NAS

`cache/scratch/` 24h 空闲会被清。抽帧、转写 JSON、校正脚本都搬进
`15-小卡工作区/开源源码/<项目名>/关键帧/`，否则下次要重新下载一遍。

## 批量重建缺失集：差集要用「已验证全集」

账号主页滚动出来的 ID 列表**混着推荐流的他人作品**。拿它直接减 vault 已有集，
会把别人的作品算成「我的丢了」，重建时又逐条被 `sec_uid` 剔除——白跑几十分钟。

```python
# ❌ 缺失池被推荐流污染，越修越大
missing = all_scrolled_ids - have_in_vault

# ✅ 只用验证通过、且 sec_uid 全等的集合做差集
mine   = {a for a, m in verified.items() if m["sec"] == TARGET_SEC}
missing = mine - have_in_vault
```

**主页列表 ≠ 该号作品集**，前者必须先过 `sec_uid` 全等过滤才是后者。
反过来说：验证器把「早期那批 719xxx/7xxxx ID」全判为他人时，那是**验证器在正确工作**，
不是列表错了——不要因此去调大过滤器。

## 成功判据回查 vault，不信日志标记

入库日志会把长 URL/标题截断，成功标记在 stdout 里被切开，grep 不到就记成失败，
最后报「入库 0 / 失败 80」而笔记其实都在盘上。

```python
# ❌ 依赖 stdout 关键词
if "✅ 入库" in stdout: ok += 1

# ✅ 回 vault 按 douyin_id 复核，这才是事实
for p in glob.glob(f"{DIR}/*.md"):
    if f'douyin_id: "{aid}"' in open(p, encoding="utf-8", errors="ignore").read(400):
        ok += 1; break
```

**通则**：长文本流程的计数一律**从最终产物反查**，不累加过程日志。
汇报前交叉核对（总数 = 已存在 + 新增 + 他人剔除 + 真失败）；对不上就是判据错了，
不是执行错了。「净损失」尤其危险——同时有误删和补进时，只看终态数量会得出
比真实损失小得多的结论，重建前必须逐条算差集。

## 删除笔记前先定死判据来源

vault 里写入的内容（包括核查报告、可信度标注块）会**污染任何扫正文的判据**。
实测正则里的「教育」命中了标注块里自己写的「教育线内容与本篇无关」，
连带删掉 83 篇纯技术笔记。

```python
# ❌ 扫正文：判据会自我污染
edu = re.search(r'教育|Day\d+', title + " " + full_text)

# ✅ 只看文件名（文件名就是标题）/ frontmatter / 本轮 ID 差集
edu = re.search(r'Day\s*\d+|青少年|AI素养', basename)
```

删除是不可逆的：**先跑 dry-run 打印待删清单并逐条核对，再真删**。