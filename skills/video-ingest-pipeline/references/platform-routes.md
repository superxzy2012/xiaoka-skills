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
末尾打印阶段可能抛 TypeError（结果项缺 title 时对 None 切片），
但**这不代表转写失败**——读 stdout 前半段拿到转写全文即可。
已修为 `(r.get('title') or '?')`；若再现仍按前半段取。

## 帧必存 NAS

`cache/scratch/` 24h 空闲会被清。抽帧、转写 JSON、校正脚本都搬进
`15-小卡工作区/开源源码/<项目名>/关键帧/`，否则下次要重新下载一遍。