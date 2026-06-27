"""集中設定：從環境變數讀取，並定義 Notion 既有欄位的允許值。"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


# Notion「圖像分析資料庫」既有 select / multi_select 選項。
# 必須與 Notion 後台一致，模型只能從這些值挑選；不在清單內的標籤會被丟棄。
ALLOWED_INDUSTRY = ["房地產", "節慶"]            # 產業用途 (select)
ALLOWED_CATEGORY = ["社群貼圖"]                  # 類別 (select)
ALLOWED_STYLE_TAGS = [                            # 風格標籤 (multi_select)
    "莫蘭迪綠",
    "漸層背景",
    "顆粒質感",
    "襯線標題",
    "植物線描",
    "幾何疊加",
    "大留白",
]


@dataclass
class Config:
    anthropic_api_key: str = field(default_factory=lambda: _get("ANTHROPIC_API_KEY"))
    claude_model: str = field(default_factory=lambda: _get("CLAUDE_MODEL", "claude-opus-4-8"))

    gemini_api_key: str = field(default_factory=lambda: _get("GEMINI_API_KEY"))
    gemini_model: str = field(default_factory=lambda: _get("GEMINI_MODEL", "gemini-2.5-flash"))

    notion_api_key: str = field(default_factory=lambda: _get("NOTION_API_KEY"))
    notion_database_id: str = field(default_factory=lambda: _get("NOTION_DATABASE_ID"))

    confidence_threshold: float = field(
        default_factory=lambda: float(_get("CONFIDENCE_THRESHOLD", "0.75") or 0.75)
    )

    pinterest_storage_state: str = field(default_factory=lambda: _get("PINTEREST_STORAGE_STATE"))
    max_pins: int = field(default_factory=lambda: int(_get("MAX_PINS", "30") or 30))
    scroll_rounds: int = field(default_factory=lambda: int(_get("SCROLL_ROUNDS", "8") or 8))

    def require(self, *names: str) -> None:
        """確認指定欄位有值，否則丟出明確錯誤。"""
        missing = [n for n in names if not getattr(self, n)]
        if missing:
            raise RuntimeError(
                "缺少必要設定：" + ", ".join(missing) + "。請參考 .env.example 設定環境變數。"
            )


config = Config()
