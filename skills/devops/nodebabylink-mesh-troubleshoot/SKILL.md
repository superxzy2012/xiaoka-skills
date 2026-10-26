---
name: nodebabylink-mesh-troubleshoot
description: Use when 节点小宝/绿联组网不通，或要判断客户端与服务端该不该升级/降级。先用 RouteAdd 权威表定位对端 IP，再用 16880 探针判定数据面；单节点掉线用三角定位判定，再用跳板隧道绕过。
---

# 节点小宝（绿联远程组网）排障

NAS 上跑的是 `owjdxb` 容器（`ionewu/nblink`，`--network host`），组网网段 `100.66.1.x`。
排障只有一条主线：**先确定「对端 IP 到底是谁」，再谈隧道。** 跳过这一步会在错误的机器上查一整轮。

## 铁律 0：peerid↔主机↔IP 只认 NAS 自己的 RouteAdd 日志

任何人（含另一个 agent、另一台机器的自检报告）告诉你「对端 NAS peer = XXX」「NAS 是 100.66.1.5」，**都不算证据**。
服务端下发的路由表才是权威，它落在 `NodeBabyLinkService.log` 的 `RouteAdd` 行里，`Comment` 字段就是主机名。

```bash
SVC=/data/store/OWData/owjdxb/.ownbsv/NodeBabyLinkService.log
ssh -o BatchMode=yes -i /opt/data/.ssh/id_ed25519 DY@192.168.199.2 "
  sudo -n docker exec owjdxb sh -c \"grep -a RouteAdd $SVC | tail -12\" \
  | sed -E 's/^([0-9-]+ [0-9:]+).*Pid:([A-Z0-9]+).*LocalIp:(100\.66\.1\.[0-9]+).*Comment:([^ ]*).*/\1 | \2 | \3 | \4/'"
```

输出即「时间 | peerid | 组网IP | 主机名」。本机自己的 peerid 从进程参数取：

```bash
sudo -n docker exec owjdxb sh -c "ps aux | grep -o 'peerid [A-Z0-9]*' | head -1"
```

**为什么必须这样查**：组网 IP 会重排（历史上有过 .5→.7 变动），peerid 是稳定的。对方报告里写「NAS peer = 076ED239...」而日志显示该 peer 是 `super`（Windows），就会导致云端一直打 Windows 的端口，而 Windows 上没有目标服务 —— 症状恰好是「TCP 建连但零字节」，看起来像隧道坏了，其实连错机器。

**认机器不认名字。** agent 名（小豆/星期五…）会在迁移后指向完全不同的主机：同名旧实例停用、新实例在另一朵云，
旧 IP 与旧路径一并作废。判定某台机器上跑的是谁，读它自己的 `~/.hermes/.env` 的 `FEISHU_APP_ID` 和
`~/.hermes/profiles/` 列表，不要按主机名或「云端 Hermes」这种描述去猜。一台机器上只起了一个网关实例时，
直接排除「另一个 agent 也在这台」的假设 —— 在那台上翻 profile 找别人的目录是白花时间。

### 自报 peerid 必须回本机核对：字母 `O` 与数字 `0` 是最常见的抄错位

peerid 固定 18 位、以 `OW` 结尾（`O` 是字母）。对端截图或口头报过来的值**不能直接拿去绑定** ——
先在那台机器上读权威位置：

| 位置 | 内容 |
|---|---|
| Windows `C:\Program Files (x86)\nblink\NodeBabyLinkClient.ini` | 完整 peerid（`[A-Z0-9]{18}`，结尾 `OW`） |
| Windows `C:\ProgramData\NodeBabyLinkService\nblink.dat` | **只有短 pid**（12 位，如 `pid = 9595DAD2AA42`），当完整值绑必失败 |
| NAS `http://<NAS>:9118/` 跳转 URL 的 `pid=` 参数 | 该机 peerid，无需账号即可取 |

日志里 `InvalidClientPeerId []` 的方括号**本来就是空的**，不是「读到了空值」，别据此判断客户端没拿到 peerid。

### Windows 客户端 `InitNBLink` 报错 = 服务端不认这个 peerid

```
ERROR glservice/nblink.go:84 InitNBLink          （错误消息为空）
ERROR datachannel/client.go:91 ConnectAndServe ctx.Done: EOF
```

判据是**日志里这条 ERROR 本身**，不是「网卡上没有 `100.66.*`」。relay 模式本来就不把组网 IP 下发到网卡，
拿「网卡无 100.66.x」当证据会产出一屏假「未绑定」。硬证据只有一条：从网关打它的 `100.66.1.x` 能不能连上。
ERROR 存在 + 网关侧探不到 = 账号未登录 / peerid 未绑定，不是网络故障。绑完仍不通，就清 `NodeBabyLinkClient.ini` + 状态文件
重启重生成 —— **peerid 会变，要再绑一次**，提前把代价说清楚，别让对方以为一次就能好。

**别把「等组网」当成阻塞**：对端有公网 IP 时先上反向隧道（见「组网不是唯一解」一节），
组网只是第二条更省事的路径，不是前置条件。

## 铁律 1：宿主网络只能借 `--net=host` 容器看，`sudo -n ip` 的输出是假的

**`sudo -n` 只免密 `/usr/bin/docker`，对 `ip` / `ss` / `iptables` 一律静默失败返回空输出。**
把「空输出」当成「没有接口/没有路由」，会直接得出「宿主根本没建隧道」的错误结论 —— 本技能上一版就是这么写错的。

宿主真实的隧道态：**有 `NodeBabyLink` 接口（MTU 1430）**，持有 `10.222.222.1` 本地虚拟网关，
`100.66.1.x` 全部 `via 10.222.222.1 dev NodeBabyLink`。所以组网是 **L3 路由 + relay 端口映射并存**，不是「没有 tun」。

