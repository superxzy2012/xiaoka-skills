# 组网 SSH 打不通：22 端口在隧道层被废，改用 2200 反代

## 先分清是哪一头（2026-10-21 定案）

| 现象 | 含义 |
|---|---|
| 目标端口 `mapping succ` 后 `sent 0 recv 0 err timeout`，**多个端口同时如此** | 那台机器的 nblink 会话死了，让对端重启客户端 |
| 只有 22 超时，其他端口（2222/3000/3456）正常 | 隧道没问题，是本地 loopback→22 被挡 → 用本文的 2200 反代 |

实测对照：Mac mini `100.66.1.3`（peerid `05C4C5154FBC636COW`）22 和 16880 **同时**超时 = 客户端侧问题；NAS `100.66.1.7` 只有 22 超时而 2222 正常 = loopback 问题。

## 蜂群节点归属（别再混）

两个云端节点是**两台独立机器**，配错就串台：

| 节点 | 位置 |
|---|---|
| 星期五 / QUEEN | 云端 VM `100.66.1.6`（peerid `A6EACE9FF0406464OW`，`systemd --user hermes-gateway`） |
| 小豆-新Hermes | **另一台云端 VPS，IP 未知，必须让小豆自报**（Hermes default profile、工作区 `/home/agentuser/A2A`） |
| 旧 Mac 端小豆 | **已停用作废**（旧址 `/Volumes/2-AI/A2A`、`launchd ai.hermes.gateway`），与现小豆无关 |

别把 `.6` 当小豆，也别把 `.6` 的配置套给小豆。

## 现象（两端都中）

- `ssh DY@100.66.1.7` → `Connection closed by 100.66.1.7 port 22` 或直接 timeout
- 裸 socket 连 22 能连上，但**永远拿不到 `SSH-2.0-...` banner**
- 同一台机器换 2222（Gitea SSH）立刻出 banner → 说明隧道数据面本身是好的

## 根因（nblink 日志实证）

```
[TCP] 100.66.1.7:22 -> B84CEAA15FDF8765OW 127.0.0.1:22 mapping succ
[TCP] 100.66.1.7:22 -> ... 127.0.0.1:22 lo 0 closed sent 0 recv 0
      err dial tcp 127.0.0.1:22: i/o timeout
```

nblink 的对端落地方式固定是**拨 `127.0.0.1:<端口>`**。宿主上 loopback→22 这一跳被挡（sshd 自己确实是 `0.0.0.0:22` 在听，LAN 直连能出 banner），于是隧道侧 5s 拨号超时 → 对外表现为「连接被关」。
**不是端口映射没配，也不是 sshd 没开。**

## 修法（不需要 root，不动 sshd、不动防火墙）

在 NAS 上起一个 host 可达的 TCP 反代，把非 22 的本地端口转到 22：

```bash
sudo -n /usr/bin/docker run -d --name ssh-mesh-relay \
  -p 2200:2200 --restart=unless-stopped \
  python:3-alpine python3 -c "<反代脚本，见 scripts/ssh_mesh_relay.py>"
```

要点：
- **必须用 `-p 2200:2200` 发布端口**，不能只 `--net=host`（实测 host 网络模式下 loopback 仍取不到 banner；走 docker 发布才通）
- 反代内部 `LISTEN=("0.0.0.0",2200)`，`TARGET=("192.168.199.2",22)`（写宿主 LAN IP，不要写 127.0.0.1）
- 客户端用法：`ssh -p 2200 DY@100.66.1.7`

## 验收标准（三条都过才算通）

1. 从**另一台**组网节点（如云端 `100.66.1.6`）连 `100.66.1.7:2200` 能读到 `SSH-2.0-OpenSSH_...`
2. 用真 ssh 客户端跑通一次命令（`SESSION_OK`），不是只测 banner
3. `docker inspect` 里 `RestartPolicy=unless-stopped`，重启后自动回来

## 踩过的坑

- 用 `nc 127.0.0.1:2200` 在宿主 netns 里测**会假阴性**（拿不到 banner 但隧道其实通）——判据要用另一台机器 + 真 ssh 客户端
- `curl http://100.66.1.3:16880/` 返回 `000` 只说明那台机器的隧道没起来，不能推断 NAS 侧有问题
- 端口扫描里 `CONNECT_ONLY(no data)` 对 HTTP 服务是正常的（服务端等请求），只有对 SSH 这类**先发 banner** 的服务才代表故障
