# 前序 agent 知识资产索引

入库规范不是凭空定的，是前序 agent 踩坑踩出来的。改流程前先读这些，别重新踩。

## 一手交接笔记（vault 内，用 search_files 定位）
| 资产 | 定位方式 | 内容价值 |
|---|---|---|
| 经验交接·通用工作流与踩坑 | vault `10-Agent共享记忆/` 下按文件名搜「经验交接」 | 视频入库 6 步全流程、下载器同名坑、登录态坑、知识星球限流码、目录映射表 |
| 抖音入库完整链路 | vault `08-抖音/` 下搜「完整链路」 | 分步图示、cookie 文件格式与位置、封装脚本结构 |
| 学习报告/索引 | vault `08-抖音视频学习/00_学习报告.md` | 已有笔记风格基线 |

## 共享库技能（`/opt/nas/volume2/2-AI/skills`）
| 技能 | 职责 | 选用条件 |
|---|---|---|
| `video-downloader` | 单条分享链接 → 无水印直链（第三方 API） | **单条入库默认用这个** |
| `douyin-video-downloader` | 按抖音号批量拉全部作品 | 仅当明确说「批量/某账号全部」 |
| `douyin-bilibili-ingest` | 入库规范权威版（铁律 + frontmatter 模板） | 拿不准格式时读它 |
| `douyin-obsidian` | 抖音→Obsidian 专项 | 抖音侧笔记格式 |
| `douyin-kb-feed` | 抖音内容喂知识库 | 持续订阅类需求 |
| `media-import` | 通用媒体入库 | 非短视频的通用媒体 |
| `realtime-video-understanding` | 实时视频理解 | 需要逐帧语义而非转录时 |

**注意**：这些技能是**在别的机器上写的**，脚本路径（常见 `/Users/【BOSS英文名】/...`）在本机不存在。
读它们的 SKILL.md 取规范，**别直接调它们的脚本**——先跑 `scripts/preflight.py` 确认本机能力。

## 查重规则
共享库已占用 `douyin-*` / `video-*` / `*-ingest` 等命名空间。
自建技能前：`ls /opt/nas/volume2/2-AI/skills | grep -i <关键词>`。
撞名的后果是 `skill_view` 报 `Ambiguous skill name` 直接拒载，不是覆盖。

## 目录规范（铁律，全公司一致）
```
抖音 → 08-抖音视频学习/<连字符标题>.md
B站  → 07-B站视频学习/<连字符标题>.md
策略 → 02-策略方案/
通用 → 11-提炼沉淀/
图片 → attachments/ + ![[xx.png]]
```