```bash
A=docker.m.daocloud.io/library/alpine:3.18
# 宿主路由（100.66/10.222 全量）—— 唯一可靠读法
sudo -n docker run --rm --net=host $A ip route | grep -E '100\.66|10\.222|default'
# 宿主真实 IP（容器内没 ip 命令时）
sudo -n docker exec owjdxb sh -c "grep -B1 '/32 host LOCAL' /proc/net/fib_trie" | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | sort -u
# 接口清单 / 网络模式
sudo -n docker exec owjdxb sh -c "ls /sys/class/net/"
sudo -n docker inspect owjdxb --format 'Net={{.HostConfig.NetworkMode}}'   # host = 与宿主共享 netns
```

`ip -4 -br addr` 在 busybox/alpine 下可能返回空，**别据此判定没有地址**，用上面两条。
`10.222.222.1` 在 NAS 和 Windows 上同时出现是**正常的**（每台机器各自的本地虚拟网关），不是 IP 冲突，不要追。

**反向推论**：`ping 100.66.1.x` 恒通且 RTT < 0.5ms，是本地代答，永远不能用来判断链路。

### 「ping 全通 0.1ms」是 tun 本地代答，不是真通

对端（尤其是自建了 tun 的云端客户端）报「ping 100.66.1.1~.5 全通，rtt 0.04~0.1ms」时，这是它本机 tun 在**自己应答自己**：真实跨机 RTT 不可能 0.04ms。
配套症状是「所有端口 TCP 秒 accept 但零字节」= accept 发生在本地桩，数据面根本没出网。
判据：**RTT < 0.5ms 一律视为本机代答**，改用真实业务请求验证（见下）。

## 铁律 1.5：一发 16880 探针定生死

每台 nblink 客户端都在 **16880** 起一个管理 HTTP 口，任何路径访问它都回 `404` + 19 字节 body。
**对端 16880 能回 404，就证明「请求出去 + 响应回来」双向都穿过了隧道** —— 这一发比任何日志统计都硬。

```bash
for t in 100.66.1.6:16880 100.66.1.5:16880 100.66.1.7:3457 100.66.1.7:3000; do
  r=$(curl -s -m4 -o /tmp/b -w '%{http_code}' "http://$t/" 2>/dev/null); printf '%-20s %s %sb\n' "$t" "${r:-000}" "$(wc -c </tmp/b 2>/dev/null)"
done; rm -f /tmp/b
```

| 结果 | 判读 |
|---|---|
| `16880 → 404 19b` | 隧道双向通。**任何「隧道坏了」的结论到此作废**，回头查 IP 归属 / 目标端口有没有服务 |
| `16880 → 000` | 真·数据面不通，才轮到查 relay / 重启客户端 |
| `16880 → 404` 但业务端口 `000` | 打错机器（那台上没这个服务），不是链路问题 |

配合铁律 0 的权威表一起看：`100.66.1.5:16880` 有应答 = 那台是 Windows super，不是 NAS。

**但它只证明「网关发起」的连接能双向传数据**，不等于两个方向都自由：客户端主动发起连网关仍可能被团队白名单拦
（`[team] OnDeviceWhitelist: 0 entries`），见下面「只测网关→客户端方向」一节。

### 服务端日志 `mapping succ` 后 `sent 0 recv 0 err timeout` = 对端会话死，不是本机服务坏

`NodeBabyLinkService.log` 里同一条隧道 `mapping succ` 之后紧跟 `sent 0 recv 0 err timeout`，
**且对端多个端口（22 与 16880 之类）同时如此**，判读是那台机器的 nblink 客户端会话已死：
relay 建了映射却一个字节都没收到。此时白名单、版本号、端口映射、本机服务全是无辜的，
别在那四项上继续折腾——让对端彻底重启客户端后重测。

只有**单个端口**超时、其他端口正常时，才轮到怀疑本机 loopback 到该端口被挡
（NAS 上 `127.0.0.1:22` 被静默 DROP 就是这种形态，修法见
`references/ssh-over-mesh-22-blocked.md`）。

### `btlBW 0` 不等于隧道坏

`net_measure.go ... end btlBW 0 rateSent 132209 warmeUpSent 132209 phase Drain` 只是**relay 带宽探测**读数，
必须交叉验证 `share_dat.go:771 shareDataConnHealthCheck ... [n/5] speed rcv N/s snd N/s`：
双向非零 = relay 真在传数据（空闲态会掉到 20/s 级心跳，仍是通的）。

同理，`tunnel LAN accept ... use of closed network connection`、`tunnel NPTU start fail: ice.Dial: the agent is closed`、
`startTcpNatypeDetect ... NAT fail` 这三类刷屏**只说明直连打洞失败、退化成 relay**，不代表隧道没建立。
看到 `relay num/rated 5/5` + `all tunnel is ready` 就该按「通」处理。

## 铁律 1.6：端口存活用 banner 探针，别用 shell `/dev/tcp`

`timeout N bash -c 'exec 3<>/dev/tcp/$h/$p && head -c 60 <&3'` 这种写法会**静默假阴性**：实测对 5 台主机全部返回空，
而其中 3 台的 22 当时是通的。据此会得出「全网 SSH 都挂了」的错误结论，白查一轮。

用 python socket 建连后 `recv(80)` 读 banner：一条命令覆盖多主机多端口，而且 banner 自带版本与系统指纹，
能直接分辨「这是哪台机器」。

```bash
python3 <skill>/scripts/probe_ports.py 192.168.199.2:22 100.66.1.5:22 100.66.1.6:22 100.66.1.6:3457
```

判读规则：

| 结果 | 含义 | 下一步 |
|---|---|---|
| 有 banner | 端口真开，且对端进程真的应答了 | 继续测业务（16880 / HTTP / SSH 登录） |
| `TimeoutError` | 被安全组或防火墙丢包 | 换组网 IP 试，公网 22 超时是常态 |
| `ConnectionRefusedError` | 主机活着，但该端口没监听 | 去那台机器上查服务 |

