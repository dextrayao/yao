"""探測 AI 工房（OpenAI 相容端點），列出可用模型，協助填好 .env。

在 Mac Studio 上執行（它連得到 Tailscale 位址）：
    python deploy/detect_workshop.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

# 容許未安裝 python-dotenv 也能跑（純標準庫）
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # noqa: BLE001
    pass

BASE = os.environ.get("AI_WORKSHOP_BASE_URL", "http://localhost:11434/v1").rstrip("/")
KEY = os.environ.get("AI_WORKSHOP_API_KEY", "ollama")


def fetch_models() -> list[str]:
    req = urllib.request.Request(
        BASE + "/models", headers={"Authorization": f"Bearer {KEY}"}
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    items = data.get("data", data) if isinstance(data, dict) else data
    return [m.get("id", "") for m in items if isinstance(m, dict)]


def main() -> int:
    print(f"探測 AI 工房：{BASE}/models\n")
    try:
        models = fetch_models()
    except Exception as exc:  # noqa: BLE001
        print(f"❌ 連線失敗：{exc}")
        print("請確認：Mac Studio 上的模型伺服器有開、Tailscale 連線正常、")
        print(f"        且 AI_WORKSHOP_BASE_URL 正確（目前：{BASE}）。")
        return 1

    if not models:
        print("⚠️  連得上，但沒有列出任何模型。請在工房載入一個『看得懂圖』的模型。")
        return 1

    print("✅ 找到以下模型：")
    for m in models:
        print(f"   - {m}")

    # 粗略挑出看起來像 vision/多模態的模型，給個建議
    hint = [m for m in models if any(
        k in m.lower() for k in ("vl", "vision", "llava", "minicpm", "qwen2-vl", "gemma", "pixtral")
    )]
    print()
    if hint:
        print("可能支援看圖的有：", ", ".join(hint))
    print("\n把選定的模型名填到 .env 的 AI_WORKSHOP_MODEL= 即可。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
