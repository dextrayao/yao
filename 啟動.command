#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  圖像逆向分析器 — 點兩下就啟動（Mac 專用）
#  第一次執行會自動安裝，之後每次點兩下就開網頁介面。
# ═══════════════════════════════════════════════════════════
cd "$(dirname "$0")"

echo "════════════════════════════════════════"
echo "  圖像逆向分析器 啟動中…"
echo "════════════════════════════════════════"

# 第一次執行：建立環境並安裝
if [ ! -d venv ]; then
  echo "🔧 第一次啟動，正在安裝（約 3~5 分鐘，只有這次要等）…"
  python3 -m venv venv || { echo "❌ 找不到 python3，請先安裝 Python（https://www.python.org/downloads/）"; read -r; exit 1; }
  # shellcheck disable=SC1091
  source venv/bin/activate
  pip install --upgrade pip >/dev/null
  pip install -r requirements.txt || { echo "❌ 套件安裝失敗"; read -r; exit 1; }
  python -m playwright install chromium
else
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

# 準備設定檔
if [ ! -f .env ]; then
  cp .env.example .env
  echo "📝 已建立 .env 設定檔（要寫入 Notion 才需填金鑰；只想試看看可先不填）"
fi

# 提醒看圖模型
if command -v ollama >/dev/null; then
  ollama list 2>/dev/null | grep -qi "vl\|vision\|llava\|minicpm" || \
    echo "⚠️  Ollama 裡似乎還沒有看圖模型，建議先跑：ollama pull qwen2.5vl:7b"
fi

echo "🚀 開啟網頁介面… 瀏覽器會自動打開 http://localhost:8501"
echo "   （要關閉：回到這個視窗按 Control + C）"
streamlit run app.py