- **超时与拒绝含义完全不同**，汇报时不能都写成「不通」。
- **shell 侧看 `rc=124`：这是「丢包」，不是「拒绝」。** 用 `timeout 5 bash -c 'exec 3<>/dev/tcp/<h>/<p>'` 探测时，
  `refused` 会**秒回**（内核 RST，耗时几毫秒），只有**无任何回应**才会把 `timeout` 耗满到点，退出码是 **124**。
  所以「rc=124 + 耗时约等于你给的超时值」= SYN 出去没人应 = 上游丢包/安全组未放行；
  「rc=1 且立刻返回」= 主机活着但端口没监听。两者不能用同一句话汇报。
  （`/dev/tcp` 只用来判**连不连得上**；要读 banner 仍然用 `scripts/probe_ports.py`，`/dev/tcp` 读 banner 会假阴性。）
- **任何「全通」/「全不通」先做反向对照再采信。** 探一个确定不存在的地址（如 `100.66.1.99`、`100.66.1.250`）：
  它也必须 `closed`；如果它也「通」，说明有代理/桩在接管，整批结果作废。
  同理可用 banner 交叉验真：真 SSH 会回 `SSH-2.0-OpenSSH_…`，对照地址应无任何字节。
  与「ping RTT < 0.5ms = 本机代答」是同一族陷阱，一个在 ICMP、一个在 TCP 层。
- 公网 IP 的 22 超时、组网 IP 的 22 通，是常态（安全组只放业务端口），不是故障。
- **绑 `127.0.0.1` 的调试口（Chrome 9222/9223 之类）从别的机器直探必然失败**：先在那台机器上
  `netstat -ano | Select-String ':9223'` 确认有没有监听，再用 SSH `-L <本地>:127.0.0.1:9223` 隧道探本地端口。
  直探远端 IP 失败 ≠ 服务挂了；不先看监听就把锅判给隧道，会重复排查错方向。

## 铁律 2：判定「服务是否真活着」用本机 127.0.0.1，不用组网 IP

```bash
# 管理面：应返回一大坨 openapi JSON
curl -s -m4 -o /dev/null -w ':%{http_code} %{size_download}b\n' http://127.0.0.1:3457/api/openapi.json

# 容器真身 + 端口绑定（必须是 0.0.0.0，不能是 127.0.0.1）
sudo -n docker ps -a --format '{{.Names}} | {{.Status}} | {{.Ports}}' | grep -iE 'obsidian|mcp|hive'
```

本机 200 = 服务没问题，故障在链路；本机也 000 = 服务挂了，才轮到重启容器。
**顺序不能反** —— 先怀疑链路会白查一轮，先怀疑服务会误重启健康的容器。

### 铁律 2 的补集：要给别的设备用的服务，验收必须从对端打

本机 `127.0.0.1` 通 **只证明进程活着，不证明组网能到**。新建的对外服务（relay、web 控制台、APK 下载页）
必须从**另一台组网节点**反向验证，否则「本机 200」会掩盖「绑错了 `127.0.0.1`」或「组网路由没生效」。

```bash
ssh <另一节点> 'curl -s -m8 -o /dev/null -w "%{http_code}\n" http://<NAS组网IP>:<端口>/healthz'
```

- 实测：容器绑 `0.0.0.0` + 宿主端口映射后，**组网无需任何端口白名单**，从 `100.66.1.6` 打 NAS 的新端口直接 200。
- 先验本机（服务层）→ 再验对端（链路层），两个都绿才算交付；顺序反过来会把「服务没起好」误判成「隧道不通」。
- 容器重建/换端口后要**重新从对端验一次**，不能沿用上次的结论。

## 铁律 3：MCP 端点不能用裸 TCP / GET 探测

Streamable-HTTP MCP 端点（`/mcp`）对非法请求**直接关连接**，表现就是「建连即断、零字节」。
用 nc / telnet / 浏览器 / GET 去探，必然得出「隧道坏了」的错误结论。

| 探测方式 | 正常返回 | 含义 |
|---|---|---|
| `GET /mcp` | `400` | 端点活着，拒绝 GET |
| `GET /` | `404` | 正常，无根路由 |
| `POST /mcp` + `initialize` | `200` + SSE | **唯一有效判据** |
| `GET /api/openapi.json`（管理面） | `200` + JSON | 服务健康 |

```bash
curl -s -m8 -i -X POST http://<IP>:3456/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"1"}}}'
```

成功返回 `HTTP 200` + `event: message` + `data: {"jsonrpc":"2.0","id":1,"result":{...}}`。
**`Accept` 必须同时含 `application/json` 和 `text/event-stream`**，缺一个会被拒。

## 判定「组网是否成功」：只测网关→客户端方向

`100.66.x` **不会出现在设备网卡上**（`Get-NetIPAddress -like '100.66*'` 为空是正常的），IP 由路由器层映射。

正确验收：从**网关（NAS）**发起 TCP 探测，拿到 SSH banner 才算通。

```python
socket.create_connection(("100.66.1.9", 22), 5).recv(64)
# b'SSH-2.0-OpenSSH_for_Windows_9.5\r\n'  => 通
```

**方向本应双向**：网关 → 客户端通，客户端 → 网关（`100.66.1.7:3000`/`:20128`）也通 —— 实测 Windows super 与 Windows Server 小豆打 `100.66.1.7:20128` 都拿到 `401`。某台客户端打不通网关，是**那台自己的故障**（最常见是 tailscale 的 CGNAT DROP，见下文「入站正常但出站全灭」），不是「组网天生单向」。用反向隧道把它盖过去，等于把可修的故障藏起来。

日志里 `[team] OnDeviceWhitelist: 0 entries, 0 pids` 是「团队白名单未启用」= 不限制，不是拦你的证据。

## 组网不是全连通：一个节点掉线时，别把结论推广到全网

「Windows → `.6:22` 通」只证明 **Windows 和 .6 之间**通，不代表 `.6 → .7` 通。
每台客户端各自向服务端注册自己的隧道，**某台掉注册 = 只有跟它有关的那几对不通**，其他节点互访照旧。
所以排障第一步是**三角定位**，而不是问一句「组网通不通」：

