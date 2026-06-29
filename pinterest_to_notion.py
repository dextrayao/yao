#!/usr/bin/env python3
"""Pinterest 圖像逆向 Prompt 分析器 —— 單檔可移植版本。

把這一個檔案丟到 AI 工房（Mac Studio）任意位置即可使用，不依賴專案目錄結構。

功能：
  抓 Pinterest 看板/使用者頁面的圖 → Claude + AI 工房雙模型逆向推回 prompt
  → Claude 裁判交叉比對算信心分數 → 過門檻者寫入 Notion「圖像分析資料庫」。

相依套件：
  pip install playwright anthropic requests notion-client python-dotenv
  python -m playwright install chromium

環境變數（可放 .env）：
  ANTHROPIC_API_KEY        Claude 金鑰
  CLAUDE_MODEL             預設 claude-opus-4-8
  AI_WORKSHOP_BASE_URL     工房 OpenAI 相容端點，結尾含 /v1
                           例：https://macmac-studio.tailbfceaf.ts.net/v1
  AI_WORKSHOP_API_KEY      工房金鑰（本機伺服器多半隨意填，預設 local）
  AI_WORKSHOP_MODEL        工房裡「看得懂圖」的模型名（必填）
  NOTION_API_KEY           Notion integration token
  NOTION_DATABASE_ID       資料來源 id，預設 e771e46f-f611-405c-8651-432aae03ba11
  CONFIDENCE_THRESHOLD     最終信心門檻，預設 0.75
  PINTEREST_STORAGE_STATE  Playwright 登入 storage_state JSON 路徑（私人看板用，選填）
  MAX_PINS / SCROLL_ROUNDS 每來源最多抓幾張 / 捲動次數

用法：
  python pinterest_to_notion.py https://www.pinterest.com/dextrayao/ --dry-run
  python pinterest_to_notion.py dextrayao/某看板 --max-pins 20 --threshold 0.8
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # noqa: BLE001 — 沒裝 dotenv 也能跑（直接用環境變數）
    pass


# ════════════════════════════ 設定 ════════════════════════════

# Notion「圖像分析資料庫」既有 select / multi_select 選項。
# 必須與 Notion 後台一致；模型只能從這些值挑，不在清單內者一律丟棄。
ALLOWED_INDUSTRY = ["房地產", "節慶"]
ALLOWED_CATEGORY = ["社群貼圖"]
ALLOWED_STYLE_TAGS = [
    "莫蘭迪綠", "漸層背景", "顆粒質感", "襯線標題", "植物線描", "幾何疊加", "大留白",
]


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass
class Config:
    anthropic_api_key: str = field(default_factory=lambda: _env("ANTHROPIC_API_KEY"))
    claude_model: str = field(default_factory=lambda: _env("CLAUDE_MODEL", "claude-opus-4-8"))

    workshop_api_key: str = field(default_factory=lambda: _env("AI_WORKSHOP_API_KEY", "local"))
    workshop_base_url: str = field(default_factory=lambda: _env("AI_WORKSHOP_BASE_URL"))
    workshop_model: str = field(default_factory=lambda: _env("AI_WORKSHOP_MODEL"))

    notion_api_key: str = field(default_factory=lambda: _env("NOTION_API_KEY"))
    notion_database_id: str = field(
        default_factory=lambda: _env("NOTION_DATABASE_ID", "e771e46f-f611-405c-8651-432aae03ba11")
    )

    confidence_threshold: float = field(
        default_factory=lambda: float(_env("CONFIDENCE_THRESHOLD", "0.75") or 0.75)
    )

    pinterest_storage_state: str = field(default_factory=lambda: _env("PINTEREST_STORAGE_STATE"))
    max_pins: int = field(default_factory=lambda: int(_env("MAX_PINS", "30") or 30))
    scroll_rounds: int = field(default_factory=lambda: int(_env("SCROLL_ROUNDS", "8") or 8))

    def require(self, *names: str) -> None:
        missing = [n for n in names if not getattr(self, n)]
        if missing:
            raise RuntimeError("缺少必要設定：" + ", ".join(missing))


config = Config()


# ════════════════════════════ 資料結構 ════════════════════════════

@dataclass
class Pin:
    image_url: str
    source_url: str
    title: str = ""


@dataclass
class Analysis:
    model: str
    name: str = ""
    prompt: str = ""
    industry: Optional[str] = None
    category: Optional[str] = None
    style_tags: List[str] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""
    error: str = ""


@dataclass
class Validation:
    name: str
    prompt: str
    industry: Optional[str]
    category: Optional[str]
    style_tags: List[str]
    agreement: float
    final_confidence: float
    notes: str = ""


@dataclass
class Record:
    pin: Pin
    claude: Analysis
    workshop: Analysis
    validation: Validation


# ════════════════════════════ 抓取 (Playwright) ════════════════════════════

_SIZE_DIR = re.compile(r"/(\d+x\d*|\d+x)/")


def upscale_image_url(url: str) -> str:
    """把縮圖網址 (/236x/、/564x/) 轉成原圖 (/originals/)。"""
    return _SIZE_DIR.sub("/originals/", url, count=1)


def normalize_user_url(url: str) -> str:
    url = url.strip()
    if not url.startswith("http"):
        url = "https://www.pinterest.com/" + url.lstrip("/")
    if not url.endswith("/"):
        url += "/"
    return url


def scrape(url: str, max_pins: int | None = None, scroll_rounds: int | None = None) -> List[Pin]:
    """抓取單一看板／使用者頁面，回傳去重後的 Pin 清單。"""
    max_pins = max_pins or config.max_pins
    scroll_rounds = scroll_rounds or config.scroll_rounds
    url = normalize_user_url(url)

    from playwright.sync_api import sync_playwright

    seen: dict[str, Pin] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context_kwargs = {
            "viewport": {"width": 1280, "height": 1600},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
        }
        if config.pinterest_storage_state:
            context_kwargs["storage_state"] = config.pinterest_storage_state

        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(3_000)

        for _ in range(scroll_rounds):
            for pin in _extract_pins(page):
                if pin.image_url not in seen:
                    seen[pin.image_url] = pin
            if len(seen) >= max_pins:
                break
            page.mouse.wheel(0, 4_000)
            page.wait_for_timeout(2_000)

        context.close()
        browser.close()

    return list(seen.values())[:max_pins]


def _extract_pins(page) -> List[Pin]:
    raw = page.eval_on_selector_all(
        "div[data-test-id='pin'], div[data-test-id='pinWrapper']",
        """nodes => nodes.map(n => {
            const img = n.querySelector('img');
            const a = n.querySelector("a[href*='/pin/']");
            return img ? { src: img.src, alt: img.alt || '', href: a ? a.href : '' } : null;
        }).filter(Boolean)""",
    )
    if not raw:  # 後備：Pinterest 改版時退而求其次掃 pin 連結
        raw = page.eval_on_selector_all(
            "a[href*='/pin/'] img",
            """imgs => imgs.map(img => ({
                src: img.src, alt: img.alt || '',
                href: img.closest("a[href*='/pin/']")?.href || ''
            }))""",
        )

    pins: List[Pin] = []
    for item in raw:
        src = item.get("src", "")
        if not src or "i.pinimg.com" not in src:
            continue
        pins.append(Pin(
            image_url=upscale_image_url(src),
            source_url=item.get("href", "") or page.url,
            title=item.get("alt", ""),
        ))
    return pins


# ════════════════════════════ 逆向分析 ════════════════════════════

_DL_TIMEOUT = 30
_ANALYZE_TIMEOUT = 60

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
    resp = requests.get(url, timeout=_DL_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    mime = resp.headers.get("Content-Type", "image/jpeg").split(";")[0]
    if mime not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
        mime = "image/jpeg"
    return resp.content, mime


def _parse_json(text: str) -> dict:
    """從模型回應抽出 JSON 物件（容忍 ```json 圍欄與前後雜訊）。"""
    text = (text or "").strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"模型未回傳 JSON：{text[:200]}")
    return json.loads(text[start:end + 1])


def analyze_with_claude(image: bytes, mime: str) -> Analysis:
    import anthropic

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)
    try:
        resp = client.messages.create(
            model=config.claude_model,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type": "base64", "media_type": mime,
                        "data": base64.b64encode(image).decode()}},
                    {"type": "text", "text": _ANALYZE_INSTRUCTION},
                ],
            }],
        )
        return _to_analysis("claude", _parse_json(resp.content[0].text))
    except Exception as exc:  # noqa: BLE001
        return Analysis(model="claude", error=str(exc))


def analyze_with_workshop(image: bytes, mime: str) -> Analysis:
    """AI 工房：OpenAI 相容 chat/completions（看圖）。

    相容 LM Studio / Ollama / vLLM / llama.cpp server 等本機伺服器。
    若你的工房是私有格式，只要改這個函式的請求組裝與回應解析即可，
    其餘流程（裁判、驗證、寫入）完全不用動。
    """
    data_uri = f"data:{mime};base64,{base64.b64encode(image).decode()}"
    base = config.workshop_base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {config.workshop_api_key}"}
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": _ANALYZE_INSTRUCTION},
            {"type": "image_url", "image_url": {"url": data_uri}},
        ],
    }]

    def _call(extra: dict) -> str:
        body = {"model": config.workshop_model, "max_tokens": 1024, "messages": messages, **extra}
        resp = requests.post(base, json=body, headers=headers, timeout=_ANALYZE_TIMEOUT)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    try:
        # 先試 JSON 模式（多數本機伺服器支援）；被拒就退回純提示。
        try:
            text = _call({"response_format": {"type": "json_object"}})
        except requests.HTTPError:
            text = _call({})
        return _to_analysis("workshop", _parse_json(text))
    except Exception as exc:  # noqa: BLE001
        return Analysis(model="workshop", error=str(exc))


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
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64", "media_type": mime,
                    "data": base64.b64encode(image).decode()}},
                {"type": "text", "text": _JUDGE_INSTRUCTION + "\n\n兩模型結果：\n"
                    + json.dumps(payload, ensure_ascii=False)},
            ],
        }],
    )
    data = _parse_json(resp.content[0].text)

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


def _clamp(value, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        return max(lo, min(hi, float(value)))
    except (TypeError, ValueError):
        return lo


def _mean_conf(a: Analysis, b: Analysis) -> float:
    confs = [x.confidence for x in (a, b) if not x.error]
    return sum(confs) / len(confs) if confs else 0.0


def _pick(value, allowed: List[str]):
    return value if value in allowed else None


def _filter_tags(tags, allowed: List[str]) -> List[str]:
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


# ════════════════════════════ 驗證 ════════════════════════════

def passes(validation: Validation, threshold: float | None = None) -> bool:
    threshold = config.confidence_threshold if threshold is None else threshold
    return bool(validation.prompt) and validation.final_confidence >= threshold


# ════════════════════════════ 寫入 Notion ════════════════════════════

def build_properties(record: Record) -> dict:
    """把一筆 Record 轉成 Notion 屬性 payload。"""
    v = record.validation
    name = v.name or record.pin.title or "未命名圖像"
    note = (f"信心分數 {v.final_confidence}（一致性 {v.agreement}）｜"
            f"Claude conf {record.claude.confidence}, 工房 conf {record.workshop.confidence}")
    if v.notes:
        note += f"｜{v.notes}"

    props: dict = {
        "名稱": {"title": [{"text": {"content": name[:200]}}]},
        "逆向 Prompt": {"rich_text": [{"text": {"content": v.prompt[:2000]}}]},
        "來源出處": {"rich_text": [{"text": {"content": record.pin.source_url}}]},
        "備註": {"rich_text": [{"text": {"content": note[:2000]}}]},
        "風格標籤": {"multi_select": [{"name": t} for t in v.style_tags]},
    }
    if record.pin.image_url:
        props["原圖"] = {"files": [{"type": "external", "name": (name[:100] or "image"),
                                     "external": {"url": record.pin.image_url}}]}
    if v.industry:
        props["產業用途"] = {"select": {"name": v.industry}}
    if v.category:
        props["類別"] = {"select": {"name": v.category}}
    return props


class NotionWriter:
    def __init__(self, api_key: Optional[str] = None, database_id: Optional[str] = None):
        from notion_client import Client

        self.client = Client(auth=api_key or config.notion_api_key)
        self.database_id = database_id or config.notion_database_id

    def exists(self, source_url: str) -> bool:
        resp = self.client.databases.query(
            database_id=self.database_id,
            filter={"property": "來源出處", "rich_text": {"equals": source_url}},
            page_size=1,
        )
        return len(resp.get("results", [])) > 0

    def create(self, record: Record) -> dict:
        return self.client.pages.create(
            parent={"database_id": self.database_id},
            properties=build_properties(record),
        )


# ════════════════════════════ 流程編排 / CLI ════════════════════════════

def process_pin(pin: Pin) -> Record:
    image, mime = download_image(pin.image_url)
    claude = analyze_with_claude(image, mime)
    workshop = analyze_with_workshop(image, mime)
    validation = cross_validate(image, mime, claude, workshop)
    return Record(pin=pin, claude=claude, workshop=workshop, validation=validation)


def run(urls: List[str], dry_run: bool, threshold: float, max_pins: int | None) -> int:
    config.require("anthropic_api_key", "workshop_base_url", "workshop_model")
    writer = None
    if not dry_run:
        config.require("notion_api_key", "notion_database_id")
        writer = NotionWriter()

    saved = skipped = failed = 0
    for url in urls:
        print(f"\n=== 抓取 {url} ===")
        pins = scrape(url, max_pins=max_pins)
        print(f"找到 {len(pins)} 張圖")

        for i, pin in enumerate(pins, 1):
            try:
                record = process_pin(pin)
            except Exception as exc:  # noqa: BLE001
                failed += 1
                print(f"  [{i}] 分析失敗：{exc}")
                continue

            v = record.validation
            ok = passes(v, threshold)
            print(f"  [{i}] {'✅' if ok else '✋'} {v.name or pin.title!r} "
                  f"信心={v.final_confidence} (一致性={v.agreement}) tags={v.style_tags}")
            if not ok:
                skipped += 1
                continue
            if dry_run:
                print(f"      [dry-run] {v.prompt[:120]}...")
                saved += 1
                continue
            if writer.exists(pin.source_url):
                print("      已存在，略過")
                skipped += 1
                continue
            writer.create(record)
            saved += 1
            print("      已寫入 Notion")

    print(f"\n完成：寫入 {saved}、略過 {skipped}、失敗 {failed}"
          + ("（dry-run 未實際寫入）" if dry_run else ""))
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pinterest 圖像逆向 Prompt 分析 → Notion")
    parser.add_argument("urls", nargs="+", help="Pinterest 看板或使用者 URL（可多個）")
    parser.add_argument("--dry-run", action="store_true", help="只分析印出，不寫入 Notion")
    parser.add_argument("--threshold", type=float, default=config.confidence_threshold)
    parser.add_argument("--max-pins", type=int, default=None)
    args = parser.parse_args(argv)
    return run(args.urls, args.dry_run, args.threshold, args.max_pins)


if __name__ == "__main__":
    sys.exit(main())
