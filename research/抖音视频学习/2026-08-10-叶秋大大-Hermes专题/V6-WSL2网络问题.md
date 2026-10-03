# V6 零 Token 使用 Hermes 常见问题 - WSL2 网络问题

> **作者**：叶秋大大
> **来源**：https://v.douyin.com/rICjc6UDioQ/
> **采集日期**：2026-08-10
> **转录引擎**：SenseVoice-Small | 视频时长 ~60 秒
> **质量评分**：⭐ 2/5（**有具体命令**，但场景不是你的）

---

## 🎯 解决的具体问题

> WSL2 里跑 Hermes，连接不上 Windows 主机里跑的"网页大模型转 API"工具（127.0.0.1 不通）

**这是真实存在的网络问题**——WSL2 看到的 `127.0.0.1` 是它自己虚拟机的 localhost，不是 Windows 主机的。

---

## 视频给的解决方法

> "在 WSL2 终端里输入一条命令，就能获取到 windows 主机服务器的地址"

**作者是 Mac 用户**（他原话："我自己用的是 mark 系统"），所以**没给完整命令**。

但根据 WSL2 文档，**这条命令就是**：
```bash
cat /etc/resolv.conf
# 找到 nameserver 那一行，比如：
# nameserver 172.20.240.1
```

这个 IP 就是 WSL2 看到的 Windows 主机地址。

---

## 实际修复流程（视频未贴全，但可推断）

```bash
# 1. 在 WSL2 终端
cat /etc/resolv.conf
# 记下 nameserver 后的 IP（比如 172.20.240.1）

# 2. 在 Hermes 配置里
# 把 base_url 从 http://127.0.0.1:PORT/v1
# 改成    http://172.20.240.1:PORT/v1

# 3. 验证
curl http://172.20.240.1:PORT/v1/models
```

---

## ⚠️ 视频没说清楚的关键点

| 缺口 | 影响 |
|---|---|
| **没贴 `cat /etc/resolv.conf` 这个命令** | 第一次看不知道怎么解 |
| **没贴新的 base_url 完整格式** | 配置时容易填错 |
| **没说明 `172.20.x.x` 段是 WSL2 默认网段** | 不熟网络的人不知道该信哪个 IP |

---

## 💡 真实可复用部分

**对你**：**几乎用不到**——
- 你用 Mac，不用 WSL2
- 你用火山方舟 API，不在本机跑转 API 工具
- 你已停用 OpenClaw 和 oMLX

**但作为知识**：WSL2 网络隔离是个**真实坑点**，未来如果你或者你团队谁用 WSL2 跑 AI 工具，这段能救急。

---

## 🎯 衍生知识点（可顺手入库）

- WSL2 默认网段：`172.16.0.0/12` 范围
- WSL1（已弃用）和 WSL2（默认）网络模型完全不同
- 如果你以后给团队写"Hermes 跨平台部署指南"，这一节要写进去

---

## 📎 原始记录

- 视频：https://v.douyin.com/rICjc6UDioQ/
- Raw：`~/跨境电商/知识库/raw_docs/零Token使用HermesAgent常见问题总结 深扒Hermes源码以问题为导向整理出更快更省力.md`
- 转录字数：1545 字
- 跑通耗时：6 秒