| 同一时刻的探测 | 结论 |
|---|---|
| A→B 失败，C→B 成功 | 故障在 **A 的出向 / A 的注册**；B 无辜 |
| A→B 与 C→B 同时失败，而 B 本机 `127.0.0.1` 200 | **B 掉出了组网**（进程活着 ≠ 注册在） |
| 所有对都失败 | 才轮到服务端 / 账号级故障 |

**`Empty reply from server`（curl exit 52）= relay 接了、对端没回**，判「对端客户端会话死」，不是发起方网络坏。
与 `000` 严格区分：`000` 是路断了，`52` 是路通但对面没人接 —— 汇报时不能都写成「不通」。

**掉线节点常常当场修不了**：`owjdxb` / `nas_agent_service` 进程活着但注册丢，重启要管理员权限
（`sudo -n` 只免密 `/usr/bin/docker`）。别卡在「等权限」，直接**跳板绕过**：找一台同时能到 A 和 B 的节点，
在 A 侧起本地转发，把应用配置里的组网 IP 换成 `127.0.0.1`。

```bash
# 在 A（应用所在机器）上，B 用物理 IP 而不是组网 IP
ssh -i ~/.ssh/<key> -o StrictHostKeyChecking=no -o BatchMode=yes \
  -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes \
  -N -L 127.0.0.1:<本地端口>:<B物理IP>:<端口> <跳板用户>@<跳板组网IP>
```

固化成 `systemctl --user` unit（`Restart=always`、`RestartSec=10`、`ExitOnForwardFailure=yes`），
并 `loginctl enable-linger <user>` —— 否则最后一条 SSH 会话结束时 unit 被回收，隔天又「自己坏了」。
验收：`systemctl --user is-active` + `show -p Linger` + 一次真实业务请求（不是 `-T` 小包）。

**隧道建在 Linux 侧、穿 Windows 出去，不要让 Windows 托管长连接 `ssh -N`**：非交互会话里
`Start-Process ssh -N -R ...` 既没有监听也没有报错，纯白花一轮。Windows 只当跳板（它的 22 口往外连是可靠的）。

**跳板需要私钥时给专用 key，别搬管理员私钥**：在跳板机上 `ssh-keygen` 一对新的、只授权到该跳板，
`chmod 600`。实在要搬，用完即删；Windows 侧删除常被 ACL 挡住（只给了 `(R)`），先
`icacls <file> /inheritance:r /grant:r "$($env:USERNAME):(F)"` 再 `Remove-Item`。

**绕行不是修复**：跳板一关机就又断，根因（掉线节点重新入网）没解决前必须如实分开说，
别让用户以为已经收尾。

## Windows Server 无头跑 4.5.2 桌面版（可行，别放弃）

GUI 主程序是 `desktop\NodeBabyLinkDesk.exe`（Flutter，session 0 起不来，20 秒内退出）——**但它不是必需**：

- 服务 `NodeBabyLinkService.exe` 单独跑即可完成绑定 + 组网注册。
- 验收标志：`http://127.0.0.1:16880/glp/sipstate` 返回 `"msg":"GLCS_CONNECTED","state":1`。
- 日志里 `ProcFind recv &{Name:[NodeBabyLinkDesk.exe]}` 每 2 秒刷一次是**正常噪音**，不代表故障。
- `gateway/switch: pid=` 为空也常见，SIP 连上后路由会自己下发（`addRoute 100.66.66.66/32 succ`）。

## 升级后必须重新扫码绑定

4.3.5 → 4.5.2 peerid 会变（`...26377OW` → `...2636BOW`），改 ini 或还原 `nblink.dat` **都无效**，服务端报 `rtn=10208 设备未绑定`。唯一解法：设备页 `jdxb_server_pc_v3/?client=windows&hostname=<h>&pid=<新peerid>` 重新扫码，绑定后服务端会**分配新 IP**（旧 100.66.1.8 → 新 100.66.1.9）。

## 版本与升级：客户端别手动动，服务端是唯一拍板点

**版本不统一本身不是故障。** 实测服务端 4.3.5 + 客户端 4.5.3 可以正常传数据（NAS 日志 `mapping succ` 后
`sent 5947 recv 4305`）。所以「版本错配 → 数据面必死」不成立，别把版本对齐当成首选修复。

**升级策略**：

- 客户端（Windows / Linux / Mac）**不要手动升降**：`ownbsvman` 每次启动都先做版本同步再拉起服务，
  换二进制会被覆盖，白费功夫；客户端落后一两个小版本无所谓。
- **NAS 服务端容器是唯一需要人拍板的点**：它是所有人的汇聚点，重启即全员掉线，必须挑窗口。
- 真要版本对齐时**服务端先升、客户端随后自动跟上**，不要反过来把客户端升到远新于服务端。
- 只有「所有客户端都连不上 + 各自重启客户端也无效」才轮到升服务端镜像。

查现状版本（一次问全，别按名字猜）：

```bash
# 服务端（NAS）
sudo -n docker inspect owjdxb --format 'image={{.Config.Image}}'
sudo -n docker exec owjdxb sh -c "grep -a glversion <SVC> | tail -2"      # 报 version 4.x.x
# Linux 客户端
cat ~/owjdxb/ownbsv/.version; sudo -n md5sum ~/owjdxb/ownbsv/NodeBabyLinkService
# Windows 客户端：读 exe 的 VersionInfo（引号处理见「远端 Windows 上跑长命令」）
```

### 想钉住旧版本：改二进制和改 /etc/hosts 都无效

`ownbsvman` 在**每次启动**时先做版本同步、再拉起服务，日志里 `ownbsv start, .ver=<版本>` 是**同步之后**才打的
—— 看到这行说明换版已经发生，不代表「当前还是旧版」。把旧版二进制覆盖进 `ownbsv/` 后只要重启一次
（哪怕只是 `serv.sh start`），它就会把新版下回来覆盖。判据用 `md5sum` 与备份比对，别只看 `.version` 或进程启动时间。

