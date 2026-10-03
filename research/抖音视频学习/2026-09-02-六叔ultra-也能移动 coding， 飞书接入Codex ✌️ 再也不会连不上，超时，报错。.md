# 也能移动 coding， 飞书接入Codex ✌️

- 来源：抖音
- 作者：六叔ultra
- 链接：https://www.douyin.com/video/7647576377244632817
- aweme_id：7647576377244632817
- 发布时间：2026-06-05 00:22
- 抓取时间：2026-09-02

## 一句话
把 Codex 接进飞书，手机上就能 vibecoding；集成文档、表格、群聊，连不上/超时/报错的问题也顺手解决了。

## 章节要点（视频自带）
- 00:02 引言
- 00:11 接入后的效果展示：翻译文档、生成手绘风格图片并插入文档等
- 00:51 群组功能：用群组创建「选题搜索群聊」「图片设计群组」，实现专业任务自动化
- 01:20 接入方法：通过开源对接项目 + 创建向导完成接入，实现手机端 vibecoding

## 关键工具（开源项目）
**lark-channel-bridge**（作者：张咋啦 / Zara）
```bash
npm i -g lark-channel-bridge
lark-channel-bridge run --agent codex   # 终端出二维码，飞书扫码，自动建 PersonalAgent 机器人
lark-channel-bridge start               # 测通后后台常驻
```
- 配置落在 `~/.lark-channel/config.json`
- 支持流式输出、Markdown 渲染、群聊 @机器人、话题 thread、文档评论 @机器人
- 评论区有人用 `npm i -g lark-channel-bridge` + `lark-channel-bridge run` 跑通

## 原文文案
也能移动 coding，飞书接入Codex ✌️ 再也不会连不上，超时，报错。随时随地 vibecoding，而且集成文档、表格和群聊功能，用起来更加丝滑🤙 PS: 感谢博主@张咋啦 提供的工具 #真实生活分享计划 #青年创作者成长计划 #ai新星计划 #vibecoding大赏 #codex

## 封面
![[attachments/7647576377244632817/page_02.png]]

## 其他截图
![[attachments/7647576377244632817/page_03.jpeg]]
![[attachments/7647576377244632817/page_18.webp]]
