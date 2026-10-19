# AI 共享迁移冻结 · AI-SHARE-MIGRATE-20261018

- 冻结开始：2026-10-18（飞书群通知，小米-codex SRE 负责）
- 范围：`/volume2/2-AI` → `/mnt/@usb/sde1/2-AI`（Obsidian、skillbox、A2A 落袋）
- 容器内路径：`/opt/nas/volume2/2-AI`
- 冻结要求：**暂停一切对该共享的写入与 A2A 落袋**（inbox/outbox/processed、vault、skills 软链目标）
- 解冻信号：小米-codex 的恢复通知到达前，一律只读
- 例外：无。即使有新 A2A 任务落 inbox，也不写 outbox、不移 processed，等恢复通知后补
- 本地写入仍可用：`/opt/data`（容器自身存储，不在迁移范围）
