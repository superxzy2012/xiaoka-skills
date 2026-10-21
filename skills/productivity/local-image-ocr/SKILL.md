---
name: local-image-ocr
description: Use when 用户发来图片/截图要读出里面的文字。本地 OCR 提字。
version: 1.0.0
author: xiaoka
license: MIT
metadata:
  hermes:
    tags: [ocr, image, screenshot, rapidocr]
    related_skills: [video-ingest-pipeline, tools-terminal-usage]
---

# 本地读图（OCR）

## When to Use

- BOSS 发来一张截图（界面、报错、后台、订单页）并问「这是什么 / 怎么弄 / 为什么报错」。
- 视觉模型那条路不可用（provider 未接入、返回「no image data」）—— **不要就此回复「我看不了图」**，先走本地 OCR。
- 需要**精确字符**而不是「图里大概有什么」：URL、端口、版本号、报错码、模型名、仓库名。这类场景**本地 OCR 比视觉模型更可靠**，就算视觉模型在线也优先用它。

## 一、定位图片

用户消息里会直接给出落盘路径（形如 `/opt/data/cache/images/img_<hash>.jpg`）。先用 `ls -la` 确认存在与大小。

## 二、跑 OCR

统一用可写 venv 的解释器（系统 python3 装不了包）：

```bash
/opt/data/.venv-browser/bin/python /opt/data/skills/productivity/local-image-ocr/scripts/ocr_image.py <图片路径>
```

脚本做三件事：RapidOCR 识别 → 按 `(y//12, x)` 排序重建版面 → 带坐标逐行打印。
**排序这步不能省**：不排的话输出是识别顺序，多栏界面（左菜单 + 右内容）会串行错乱，读出来是乱的。

## 三、🔴 坑一：`libGL.so.1` 缺失导致 cv2 导入失败

RapidOCR 依赖 cv2（opencv-python），而它需要系统 `libGL.so.1`。本机没有，报：

```
ImportError: libGL.so.1: cannot open shared object file: No such file or directory
```

**修法：换成 headless 版**（headless 不需要 GUI 库，OCR 用不到 GUI）：

```bash
UV=/opt/hermes/tools/uv-0.12.3-linux-x64/uv        # uv 不在 PATH，用绝对路径
PY=/opt/data/.venv-browser/bin/python
$UV pip uninstall --python $PY opencv-python
$UV pip install   --python $PY -q opencv-python-headless
$PY -c "import cv2; print(cv2.__version__)"
```

（不要 `pip install` —— 该 venv 无 pip；也不要去找 `libGL` 装，headless 才是根治。）

## 四、🔴 坑二：小字/低分辨率识别不全

整图 OCR 漏字（尤其是对话框、按钮、地址栏）时，**裁剪 + 放大 2 倍再 OCR**：

```python
from PIL import Image
im = Image.open(path); w, h = im.size
crop = im.crop((int(w*0.45), int(h*0.05), w, int(h*0.75)))
crop = crop.resize((crop.width*2, crop.height*2))   # 放大后重新 OCR
```

脚本已内置：`--crop 0.45 0.05 1.0 0.75 --scale 2`。

## 五、🔴 坑三：OCR 会把专有名词认错，**不能当权威**

实测：`Agent2API` → 被认成 `Agent2APl`（大写 I 认成小写 l）。中文界面里的英文标识、模型名、端口、仓库名都属于高风险。

**规则：OCR 只用来「知道该去查什么」，凡是要写进结论的标识符，都要回源核一遍** ——
按 OCR 到的关键词去搜 GitHub / 看本地进程 / 探活那个端口，以真实系统为准。

## 六、读完图之后：图只是线索，不是结论

截图告诉你「BOSS 现在盯着什么界面」，**不等于**「系统当前是什么状态」——两者经常不一致（截图是几十分钟前的）。

流程：**OCR 提字 → 抽出可核实的标识符（端口 / 服务名 / 版本 / 报错码）→ 到真机验证 → 再回答**。
例：截图里写着「网关启动失败 · 127.0.0.1:3065」，实测 3065 其实在监听、只是 `status:degraded`
且 `loggedIn:false` —— 根因是「没登录账号」，跟「启动失败」是两回事，只有去验证才知道。

## 七、超长截图（高 > 5000px）：按高度切段，别缩图

「一条对话截到底」的图常是 1260×24000 这种比例。整张丢给视觉模型会被上游拒（`400 upstream`），
缩到长边 1600px 又只剩 83px 宽——**字全没了**。宽度承载文字，所以只能切高度：

- 保持**原始宽度**，按 1500px 高切段，段间**重叠 60px**（跨切口的行不至于被腰斩）。
- 每段单独 base64 喂视觉模型，要求「逐字抄原文」，最后按顺序拼回。
- 空白段是正常的（纯图片区域），**不要把空段当失败**。
- **慢**：17 段约 15 分钟，单段 30–60s。必须 `background=True` + 900s 级超时；
  前台 420s 会被硬超时掐断，日志里只留下「段 1」一行，看起来像卡住，其实只是没跑完。

脚本：`scripts/ocr_long_screenshot.py <图> -o out.md`（`--seg-h` / `--overlap` / `--model` / `--base` 可调）。

读出来的东西照样受坑三约束：**界面文字可直引，标识符必须回源核**。长图尤其容易把同一段话重复读出
（重叠区），拼回后按 `y` 去重再引用。

## 八、汇报口径

- 先给结论（「这是什么 + 现在什么状态」），再给依据。
- 提一句「视觉模型没接入，我用本地 OCR 读的」——让 BOSS 知道可能的识别误差从哪来，别把 OCR 误认当事实陈述。
- 界面里的**界面文字**可以直引；**标识符**必须是你核过的值。
