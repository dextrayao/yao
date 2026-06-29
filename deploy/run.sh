#!/usr/bin/env bash
# 啟動網頁介面（Streamlit）。預設只在本機開，加 --lan 則對 Tailscale/區網開放。
set -euo pipefail
cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
source venv/bin/activate

ADDR="localhost"
if [ "${1:-}" = "--lan" ]; then
  ADDR="0.0.0.0"   # 同網路/Tailscale 內其他裝置可連 http://<mac-studio>:8501
fi

exec streamlit run app.py \
  --server.address "$ADDR" \
  --server.port 8501 \
  --browser.gatherUsageStats false
