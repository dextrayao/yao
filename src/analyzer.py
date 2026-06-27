"""逆向 Prompt 分析：Claude 與 Gemini 各跑一次，再用 Claude 當裁判交叉比對。"""
from __future__ import annotations

import base64
import json
from typing import Tuple

import requests

from config import (
    ALLOWED_CATEGORY,
    ALLOWED_INDUSTRY,
    ALLOWED_STYLE_TAGS,
    config,
)
from src.models import Analysis, Validation

_TIMEOUT = 30

# 兩個分析模型共用的指令：要求輸出嚴格 JSON，select/tag 只能從允許清單挑。
_ANALYZE_INSTRUCTION = f"""你是 AI 影像逆向工程專家。觀察這張圖，推回最可能生成它的文字 prompt。

請只輸出 JSON（不要任何多餘文字），格式：
{{
  "name": "8 字內的中文短名稱，描述這張圖",
  "prompt": "一段詳盡的英文生成 prompt，涵蓋主體、構圖、配色、光線、材質、風格、鏡頭",
  "industry": 從 {ALLOWED_INDUSTRY} 擇一，不確定填 null,
  "category": 從 {ALLOWED_CATEGORY} 擇一，不確定填 null,
  "style_tags": 從 {ALLOWED_STYLE_TAGS} 挑出符合的（可多選或空陣列），不要自創,
  "confidence": 0~1 的數字，表示你對這份逆向 prompt 正確程度的信心,
  "reasoning": "一句話說明判斷依據"
}}"""

_JUDGE_INSTRUCTION = f"""你是評審。下面是兩個模型對同一張圖逆向出的 prompt 與標籤。
請對照原圖判斷兩者一致性，並合成一份最佳結果。

只輸出 JSON：
{{
  "agreement": 0~1，兩份結果在主體/風格/配色上的一致程度,
  "name": "最終中文短名稱",
  "prompt": "合成後最精準的英文 prompt",
  "industry": 從 {ALLOWED_INDUSTRY} 擇一或 null,
  "category": 從 {ALLOWED_CATEGORY} 擇一或 null,
  "style_tags": 從 {ALLOWED_STYLE_TAGS} 挑出最終標籤,
  "notes": "一句話說明兩模型分歧處（若有）"
}}"""


def download_image(url: str) -> Tuple[bytes, str]:
    """下載圖片，回傳 (bytes, mime)。"""
    resp = requests.get(url, timeout=_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    mime = resp.headers.get("Content-Type", "image/jpeg").split(";")[0]
    if mime not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
        mime = "image/jpeg"
    return resp.content, mime


def _parse_json(text: str) -> dict:
    """從模型回應抽出 JSON 物件（容忍 ```json 圍欄與前後雜訊）。"""
    text = text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"模型未回傳 JSON：{text[:200]}")
    return json.loads(text[start : end + 1])


def analyze_with_claude(image: bytes, mime: str) -> Analysis:
    import anthropic

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)
    try:
        resp = client.messages.create(
            model=config.claude_model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime,
                                "data": base64.b64encode(image).decode(),
                            },
                        },
                        {"type": "text", "text": _ANALYZE_INSTRUCTION},
                    ],
                }
            ],
        )
        data = _parse_json(resp.content[0].text)
        return _to_analysis("claude", data)
    except Exception as exc:  # noqa: BLE001 — 任何失敗都記錄，不中斷整批
        return Analysis(model="claude", error=str(exc))


def analyze_with_gemini(image: bytes, mime: str) -> Analysis:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=config.gemini_api_key)
    try:
        resp = client.models.generate_content(
            model=config.gemini_model,
            contents=[
                types.Part.from_bytes(data=image, mime_type=mime),
                _ANALYZE_INSTRUCTION,
            ],
        )
        data = _parse_json(resp.text)
        return _to_analysis("gemini", data)
    except Exception as exc:  # noqa: BLE001
        return Analysis(model="gemini", error=str(exc))


def cross_validate(image: bytes, mime: str, a: Analysis, b: Analysis) -> Validation:
    """用 Claude 當裁判合成兩份結果，並算最終信心分數。"""
    import anthropic

    payload = {
        "model_a": {"model": a.model, "prompt": a.prompt, "style_tags": a.style_tags,
                    "industry": a.industry, "category": a.category, "confidence": a.confidence},
        "model_b": {"model": b.model, "prompt": b.prompt, "style_tags": b.style_tags,
                    "industry": b.industry, "category": b.category, "confidence": b.confidence},
    }
    client = anthropic.Anthropic(api_key=config.anthropic_api_key)
    resp = client.messages.create(
        model=config.claude_model,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime,
                            "data": base64.b64encode(image).decode(),
                        },
                    },
                    {"type": "text", "text": _JUDGE_INSTRUCTION + "\n\n兩模型結果：\n"
                        + json.dumps(payload, ensure_ascii=False)},
                ],
            }
        ],
    )
    data = _parse_json(resp.content[0].text)

    agreement = _clamp(data.get("agreement", 0.0))
    self_conf = _mean_conf(a, b)
    final_confidence = round(agreement * self_conf, 3)

    return Validation(
        name=str(data.get("name", "")).strip(),
        prompt=str(data.get("prompt", "")).strip(),
        industry=_pick(data.get("industry"), ALLOWED_INDUSTRY),
        category=_pick(data.get("category"), ALLOWED_CATEGORY),
        style_tags=_filter_tags(data.get("style_tags", []), ALLOWED_STYLE_TAGS),
        agreement=agreement,
        final_confidence=final_confidence,
        notes=str(data.get("notes", "")).strip(),
    )


# ---- 純函式輔助（可單元測試） ----

def _clamp(value, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        return max(lo, min(hi, float(value)))
    except (TypeError, ValueError):
        return lo


def _mean_conf(a: Analysis, b: Analysis) -> float:
    confs = [x.confidence for x in (a, b) if not x.error]
    return sum(confs) / len(confs) if confs else 0.0


def _pick(value, allowed: list[str]):
    return value if value in allowed else None


def _filter_tags(tags, allowed: list[str]) -> list[str]:
    if not isinstance(tags, list):
        return []
    return [t for t in tags if t in allowed]


def _to_analysis(model: str, data: dict) -> Analysis:
    return Analysis(
        model=model,
        name=str(data.get("name", "")).strip(),
        prompt=str(data.get("prompt", "")).strip(),
        industry=_pick(data.get("industry"), ALLOWED_INDUSTRY),
        category=_pick(data.get("category"), ALLOWED_CATEGORY),
        style_tags=_filter_tags(data.get("style_tags", []), ALLOWED_STYLE_TAGS),
        confidence=_clamp(data.get("confidence", 0.0)),
        reasoning=str(data.get("reasoning", "")).strip(),
    )
