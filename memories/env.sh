#!/usr/bin/env bash
# 小卡 · HuggingFace 镜像配置（持久）
# 根因：本机 DNS 把 huggingface.co 解析到不可达的 IPv6，必须走国内镜像
export HF_ENDPOINT=https://hf-mirror.com
export HF_HUB_DOWNLOAD_TIMEOUT=120
export HF_HUB_ENABLE_HF_TRANSFER=0
# faster-whisper 缓存位置（避开只读 HOME）
export HF_HOME=/opt/data/.cache/huggingface
export PLAYWRIGHT_BROWSERS_PATH=/opt/data/.playwright-browsers
export PATH=/opt/hermes/bin:/opt/data/.venv-browser/bin:$PATH
