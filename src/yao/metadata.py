"""使用 Claude API 從逐字稿產生 podcast 標題 / 說明 / hashtag。

- 使用 Opus 4.6 + adaptive thinking (skill 建議預設)
- system prompt 加上 prompt caching 以降低重複呼叫成本
- 透過 `messages.parse()` + JSON schema 強制結構化輸出,避免解析錯誤
"""

from __future__ import annotations

import json
from typing import Any

import anthropic

SYSTEM_PROMPT = """你是專業的 Podcast 編輯助理,擅長為中文 Podcast 節目產生高品質的發佈素材。

根據使用者提供的逐字稿或重點摘要,產生下列欄位:

1. title (string): 吸引人、具體、能凸顯節目亮點的標題,建議 15~30 字。
2. subtitle (string): 輔助副標,可為空字串。10~25 字。
3. summary (string): 一句話重點摘要,50 字以內。
4. description (string): 節目說明文本,150~300 字。
   - 第一段: 開門見山介紹本集主題與聽眾能得到什麼
   - 第二段: 列出 3~5 個重點 (可用 "・" 或數字條列)
   - 第三段: CTA (訂閱、留言、分享、追蹤社群)
5. hashtags (string array): 8~15 個相關 hashtag。
   - 混合中英文與不同抽象層級 (廣泛主題 + 精準關鍵字)
   - 不含 # 符號
   - 不重複
6. chapters (array of {time, title}): 若能從逐字稿判斷時間戳,則產生章節列表;
   若無明確時間資訊,可回傳空陣列。time 格式為 "MM:SS" 或 "HH:MM:SS"。
7. keywords_en (string array): 3~6 個英文搜尋關鍵字,協助國際搜尋。

內容規範:
- 不要編造逐字稿未提及的事實
- 語氣自然、專業、不浮誇
- 符合 Apple Podcasts / Spotify 的欄位規範
- 若提示為繁體中文,所有中文欄位都以繁體中文書寫
"""


RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "subtitle": {"type": "string"},
        "summary": {"type": "string"},
        "description": {"type": "string"},
        "hashtags": {
            "type": "array",
            "items": {"type": "string"},
        },
        "chapters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "time": {"type": "string"},
                    "title": {"type": "string"},
                },
                "required": ["time", "title"],
                "additionalProperties": False,
            },
        },
        "keywords_en": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "title",
        "subtitle",
        "summary",
        "description",
        "hashtags",
        "chapters",
        "keywords_en",
    ],
    "additionalProperties": False,
}


def generate_metadata(
    transcript: str,
    hints: str = "",
    language: str = "zh-TW",
    model: str = "claude-opus-4-6",
    max_tokens: int = 16000,
) -> dict[str, Any]:
    """呼叫 Claude 產生 podcast 中繼資料。

    Args:
        transcript: 逐字稿或重點摘要純文字。
        hints: 節目主題、風格或目標聽眾提示 (選填)。
        language: 輸出語言,例如 "zh-TW"、"zh-CN"、"en"。
        model: Anthropic model id。
        max_tokens: 最大輸出 token 數。
    """
    client = anthropic.Anthropic()

    user_parts = [f"輸出語言: {language}"]
    if hints:
        user_parts.append(f"節目主題 / 風格提示:\n{hints}")
    user_parts.append(f"逐字稿 / 重點內容:\n{transcript}")
    user_content = "\n\n".join(user_parts)

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_content}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": RESPONSE_SCHEMA,
            }
        },
    )

    # output_config.format 保證第一個 text block 是合法 JSON
    text = next(
        (block.text for block in response.content if block.type == "text"),
        "",
    )
    if not text:
        raise RuntimeError("Claude 回應未包含文字區塊")

    data = json.loads(text)

    # 附帶 usage 資訊,方便檢視 prompt caching 效果
    data["_usage"] = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cache_creation_input_tokens": getattr(
            response.usage, "cache_creation_input_tokens", 0
        ),
        "cache_read_input_tokens": getattr(
            response.usage, "cache_read_input_tokens", 0
        ),
    }
    return data