`/etc/hosts` 屏蔽 `pcdntest2.ionewu.com` **拦不住**（加完仍被升级，它走别的通道/IP），别拿它当版本钉，
白留一条无效改动。要真钉住只能停掉 ownbsvman 的版本同步，代价是放弃官方修复 —— 属于要 BOSS 拍板的事。

### 控制面全绿、数据面全死：先重启客户端，再谈版本

症状：RouteAdd succ、接口/路由/MTU(1430) 全对、`addRoute ... succ (sys 100.66.1.0/24)` 照打，
但对端 TCP 连任何端口（3000/3456/22）**全部 SYN 超时**；服务端日志里**看不到这些探测的 TCP mapping**；
对端刷 `pxymap/glcrouter.go:20 MapingRoute err: NotFound . addr <服务端LAN IP>`。

判定与修复顺序：

0. 先在故障端 `tcpdump -ni NodeBabyLink` 抓一次（同时另开一个 curl 打对端）：**SYN 出、SYN-ACK 回、本机又重传 SYN** = 回包被本机防火墙丢了
   （tailscale 的 `100.64.0.0/10` DROP 规则），此时重启客户端、换版本都无效，直接 `iptables -S ts-input`。
1. 在故障端发探测，同时在服务端 `grep <peerid> NodeBabyLinkService.log | tail`：**零 mapping 记录 = 包没穿隧道**。
2. `mapping succ` 后紧跟 `sent 0 recv 0 err timeout` = **客户端会话死了** → **重启客户端**
   （`serv.sh stop` 再 `start`，或重启 NodeBabyLinkService 服务），这是最常见也最便宜的一步。
3. 重启无效才做版本对齐，且**优先动故障端那一台**（影响单机）；升服务端会瞬断全员，须批窗口。
4. 别被 `addRoute succ` 骗：**控制面协议与数据面协议分离**，route 协商成功 ≠ 隧道能传数据。
5. 组网死时**公网通道照常可用**（GitHub 主通道），别因为组网不通就以为整台机器失联。

### 服务端（NAS 容器）「升级到最新」通常是伪需求：先查官方镜像内部版本

NAS 上跑的是 UGOS 版镜像 `ionewu/nblink:v4.2.3-821`，**镜像 tag 与内部 glversion 不是一回事**
（tag v4.2.3，内部 `ownbsv/.version` 与日志 `glversion` 都是 4.3.5）。判断「有没有新版」只有一条硬证据：

```bash
# 1) 现网内部版本 + 二进制指纹
sudo -n docker exec owjdxb sh -c "cat /owjdxb/ownbsv/.version; md5sum /owjdxb/ownbsv/NodeBabyLinkService; ls -l /owjdxb/ownbsv/NodeBabyLinkService"
# 2) 官方镜像同样查一遍（Hub 直连被墙，走 1ms 镜像）
sudo -n docker pull docker.1ms.run/ionewu/owjdxb:latest
sudo -n docker run --rm --entrypoint sh docker.1ms.run/ionewu/owjdxb:latest \
  -c "cat /owjdxb/ownbsv/.version; md5sum /owjdxb/ownbsv/NodeBabyLinkService; ls -l /owjdxb/ownbsv/NodeBabyLinkService"
```

2026-10-25 实测：官方 `ionewu/owjdxb:latest` 内部也是 **4.3.5**，二进制构建于 08-25；
NAS 现网二进制构建于 **10-01**（更新），版本同为 4.3.5。**即服务端已是最新，无可升版本**，
客户端 4.5.2/4.5.3 属于客户端线，服务端发布滞后于客户端属正常，实测兼容。

要点：① 官方仓库名是 `ionewu/owjdxb`（不是 `nblink`），可用 tag 见
`curl -s https://docker.1ms.run/v2/ionewu/owjdxb/tags/list`；② Hub 直连 `registry-1.docker.io` 超时，
`daemon.json` 里的 registry-mirrors 对 token 环节无效，改用 `docker.1ms.run/<repo>` 前缀可拉；
③ 重启容器**不会**让服务端自升级（ownbsvman 在容器里不做版本同步，与客户端行为不同），别指望靠 restart 升版；
④ 升级/重启前先 `cp -a /owjdxb/ownbsv` 与 `/owjdxb/bin` 到 `/data/store/OWData/owjdxb/` 持久层备份，
重启约 40 秒，全员瞬时掉线；⑤ 宿主机 `DY` 只对 `/usr/bin/docker` 免密，其余 sudo 要密码；
⑥ 改 `/etc/hosts` 这类系统文件会触发审批：**审批超时 = 未同意**，不要改写命令重试，
先把「加了什么、没生效、怎么撤」原样报给 BOSS 并请他重批，再执行撤销——留一条无效改动在系统里
比没做更糟（后续排查会把它当已生效的配置）。

### 入站正常但出站全灭 = tailscale 的 CGNAT DROP 规则（2026-10-25 实测，Linux 客户端）

**症状**：该节点能被别人连进来（SSH、16880 探针都正常），但它自己访问任何 `100.66.1.x` 全部超时；
`curl http://100.66.1.7:20128` 卡满 8 秒返回 000；节点小宝日志里刷
`pxymap/glcrouter.go:20 MapingRoute err: NotFound . addr 192.168.199.2`。

**定位手法**（关键，别靠猜版本）：
```bash
sudo tcpdump -ni NodeBabyLink -c 12      # 同时另开一个 curl 打对端
```
会看到 `SYN 出 → SYN-ACK 回 → 本机又重传 SYN`，说明**回包在内核 INPUT 阶段被丢了**，
不是隧道没通、也不是版本不兼容。再查防火墙：
```bash
sudo iptables -S ts-input | head
# -A ts-input -s 100.64.0.0/10 ! -i tailscale0 -j DROP   ← 就是它
```
节点小宝的 `100.66.1.0/24` 落在 tailscale 的 CGNAT 段 `100.64.0.0/10` 里，回包从
`NodeBabyLink` 进来（非 `tailscale0`）即被 DROP。

**修复**（一行，立即生效）：
```bash
sudo iptables -I ts-input 1 -i NodeBabyLink -j RETURN
```
验证：`curl -m8 http://100.66.1.7:20128/v1/models` → 401（0.5s 内），Gitea 3000 → 200。

