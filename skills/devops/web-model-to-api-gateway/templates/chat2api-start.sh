#!/bin/bash
# Chat2API (Electron) in a headless container: Xvfb + noVNC + CDP bridge.
# 关键：不要 exec AppRun（flag 当 $1 时 APPDIR 会解析成 /），直接跑解包后的二进制。
export DISPLAY=:99
export ELECTRON_DISABLE_SANDBOX=1

Xvfb :99 -screen 0 1440x900x24 -nolisten tcp >/tmp/xvfb.log 2>&1 &
sleep 2
x11vnc -display :99 -forever -shared -nopw -rfbport 5900 -quiet >/tmp/x11vnc.log 2>&1 &
websockify --web=/usr/share/novnc 6080 127.0.0.1:5900 >/tmp/novnc.log 2>&1 &
# Electron DevTools 只绑 127.0.0.1，用 socat 桥到 0.0.0.0 才能从外部 CDP 接管
socat TCP-LISTEN:9223,fork,reuseaddr TCP:127.0.0.1:9222 >/tmp/socat.log 2>&1 &
sleep 1

echo "=== chat2api 启动 ==="
export APPDIR=/app/electron
exec /app/electron/chat2api \
  --no-sandbox --disable-gpu --disable-dev-shm-usage \
  --remote-debugging-port=9222
