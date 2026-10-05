# mihomo deployment reference

Known-good skeleton for a NAS-hosted gateway on host network mode. Adjust the control secret and
the provider path; nothing else is load-bearing.

## Topology

```
NAS host network
  |- :7891  mixed HTTP+SOCKS5   <- the only address clients need
  |- :1053  DNS (fake-ip)       <- optional, anti-pollution
  `- :9090  RESTful API + WebUI  <- bearer-secret protected
```

`--network host` is required for the ports to be reachable from the LAN. A bridge-network
container is only reachable from its own docker network.

## config.yaml

```yaml
mixed-port: 7891
allow-lan: true
bind-address: '*'
mode: rule
log-level: info
ipv6: false
unified-delay: true
tcp-concurrent: true
external-controller: '0.0.0.0:9090'
secret: '<RANDOM-BEARER>'

dns:
  enable: true
  listen: 0.0.0.0:1053
  enhanced-mode: fake-ip
  fake-ip-range: 198.18.0.1/16
  fake-ip-filter: ['*.lan', '*.local', 'localhost', '+.msftconnecttest.com']
  nameserver: [223.5.5.5, 119.29.29.29]
  proxy-server-nameserver: [223.5.5.5, 119.29.29.29]

proxy-providers:
  provider:
    type: file
    path: ./provider.yaml
    health-check:
      enable: true
      url: http://www.gstatic.com/generate_204
      interval: 300

proxy-groups:
  - name: MAIN            # 代理选择
    type: select
    use: [provider]
    proxies: [AUTO, DIRECT]
  - name: AUTO            # 自动选择
    type: url-test
    use: [provider]
    url: http://www.gstatic.com/generate_204
    tolerance: 100
    interval: 300

rule-providers:            # GeoSite/GeoIP CN for domestic-direct split routing
  cn-domain: { type: http, behavior: domain, format: mrs, path: ./ruleset/cn-domain.mrs, interval: 86400, url: <MRS-URL> }
  cn-ip:     { type: http, behavior: ipcidr, format: mrs, path: ./ruleset/cn-ip.mrs,     interval: 86400, url: <MRS-URL> }

rules:
  - GEOIP,private,DIRECT,no-resolve
  - GEOSITE,cn,DIRECT
  - GEOIP,CN,DIRECT,no-resolve
  - MATCH,MAIN
```

Group names may be CJK; percent-encode them when they appear in REST paths.

## Commands

```bash
# validate (quote the binary's own verdict)
sudo -n docker run --rm -v "$D:/root/.config/mihomo" metacubex/mihomo:latest \
  -t -d /root/.config/mihomo

sudo -n docker run -d --name mihomo --restart unless-stopped --network host \
  -v "$D:/root/.config/mihomo" metacubex/mihomo:latest

# refresh subscription (client UA required), then restart
curl -s -A "clash-verge/v1.6.0" -o "$D/provider.yaml" "$SUB_URL"
chmod 600 "$D/provider.yaml"; sudo -n docker restart mihomo
```

## API for health

```bash
S='<RANDOM-BEARER>'; API=http://127.0.0.1:9090
curl -s "$API/proxies" -H "Authorization: Bearer $S" | jq '.proxies.MAIN.now'
curl -s -X PUT "$API/proxies/<ENC-MAIN>" -H "Authorization: Bearer $S" \
  -H 'Content-Type: application/json' -d '{"name":"<node>"}'
curl -s "$API/proxies/<ENC-GROUP>/delay?url=http%3A%2F%2Fwww.gstatic.com%2Fgenerate_204&timeout=8000" \
  -H "Authorization: Bearer $S"        # -> {"delay":<ms>}
```

Per-node delays are readable from `.proxies.<node>.history[-1].delay` after a health check runs —
cheaper and encoding-free compared to one request per node name.

## Bandwidth probe

```bash
U=https://<reachable>/<size>.bin
for n in 1 4 8 16; do
  s=$(date +%s%N)
  for i in $(seq 1 $n); do curl -s -m 20 -o /dev/null "$U" & done
  wait
  e=$(date +%s%N); ms=$(( (e - s) / 1000000 ))
  awk -v n="$n" -v ms="$ms" 'BEGIN{printf "%2d streams: %6.1f Mbps\n", n, n*100*8*1000/ms}'
done
cat /sys/class/net/<if>/speed    # link ceiling, for comparison
```

Run the same loop with `-x http://127.0.0.1:7891` for the proxied figure, against the same URL.

## Troubleshooting table to ship with the config

| Symptom | Cause | Fix |
|---|---|---|
| port refuses connection | container stopped | `docker ps --filter name=mihomo` |
| connects, zero throughput | subscription expired / all nodes dead | re-pull provider, check node delays |
| some sites fail | DNS | point resolver at `:1053` |
| domestic sites got slow | split-routing rule lost | confirm `GEOSITE,cn,DIRECT` present |
| speed test returns 0 B/s | test source blocked or transport mismatch | probe with a small range request first |