#!/usr/bin/env bash
# 小豆云端 VPS 自检（只读，不改任何配置）。用法: bash xiaodou_vps_probe.sh
echo "===== 1. 机器 ====="
echo "host: $(hostname) | user: $(id -un) | $(uname -srm)"
[ -r /etc/os-release ] && . /etc/os-release && echo "os: $PRETTY_NAME"

echo "===== 2. 公网 IP ====="
for u in https://api.ipify.org https://ifconfig.me/ip https://ipinfo.io/ip; do
  ip=$(curl -s --max-time 6 "$u" 2>/dev/null | tr -d '\r\n')
  case "$ip" in
    [0-9]*.[0-9]*.[0-9]*.[0-9]*) echo "public: $ip  (via $u)"; break;;
  esac
done
[ -z "$ip" ] && echo "public: 取不到（出网被限）"
echo "lan: $(ip -4 route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}')"

echo "===== 3. sshd ====="
echo "service: $(systemctl is-active ssh 2>/dev/null || systemctl is-active sshd 2>/dev/null)"
echo "listen:"; (ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null) | grep -E ':22\b' || echo "  !! 没有 22 端口在监听"
for k in Port PermitRootLogin PasswordAuthentication PubkeyAuthentication; do
  v=$(grep -hiE "^\s*$k\s+" /etc/ssh/sshd_config /etc/ssh/sshd_config.d/*.conf 2>/dev/null | tail -1)
  [ -n "$v" ] && echo "cfg: $v"
done

echo "===== 4. 节点小宝 ====="
ps -eo pid,cmd 2>/dev/null | grep -iE "nodebaby|nblink|owjdxb" | grep -v grep | head -3 || echo "  未发现小宝进程"
command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}|{{.Image}}' 2>/dev/null | grep -iE "nblink|owjdxb|nodebaby" || true
echo "组网 IP:"; ip -4 addr 2>/dev/null | grep -E 'inet 100\.66\.' || echo "  !! 没有 100.66.x 地址（小宝没连上或没建 tun）"
[ -c /dev/net/tun ] && echo "tun: /dev/net/tun 存在" || echo "tun: !! 缺 /dev/net/tun"

echo "===== 5. 小卡公钥 ====="
grep -q "xiaoka@nas" ~/.ssh/authorized_keys 2>/dev/null && echo "authorized_keys: 已含 xiaoka@nas" || echo "authorized_keys: !! 未含 xiaoka@nas"
ls -ld ~/.ssh ~/.ssh/authorized_keys 2>/dev/null

echo "===== 6. A2A 根 ====="
for d in ~/A2A /opt/A2A /srv/A2A; do [ -d "$d" ] && echo "found: $d ($(ls "$d" | tr '\n' ' '))"; done
echo "git: $(git --version 2>/dev/null || echo 未安装)"
echo "===== 完，把上面整段贴回群里 ====="
