"""資料結構：貫穿抓取 → 分析 → 驗證 → 寫入的流程。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Pin:
    """一張從 Pinterest 抓到的圖。"""

    image_url: str          # 高解析圖片直連 (i.pinimg.com/originals/...)
    source_url: str         # pin 頁面網址，寫入「來源出處」
    title: str = ""         # pin 上的標題（若有）


@dataclass
class Analysis:
    """單一視覺模型對一張圖的逆向分析結果。"""

    model: str
    name: str = ""
    prompt: str = ""
    industry: Optional[str] = None       # 產業用途
    category: Optional[str] = None       # 類別
    style_tags: List[str] = field(default_factory=list)  # 風格標籤
    confidence: float = 0.0              # 模型自評信心 0~1
    reasoning: str = ""
    error: str = ""                      # 呼叫失敗時填寫


@dataclass
class Validation:
    """交叉比對後的最終結果。"""

    name: str
    prompt: str
    industry: Optional[str]
    category: Optional[str]
    style_tags: List[str]
    agreement: float            # 兩模型一致性 0~1
    final_confidence: float     # 最終信心分數 0~1
    notes: str = ""


@dataclass
class Record:
    """準備寫入 Notion 的一筆完整資料。"""

    pin: Pin
    claude: Analysis
    gemini: Analysis
    validation: Validation
