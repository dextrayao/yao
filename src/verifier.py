"""驗證：依信心分數門檻決定一筆結果是否夠格寫入 Notion。"""
from __future__ import annotations

from config import config
from src.models import Validation


def passes(validation: Validation, threshold: float | None = None) -> bool:
    """最終信心分數達門檻、且確實有 prompt，才算通過。"""
    threshold = config.confidence_threshold if threshold is None else threshold
    return bool(validation.prompt) and validation.final_confidence >= threshold