**持久化**：`ts-input` 是 tailscaled 自己建的链，开机/重启 tailscaled 会重建并丢我们的规则。
用两个 unit（已装于 100.66.1.6，enabled + active）：
- `nblink-fw.service`：oneshot，`After=tailscaled.service`，`ExecStart=/bin/sh -c 'iptables -C ts-input -i NodeBabyLink -j RETURN 2>/dev/null || iptables -I ts-input 1 -i NodeBabyLink -j RETURN'`
- `nblink-fw-check.timer/.service`：`OnBootSec=2min` + `OnUnitActiveSec=15min` 周期性补规则（tailscaled 自动更新会重启并重建自己的链，光靠开机那一次不够）

自愈验收法：`iptables -D ts-input -i NodeBabyLink -j RETURN` 故意删掉 → `systemctl start nblink-fw-check.service` → 规则应回来且 `curl -m8 http://100.66.1.7:20128/v1/models` 回到 401（50ms 级）。
改 `/etc/systemd/system` 属系统配置，动手前先跟 BOSS 报备。

**最容易误判的一点**：入站是客户端把对端请求映射到 `127.0.0.1:port` 完成的，**根本不经过 tun**，
所以「我能 SSH 进去」完全不能证明该节点数据面健康。判断必须双向：从该节点**主动**打对端。

**排障顺序修正**（推翻「先降版本」的老思路）：① 先双向连通性（主动打对端）；② tcpdump 看是没发包还是回包被丢；
③ 查 tailscale/防火墙 CGNAT 规则；④ 最后才谈客户端版本 —— 本例 4.3.5 与 4.5.3 表现完全一致，版本无关。

## 新节点接入（给 peer 开 SSH 通道）

对端不在组网里时，排障没有意义，先把它接进来。**NAS 侧不需要任何改动**：`owjdxb` 是 `--network host`
+ `/dev/net/tun` + `NET_ADMIN` 的完整节点（不只是 relay），新 peer 一上线就能从 NAS 直接打它的 `100.66.1.x`。

给对端 agent 的接入清单一次给全，别拆成五轮问：

1. 装 NodeBuddy 客户端（`ionewu/nblink`），用**同一个账号**登录，拿到自己的 `100.66.1.x`。
2. 开 sshd：Linux `systemctl enable --now ssh`；macOS 系统设置 → 通用 → 共享 → 远程登录。
3. 把本机公钥追加到对端 `~/.ssh/authorized_keys`（600）。公钥用 `ssh-keygen -y -f <私钥>` 现取，
   别凭记忆粘贴——`known_hosts` 行和公钥长得几乎一样，贴错就是「授权了什么也没授权」。
4. 让它回四个值：组网 IP、ssh 用户名、端口、它的 A2A 根路径。
5. 拿到值立刻实测 `ssh -i <key> <user>@<ip> 'hostname; date'`，通了再投凭据、再谈业务。

### 接驳脚本写成「组网 IP + 密钥优先，公网 IP + 密码兜底」

对端入网后，SSH 执行器不要只留一条硬编码 IP。按 `[组网IP, 公网IP]` × `[密钥, 密码]` 顺序试，谁先通
就把实际路径打到 stderr（`[via <ip> <mode>]`）：组网通时连密码环境变量都不用给，组网掉线/公网换 IP 时
自动回落，而且报错能直接分辨是「路径变了」还是「认证错了」。

```python
HOSTS = ["100.66.1.9", "43.153.26.131"]   # 组网优先，公网兜底
for host in HOSTS:
    for mode in ("key", "pw"):           # pw 只在环境变量有值时才试
        ...
```

绑定 IP 变更（重绑、升级、IP 重排）要同步改**三处**：执行器 `HOSTS`、A2A 名册里的组网 IP 行、隧道脚本目标。
只改一处会留下「某个脚本还打旧 IP」的静默故障。

**装完立刻清对端残留**：安装包（250MB 级）+ 分段 `part*.bin` / `t*.bin` / `range_test.bin` 用完就删，
别留在对方磁盘上——清完顺手把 `C:\A2A` 之类的目录列一遍，确认只剩仓库和工具链。

**判据细节**：TCP 建连成功但 `recv` banner 超时/为空，**不等于 sshd 没开** —— relay 先 accept 再连后端，
后端慢或没监听都长这样。banner 只用来认机器；「端口通不通、能不能登录」以 `ssh` 自己的三态为准
（登录成功 / `Permission denied` = 通但没授权 / `Connection timed out` = 真不通）。

### 组网不是唯一解：有公网 IP 的 peer 直接上反向隧道

「新节点连不进来」先问一句：**它有没有公网 IP？** 有的话不必等组网，先分两个方向测：

| 方向 | 实测 | 含义 |
|---|---|---|
| NAS → 对端公网 `:22` | 通 | 通道可以建 |
| 对端 → NAS | 不通 | NAS 在 NAT 后，这正是它非要组网的原因 |

由 NAS 主动 ssh 过去，把 NAS 的服务反向映射到对端的 `127.0.0.1`：

```bash
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -i /opt/data/.ssh/id_ed25519 \
  -R 127.0.0.1:22022:<NAS>:22 -R 127.0.0.1:23000:<NAS>:3000 \
  -R 127.0.0.1:23456:<NAS>:3456 -R 127.0.0.1:23458:<NAS>:3458 \
  <user>@<对端公网IP>
```

对端随即能用 `git clone http://127.0.0.1:23000/<owner>/<repo>.git`、`http://127.0.0.1:23456/mcp`。
不占节点小宝免费额度（免费版只 2 台互联，蜂群早超了）、不走 relay 中转、带宽是公网直连。
Windows 对端同样认 `-R`（OpenSSH for Windows 支持绑 `127.0.0.1`）。

## 铁律 4：已入网的 peer 不要再追加 SSH 穿透/反代（治理令优先）

