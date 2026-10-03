---
name: source-claim-verification
description: Use when 外部来源提到某项目、排名、许可证或数据，需回一手 API 核实。
---

# 外部声称回源核实

处理「别人说的」而不是「自己查的」。短视频口播、图文帖、他人 README、榜单截图里的项目名/星数/功能/许可证，**都要回一手 API 核对后才能写进产物**。

## 触发条件

- 用户发来一条**介绍某个开源项目/工具/榜单**的抖音、小红书、B站、公众号文章
- 要判定某个视频/文章的技术说法是否成立
- 要拿「许可证能不能用」的结论
- 任何要写入知识库、报告、汇报的**外部来源数据**

不触发：用户自己给的数据、自己机器上实测的结果。

## 流程

### 1. 先把声称完整抠出来，不要边看边下结论

视频走 `douyin-obsidian` / `media-import` 抓取链路；拿到后**转录原文与画面 OCR 分开存**。

- 转录（ASR）对专有名词错得厉害，且错得「很像对的」：项目名、公司名、型号、人名是高发区
- 画面 OCR 会把字母读错：`om-ai-lab` → `om-al-lab`（i/l 形近）
- **转录和 OCR 都只是线索，不是证据。** 两者都要拿去做第 2 步反查

> 关键纪律：**保留转录原文不动**，另起一段写「校正说明」。
> 直接改原文会让人无法判断原始转写到底错在哪。

### 2. 用项目名反查一手仓库（OCR 常错一个字母）

```bash
export HOME=/opt/data/home GH_CONFIG_DIR=/opt/data/home/.config/gh
gh api "search/repositories?q=<短关键词>&per_page=8" > /tmp/sr.json
```

- **用短词，不要用完整长句**（长自然语言搜索几乎必然返回空）
- OCR 出的仓库名**先当不确定**：逐个候选 `gh api repos/<owner>/<repo>` 试，
  404 说明 OCR 读错了，按描述和星数重新定位
- 搜到多个同名时按 `description` + `stargazers_count` + 语言筛，**不要只看名字像**

### 3. 拉一手元数据（不要只靠搜索结果摘要）

```bash
gh api repos/<owner>/<repo> --jq '{stars:.stargazers_count,license:(.license.spdx_id//"无"),
  created:.created_at[0:10],pushed:.pushed_at[0:10],lang:.language,desc:.description}'
```

必须拿到的字段：stars、license、created/pushed（判断是否还活着）、
default_branch、language、homepage、archived。

> `default_branch` 经常不是 `main`。直接 `raw.githubusercontent.com/<repo>/main/README.md`
> 会返回空内容（看起来像 14 字节），用 Contents API 或改用默认分支。

### 4. 许可证必须回源原文，不能信 API 字段

```bash
python3 scripts/resolve_license.py <owner/repo> [<owner/repo> ...]
python3 scripts/resolve_license.py --selftest    # 改过判定规则后必跑
```

详见下方「许可证回源」。

### 5. 逐条对照，写成核查表

结论不是「视频说的对/不对」，而是**每条声称一行**，三态标注：

| 声称 | 一手数据 | 判定 |
|---|---|---|
| 准确 | 与 API 完全一致 | ✅ 属实 |
| 部分属实 | 主体对、细节错（版本号/许可/是否官方） | ⚠️ 需修正 |
| 不实 | 与一手数据矛盾 | ❌ 不实 |

**常见的不实类型**（按实测频次）：

- **指标张冠李戴**：把某平台的安装量/下载量写成「GitHub Stars」。
  实测一条榜单视频 10 项里 7 项数字与当时实际不符，标题还写着「按 GitHub Stars 排序」
- **榜单错位**：漏掉真正的头部，塞进排 50 名开外的项目
- **功能夸大**：把 beta 说成稳定版（`2.0.0-beta.28` ≠ 正式版）
- **归属错误**：说某功能是官方的，实际是第三方（实测：官方是 Electron 桌面应用，
  视频演示的 Docker 版根本不是官方产物）
- **OCR 可见性差导致的名字错误**：画面模糊时项目名容易读错，转写听错

### 6. 结论里保留对 BOSS 有用的部分

核实不是为了否定视频。写清：

- **能不能用**（结合本机硬件/已有栈，重复的东西不必装）
- **许可与合规风险**（AGPL 传染、模型各有独立许可、声音/音源版权）
- **更好的替代**（本机已有同类、或有许可更干净的等价项目）

## 许可证回源

### 为什么不能用 API 字段

GitHub 用 licensee 识别 SPDX。**LICENSE 正文前加一句自定义措辞就会识别失败**：

```
This program is licensed under the GNU Affero General Public License v3.0 only.
    ↑ 这句导致 → API 返回 NOASSERTION
```

`NOASSERTION` 被当成「无许可证」就会错杀可用项目。必须回源读原文。

### 判定规则的两条顺序铁律

1. **禁商用/专有必须排在宽松许可之前**
   原因：AGPL 与 MIT 正文都含 `free of charge`，宽松许可先匹配会把
   「非商用 + MIT 特征」的文件误判成 MIT。

2. **禁商用只认授权声明句式，绝不认条款细则里的用法描述**
   原因：标准 AGPL-3.0 正文第 6(b) 节含
   `This alternative is allowed only occasionally and noncommercially` ——
   那是「偶尔且非商业性地附源码」的条件，**不是禁止商用**。
   裸 `noncommercial` 匹配会把整个 AGPL 项目误判成完全不可用。
   故要求形如 `licensed ... for non-commercial` / `not licensed for commercial use`。

### 商用友好度分级

| 级别 | 含义 |
|---|---|
| `permissive` / `public-domain` | 可闭源商用，保留版权声明 |
| `copyleft-weak` | 弱 copyleft，动态链接可闭源 |
| `copyleft-strong` | GPL/AGPL/SSPL，**闭源商用前必须审** |
| `copyleft-source` | BUSL 等，非 OSI 认证 |
| `no-commercial` / `proprietary` | 默认无授权 |

## 校验器必须自带自检

`resolve_license.py --selftest` 覆盖 10 个用例，**含两条真实踩坑的回归**：

- AGPL 全文含 `noncommercially` → 不得判成禁商用
- MIT 正文后附「non-commercial use only」→ 必须判成禁商用

> 写完判定规则**立刻跑自检**。本次实测：自检当场抓出「禁商用被 MIT 覆盖」；
> 真实仓库复验又抓出「标准 AGPL 被误判禁商用」。**没有反例的校验器会一直假 PASS**——
> 与 `ground-truth-discipline` 里 `verify_quote.py` 是同一个道理。

## 凭据纪律（写核查脚本时必守）

- **任何脚本都不得把 token 写进字面量**，包括临时核查脚本。
  正确做法：从环境变量读，文件权限一律 600。
  实测踩坑：核查脚本硬编码了真 PAT，并随归档进了 NAS 和公开备份仓。
- 读文件工具可能自动给凭据打码，**但磁盘上是明文**——打码不等于没泄露。
- 扫描时区分真假：官方文档占位符写作 `ghp_xx...xxxx`，真值是 40 位混合大小写。

## 产出形态

笔记写进 Obsidian 时包含：转录原文（含校正说明）→ 项目一手元数据表 →
逐条核查表 → 给 BOSS 的实际建议 → 相关文件路径 → 踩坑记录。

## 与其他技能的关系

- `ground-truth-discipline` —— 那套管「引文 vs 原始语料」，本技能管「外部声称 vs 一手 API」
- `douyin-obsidian` / `media-import` —— 抓取链路，本技能是抓完之后���核实步骤