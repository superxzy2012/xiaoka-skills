#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A股实盘播报 · 小卡
数据源：腾讯行情 qt.gtimg.cn（GBK）
输出：飞书播报文本 + Obsidian 笔记
"""
import sys, json, urllib.request, datetime, io, re

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

INDEX = [
    ("sh000001", "上证指数"),
    ("sz399001", "深证成指"),
    ("sz399006", "创业板指"),
    ("sh000688", "科创50"),
    ("sh000300", "沪深300"),
    ("sh000905", "中证500"),
    ("sh000016", "上证50"),
    ("sz399303", "国证2000"),
]

def fetch(codes):
    url = "https://qt.gtimg.cn/q=" + ",".join(c for c, _ in codes)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read().decode("gbk", errors="replace")
    out = {}
    for line in raw.strip().split("\n"):
        m = re.match(r'v_([a-z0-9]+)="(.*)";', line.strip())
        if not m:
            continue
        code, payload = m.group(1), m.group(2)
        f = payload.split("~")
        if len(f) < 45:
            continue
        out[code] = {
            "name": f[1],
            "code": f[2],
            "price": float(f[3]),
            "prev_close": float(f[4]),
            "open": float(f[5]),
            "volume": float(f[6]),
            "time": f[30],
            "change": float(f[31]),
            "pct": float(f[32]),
            "high": float(f[33]),
            "low": float(f[34]),
            # f[37] 是成交额，单位万元 → 换算成亿
            "amount": float(f[37]) / 1e4 if f[37] else 0.0,
        }
    return out

def minute_trend(code):
    """分时数据，可选"""
    try:
        url = f"https://web.ifzq.gtimg.cn/appstock/app/minute/query?code={code}"
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read().decode("utf-8", errors="replace"))
        pts = d["data"][code]["data"]["data"]
        vals = [float(p.split()[1]) for p in pts]
        return vals
    except Exception:
        return []

def main():
    codes = INDEX
    extra = sys.argv[1:] if len(sys.argv) > 1 else []
    for c in extra:
        codes = codes + [(c, c)]
    d = fetch(codes)
    now = datetime.datetime.now()
    if not d:
        print("❌ 行情获取失败", file=sys.stderr)
        return 1

    # 市场状态判断
    hm = now.hour * 60 + now.minute
    if now.weekday() >= 5:
        status = "休市（周末）"
    elif hm < 9 * 60 + 15:
        status = "盘前"
    elif hm <= 11 * 60 + 30:
        status = "早盘交易中"
    elif hm < 13 * 60:
        status = "午间休市"
    elif hm <= 15 * 60:
        status = "午盘交易中"
    else:
        status = "已收盘"

    lines = []
    lines.append(f"# 📈 A股实盘播报 {now.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"\n> 状态：{status}　数据源：腾讯行情")
    lines.append("")
    lines.append("| 指数 | 现价 | 涨跌 | 涨跌幅 | 最高 | 最低 | 成交额(亿) |")
    lines.append("|---|---|---|---|---|---|---|")
    for c, label in codes:
        v = d.get(c)
        if not v:
            lines.append(f"| {label} | - | - | - | - | - | - |")
            continue
        emoji = "🔴" if v["pct"] > 0 else ("🟢" if v["pct"] < 0 else "⚪")
        lines.append(
            f"| {emoji} {v['name']} | {v['price']:.2f} | {v['change']:+.2f} | "
            f"{v['pct']:+.2f}% | {v['high']:.2f} | {v['low']:.2f} | {v['amount']:.1f} |"
        )

    # 自定义代码的价格
    if extra:
        lines.append("")
        lines.append("## 你的自选")
        for c in extra:
            v = d.get(c)
            if v:
                lines.append(f"- **{v['name']}** ({v['code']}) {v['price']:.2f}　{v['pct']:+.2f}%")

    # 上证分时走势
    trend = minute_trend("sh000001")
    if trend:
        lo, hi = min(trend), max(trend)
        cur = trend[-1]
        lines.append("")
        lines.append("## 上证分时")
        lines.append(f"- 区间：{lo:.2f} ~ {hi:.2f}　振幅 {hi-lo:.2f}（{((hi-lo)/lo*100):.2f}%）")
        spark = "".join("▁▂▃▄▅▆▇█"[min(7, int((x-lo)/(hi-lo+1e-9)*7.99))] for x in trend)
        lines.append(f"- `{spark}`")
        lines.append(f"- 收盘位置：{(cur-lo)/(hi-lo+1e-9)*100:.1f}%（0=最低 100=最高）")

    lines.append("")
    lines.append(f"⏰ 下一交易日：{_next_trading_day(now)}")
    return "\n".join(lines)

def _next_trading_day(now):
    d = now + datetime.timedelta(days=1)
    while d.weekday() >= 5:
        d += datetime.timedelta(days=1)
    return d.strftime("%Y-%m-%d %A")

if __name__ == "__main__":
    print(main())