当对端**已经在组网里**（NAS 路由表有它的 `100.66.1.x`、`16880` 探针回 `404 19b`），它的 Gitea / MCP / 任意服务端都**直接走组网 IP 访问**，不要再为它起 `ssh-mesh-relay` 反代容器、也不要塞 `ssh -R/-L` 持久隧道。理由：多做一条 SSH 穿透既扩大攻击面，又违反「新节点只走异地组网、禁 SSH 穿透」的治理令；而且某个节点若按旧网络假设把 onboarding 回执的 channel 写成「SSH 反向隧道 23000」，纠正后必须改回组网 IP `100.66.1.7:3000`。

判据：先跑 16880 探针确认对端在网（`404 19b` = 在网），再 `curl 100.66.1.7:3000/api/v1/version` 确认服务可达；两者都绿就说明**组网即通路，直接拿组网 IP 给对端 clone / 调 MCP**，不要碰 `22`/`2200`/`23000` 任何 SSH 入口。只有「对端还没入网、但有公网 IP」才走上一节的 reverse tunnel——那是入网前的临时通道，不是入网后的叠加层。

### 重启隧道前先确认旧监听已死：残留监听会「accept 然后挂死」

隧道进程被杀/重启后，对端 sshd 的**转发监听子进程可能残留**并继续占着那个端口。新隧道绑不上（只打一句
`remote port forwarding failed`，ssh 本身照常活着），而客户端连过去会被**旧监听 accept 然后永远不回数据**——
症状是「端口在听、TCP 能连、零字节、无报错」，跟「隧道不通」完全不同，很容易误判成协议/防火墙问题。

```powershell
netstat -ano | Select-String ':2222'    # 记 PID，确认是不是上一轮留下的 sshd 子进程
Stop-Process -Id <pid> -Force           # 只杀那个监听进程，别动 sshd 服务
# 重启隧道后再看一次 netstat：监听 PID 必须变
```

**验收必须用真实业务请求（长连接 / 大数据量），不能用 `ssh -T` 这种一发即回的小请求。**
小包能穿过旧监听和半死隧道，`git push` 不行——用轻请求验收会把「半个通道」判成「通了」。

### 远端 Windows 上跑长命令：批处理 + 重定向 + 读日志

把 `ssh` / `git` 直接塞进远程 exec 通道（paramiko / `powershell -Command`）会挂：输出被整段缓冲，
进程又在等 stdin，于是「无输出、无报错、超时」。可靠形态是 `.bat`（ASCII + CRLF，重定向补 `< NUL`）
由 `.ps1`（UTF-8 BOM）`Start-Process -WindowStyle Hidden` 起，`Start-Sleep` 后 `Get-Content <log> -Tail 8`。
完整模板见 `a2a-file-bus` → `references/github-mirror-transport.md`。

**引号地狱用 `-EncodedCommand`**：经 `pc.sh` / ssh 传 `powershell -Command "..."` 时，嵌套引号和
`Program Files (x86)` 里的括号会被本地 shell 与 PowerShell 各吃一层（典型报错 `CommandNotFoundException: x86`）。
本地生成 UTF-16LE base64 再传，一次搞定：

```bash
B64=$(python3 -c "import base64;c='Get-Item \"C:\\\\Program Files (x86)\\\\nblink\\\\nblink.exe\" | % { \$_.VersionInfo.FileVersion }';print(base64.b64encode(c.encode('utf-16-le')).decode())")
pc.sh "powershell -NoProfile -EncodedCommand $B64"
```

读 Windows 客户端版本就走这条路（`Get-Item <exe> | % { $_.VersionInfo.FileVersion }`），
别用 `dir` 猜，也别信 `Get-NetIPAddress` 之类与组网无关的自检。

**Windows 客户端的控制台端口不是 9118。** `9118` 是绿联 NAS（UGOS）内置版专用；Windows 版 `NodeBabyLinkService` 实测监听：
`127.0.0.1:16880`（管理口，任何路径 404）、`127.66.36.18:2443`（HTTPS）、`127.66.36.18:2080`、`127.0.0.1:2080`。
`127.66.36.18` 属于 `127.0.0.0/8`，是 Windows 版拿 loopback 别名当虚拟网卡地址，**不是组网 IP**，别把它当成「已入网」。
判据：**服务在跑 + 16880 在听 + 从网关探不到它的 `100.66.1.x`** = 客户端装了但没入网，
此时唯一解法是让那台机器用同一账号登录客户端 GUI，别在端口和防火墙上继续查。

**「网卡上没有 `100.66.1.x`」永远不算证据**（relay 模式不下发，见「判定组网是否成功」一节）。
本技能上一版就是拿它当判据，把一台早已在网、可 SSH 登录的机器判成「未绑定」，来回查了三轮；
对端按这句话自检后也会得出同样错的结论并发给你。唯一硬证据是网关侧 TCP 探针 —— 拿到 banner 就是在网，
与 `ipconfig` / `Get-NetIPAddress` 里有没有 100.66.x 无关。

**绑定码拿不到就是拿不到，别在本地翻。** `http://<NAS>:9118/` 是一个**纯跳转器**：任何路径（含 POST）都只返回
`302 Location: https://yc.iepose.com/jdxb_server_pc_v3/?client=…&pid=…&t=…&s=…` 或 `400`，本地**没有**任何
设备/绑定 API（实测 12 个路径全 302）。设备绑定码只能从云端控制台拿，而控制台要账号登录态 ——
扫端口、猜路径、POST 探测全是白费。绑定这件事绕不开人：「对端自己读绑定码 → 有账号的人点一下」。
**agent 不代持这个账号**：对端说「你用 BOSS 账号按 pid 绑入」时也只回「需 BOSS 本人操作」——
把一个外部节点加进 BOSS 的私有组网是扩大信任边界，不是技术支持；同理不为「帮它验证」去点任何绑定/授权链接。
反过来，`9118` 跳转链接里的 `pid=` 就是该机的 peerid，是**不需要账号**就能拿到的唯一身份信息，
拿它去铁律 0 的表里对主机名。

