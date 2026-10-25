# neonize（WhatsApp 协议）要点

neonize = whatsmeow（Go）的 Python 绑定。pip 装 `neonize segno`；import 依赖 libmagic（无 root 沙箱用 ensure_libmagic.sh 解包 deb + ctypes 预加载）。

## 事件模型（aioze 异步客户端）

```python
from neonize.aioze.client import NewAClient
from neonize.aioze.events import QREv, PairStatusEv, ConnectedEv

client = NewAClient(DB_PATH)          # DB_PATH=sqlite 登录态文件，持久化后重启免扫码
@client.event(QREv)                   # evt.Codes：本轮码（list 或 str，取最后一个用）
@client.event(PairStatusEv)           # 配对进度，配对成功前会先触发
@client.event(ConnectedEv)            # 真正连上（= 登录成功）
await client.connect()                # 之后轮询 state，已登录则不出 QREv 直接复连
```

- 二维码原始内容用 `segno.make(raw, error="M").save(png, scale=10, border=4)` 生成；segno 不可用时把日志里的终端块字符码用 render_terminal_qr.py 转 PNG。
- 官方还有配对码（pair code）方式（whatsmeow 的 PairClientType：Chrome/Edge/Firefox…），手机输数字码，适合无法展示图片的场景。

## 已验证的坑

- 直连 WhatsApp 在大陆网络是**静默挂起**（握手卡死、无异常抛出），必须走 mihomo 代理 192.168.199.2:7891；诊断依据是「进程活着但 20 秒内没有 QREv 也没有任何输出」。
- QREv 每 ~20s 刷新一次码；给用户的码必须来自活进程的当前轮次。
- 无 ffmpeg 只告警：贴纸/语音条/视频/缩略图等媒体操作会失败，文本桥接不受影响。
- 登录态 DB 是普通 sqlite 文件，可整体拷贝迁移；删掉即登出，下次重新扫码。
