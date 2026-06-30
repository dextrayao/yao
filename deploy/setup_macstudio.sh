#!/usr/bin/env bash
# Mac Studio 一鍵安裝：建立 venv、裝套件、裝瀏覽器、備好 .env、探測 AI 工房。
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> 1/5 檢查 Python"
command -v python3 >/dev/null || { echo "找不到 python3，請先安裝（brew install python）"; exit 1; }

echo "==> 2/5 建立虛擬環境並安裝套件"
python3 -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "==> 3/5 安裝 Playwright Chromium"
python -m playwright install chromium

echo "==> 4/5 準備 .env"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "已建立 .env，請填入 ANTHROPIC_API_KEY / NOTION_API_KEY 等金鑰。"
else
  echo ".env 已存在，沿用。"
fi

echo "==> 5/6 下載看圖模型到 Ollama（若已存在會略過）"
if command -v ollama >/dev/null; then
  ollama pull qwen2.5vl:7b || echo "（pull 失敗，可稍後手動執行 ollama pull qwen2.5vl:7b）"
else
  echo "（找不到 ollama 指令，請確認 Ollama 已安裝並啟動）"
fi

echo "==> 6/6 探測 AI 工房模型"
python deploy/detect_workshop.py || true

echo
echo "完成。接著："
echo "  1) 編輯 .env 填好金鑰與 AI_WORKSHOP_MODEL"
echo "  2) 啟動介面：bash deploy/run.sh"