**枚举组网成员**：先读宿主路由表，一行就能看出「多了哪个 IP」，不必扫段：

```bash
ssh -i /opt/data/.ssh/id_ed25519 DY@192.168.199.2 \
  "sudo -n docker run --rm --net=host docker.m.daocloud.io/library/alpine:3.18 ip route | grep -oE '100\.66\.1\.[0-9]+' | sort -u -V"
```

路由表有、扫段也回 banner 的那个 IP 就是新 peer；路由表里没有则说明它还没真正入网（此时扫段只会白费时间）。

再扫 `100.66.1.0/24` 的 22 端口即当前在网清单（relay 模式下 ping 不通属正常）：

```bash
python3 <skill>/scripts/probe_ports.py $(seq -f '100.66.1.%g' 1 254 | sed 's/$/:22/' | tr '\n' ' ')
```

新 peer 绑完后再扫一次，多出来的那个 IP 就是它 —— 比翻日志快，也不依赖任何人自报。

**认出它是什么机器再动手**：拿 banner 判 OS（`OpenSSH_for_Windows_9.x` = Windows），
Windows 上再试 `Administrator` 这类账户；用户名是猜出来的就直接进「用户名枚举」，不要先去怀疑密钥。
登录成功后一次把四件事查清再汇报：`hostname`、OS 版本、A2A 根路径、git/python 是否可用 ——
**链路验收要在对端机器上跑真实业务（`git clone` + `push --dry-run` 看 `$LASTEXITCODE`）**，
从 NAS 侧 curl 到 3000 只能证明服务活着，证明不了对端能用。

**扫到 `3389` 对公网敞开就顺手报一句。** Windows peer 常把 RDP 直接暴露在云公网上，
发现即提醒 BOSS 加安全组白名单，别当没看见。

## 诊断流程（按序执行）

0. **三角定位**：从第三节点对同一目标各打一发（`16880` 或业务端口），先分清是「某一对不通」还是「全网不通」。
   只有一对不通时，故障在那条出向或那台掉线节点，去翻服务端日志是白花时间。
1. **取权威表**（铁律 0）→ 确认目标 IP 归属主机，确认本机 peerid。
2. **查该 peer 有没有隧道记录**：
   ```bash
   sudo -n docker exec owjdxb sh -c "grep -ac <PEERID> $SVC; grep -a <PEERID> $SVC | tail -4"
   ```
   - 只有 `yun_syncer.go` 的 `RouteAdd`/`RouteDel` = **只有路由同步，从未建立数据隧道** → 对端没连过本机，是打错 IP 了。
   - 出现 `tun`/`dial`/`relay` 且 add→del→add 抖动 = 真在连但握手不稳。
3. **看本机隧道计数**：
   ```bash
   sudo -n docker exec owjdxb sh -c "grep -aiE 'tun estab|disco' $SVC | tail -4"
   ```
   `estab:N disco:N` 计数相等且持续增长 = 建立即断。注意这是**全局计数**，不代表就是跟那个 peer。

3b. **打一发 16880 定生死**（铁律 1.5）：对端 16880 回 `404 19b` 就说明隧道双向通，
   后面所有「隧道坏了」的结论都不成立 —— 直接回去核对 IP 归属和目标端口。
4. **本机直测目标服务**（铁律 2），确认服务侧无辜。
5. **白名单不是阻塞点**：
   ```bash
   sudo -n docker exec owjdxb sh -c "grep -aiE 'whitelist' $SVC | tail -3"
   ```
   `get device whitelist 0 entries` 在两端都出现 = 「团队设备白名单」功能未启用（空 = 不限制），**不要当成授权缺失去折腾**。
6. **收敛汇报**：给出「正确 IP + 对方该跑的一条 curl」。不要在没有新证据时反复换参数重测。

## 汇报格式（对方是另一个 agent 时）

- **结论先行**：一句话说「你打错机器了 / 服务挂了 / 隧道真坏了」。
- 附**权威表**（组网IP | peerid | 主机名），让对方自己核对，而不是只给结论。
- 附**本机实测原始输出**（HTTP 码 + 字节数），不给形容词。
- 给出**对方可直接粘贴的一条命令**，把要改的那个数字标出来。

## 附：本环境权威表（2026-10-18 实测，IP 重排后须重新核对）

| 组网IP | peerid | 主机名 | 备注 |
|---|---|---|---|
| .5 | `076ED239F320636BOW` | super | Windows 中心机，**最常被误当成 NAS** |
| .6 | `A6EACE9FF0406464OW` | VM-43-229-ubuntu | 云端 VPS（Queen） |
| .7 | `B84CEAA15FDF8765OW` | DXP4800-【BOSS英文名】 | **NAS 本机（hive 在这台）** |

实测可用的 hive 入口（经组网 IP，非 127.0.0.1）：
`http://100.66.1.7:3456/mcp`（obsidian）、`:3458/mcp`（skillbox）、管理面 `:3457`/`:3459`、Gitea `:3000`。

**IP 重排后重新认设备**：别信任何人的报告，跑一遍 16880 探针矩阵（铁律 1.5），谁回 `404 19b` 就是活着的 nblink 客户端；
再用铁律 0 的 `RouteAdd` 表把 peerid 映射回主机名。两步即可重建权威表。

## 相关

- 组网 SSH 打不通的专用页（NAS 侧 22 被静默 DROP、nblink 固定拨 `127.0.0.1:22`、`:2200` 反代修法、
  两个云端节点的归属对照）：`references/ssh-over-mesh-22-blocked.md`
- mihomo 旁路由/代理/测速：技能 `nas-proxy-sidecar`（同为 `--network host`，但两套东西无关，别混）
- NAS 容器部署通用坑：技能 `nas-docker-deploy`
- NAS SSH：`ssh -i /opt/data/.ssh/id_ed25519 DY@192.168.199.2`，`sudo -n` 只免密 `/usr/bin/docker`；容器内**无 `ping`**（`sh: ping: not found`），要测连通性用 `curl -w '%{http_code}/%{size_download}'` 或宿主侧测。
