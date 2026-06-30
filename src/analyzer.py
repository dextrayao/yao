"""逆向 Prompt 分析：Claude 與 AI 工房各跑一次，再用 Claude 當裁判交叉比對。"""
from __future__ import annotations

import base64
import json
from typing import Optional, Tuple

import requests

from config import (
    ALLOWED_CATEGORY,
    ALLOWED_INDUSTRY,
    ALLOWED_STYLE_TAGS,
    config,
)
from src.models import Analysis, Validation

_TIMEOUT = 30
_ANALYZE_TIMEOUT = 60

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


def _try_json(segment: str) -> Optional[dict]:
    """嘗試從一段文字抽最外層 {..} 並解析；失敗回 None。"""
    start, end = segment.find("{"), segment.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(segment[start : end + 1])
    except json.JSONDecodeError:
        return None


def _parse_json(text: str) -> dict:
    """從模型回應抽出 JSON 物件。

    先直接對整串抽 {..}；失敗才退而逐一嘗試各 ``` 圍欄區塊——
    圍欄處理只能是「額外嘗試」，不能像舊版那樣覆蓋掉原文而丟掉真正的 JSON。
    """
    text = (text or "").strip()
    obj = _try_json(text)
    if obj is not None:
        return obj
    if "```" in text:
        for part in text.split("```")[1:]:
            if part.startswith("json"):
                part = part[4:]
            obj = _try_json(part)
            if obj is not None:
                return obj
    raise ValueError(f"模型未回傳可解析的 JSON：{text[:200]}")


def analyze_with_claude(image: bytes, mime: str) -> Analysis:
    import anthropic

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)
    try:
        resp = client.messages.create(
            model=config.claude_model,
            max_tokens=2048,
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


def _workshop_content(extra: dict, messages: list) -> str:
    """打一次工房請求，穩健取出 message.content（會把伺服器錯誤明確拋出）。"""
    body = {"model": config.workshop_model, "max_tokens": 2048, "messages": messages, **extra}
    resp = requests.post(
        config.workshop_base_url.rstrip("/") + "/chat/completions",
        json=body,
        headers={"Authorization": f"Bearer {config.workshop_api_key}"},
        timeout=_ANALYZE_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"工房回應錯誤：{data['error']}")
    choices = (data or {}).get("choices") or []
    if not choices:
        raise RuntimeError(f"工房未回傳 choices：{str(data)[:200]}")
    msg = choices[0].get("message") or {}
    content = msg.get("content") or msg.get("reasoning_content")
    if not content:
        raise RuntimeError("工房回應 content 為空（可能被 max_tokens 截斷或走了 tool-call 路徑）")
    return content


def analyze_with_workshop(image: bytes, mime: str) -> Analysis:
    """AI 工房：OpenAI 相容 chat/completions（看圖）。

    相容 LM Studio / Ollama / vLLM / llama.cpp server 等本機伺服器。
    先試 response_format json_object；若伺服器回 400（不支援）或回了無法解析的內容，
    才退回純提示重試。其他 HTTP 錯誤（404/500…端點或模型問題）直接拋出真實原因，不掩蓋。
    若你的工房是私有格式，只要改這個函式即可，其餘流程不用動。
    """
    data_uri = f"data:{mime};base64,{base64.b64encode(image).decode()}"
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": _ANALYZE_INSTRUCTION},
                {"type": "image_url", "image_url": {"url": data_uri}},
            ],
        }
    ]
    try:
        try:
            text = _workshop_content({"response_format": {"type": "json_object"}}, messages)
            return _to_analysis("workshop", _parse_json(text))
        except (requests.HTTPError, ValueError) as first:
            # 非-400 的 HTTP 錯誤與 response_format 無關，直接拋出真實原因
            if isinstance(first, requests.HTTPError):
                resp = getattr(first, "response", None)
                if resp is not None and resp.status_code != 400:
                    raise
            text = _workshop_content({}, messages)
            return _to_analysis("workshop", _parse_json(text))
    except requests.exceptions.ConnectionError:
        return Analysis(model="workshop",
                        error="無法連線到 AI 工房，請確認伺服器已啟動且 AI_WORKSHOP_BASE_URL 含 /v1")
    except Exception as exc:  # noqa: BLE001
        return Analysis(model="workshop", error=str(exc))


def cross_validate(image: bytes, mime: str, a: Analysis, b: Analysis) -> Validation:
    """用 Claude 當裁判合成兩份結果，並算最終信心分數。

    裁判呼叫/解析失敗時不讓整張圖作廢——回傳保守結果（信心 0，取信心較高那個
    模型的 prompt），讓 verifier 自然擋在門檻外，與 analyze_* 的降級策略一致。
    """
    import anthropic

    payload = {
        "model_a": {"model": a.model, "prompt": a.prompt, "style_tags": a.style_tags,
                    "industry": a.industry, "category": a.category, "confidence": a.confidence},
        "model_b": {"model": b.model, "prompt": b.prompt, "style_tags": b.style_tags,
                    "industry": b.industry, "category": b.category, "confidence": b.confidence},
    }
    try:
        client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        resp = client.messages.create(
            model=config.claude_model,
            max_tokens=2048,
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
    except Exception as exc:  # noqa: BLE001 — 裁判失敗 → 保守降級，不中斷整批
        best = a if a.confidence >= b.confidence else b
        return Validation(
            name=best.name, prompt=best.prompt, industry=best.industry,
            category=best.category, style_tags=best.style_tags,
            agreement=0.0, final_confidence=0.0, notes=f"裁判失敗：{exc}",
        )

    agreement = _clamp(data.get("agreement", 0.0))
    final_confidence = round(agreement * _mean_conf(a, b), 3)
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
