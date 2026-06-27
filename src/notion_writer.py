"""寫入 Notion「圖像分析資料庫」，並依「來源出處」去重。"""
from __future__ import annotations

from typing import Optional

from notion_client import Client

from config import config
from src.models import Record


def build_properties(record: Record) -> dict:
    """把一筆 Record 轉成 Notion 屬性 payload（純函式，可單元測試）。"""
    v = record.validation
    name = v.name or record.pin.title or "未命名圖像"

    note = (
        f"信心分數 {v.final_confidence}（一致性 {v.agreement}）｜"
        f"Claude conf {record.claude.confidence}, Gemini conf {record.gemini.confidence}"
    )
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
        props["原圖"] = {
            "files": [
                {"type": "external", "name": name[:100] or "image",
                 "external": {"url": record.pin.image_url}}
            ]
        }
    if v.industry:
        props["產業用途"] = {"select": {"name": v.industry}}
    if v.category:
        props["類別"] = {"select": {"name": v.category}}
    return props


class NotionWriter:
    def __init__(self, api_key: Optional[str] = None, database_id: Optional[str] = None):
        self.client = Client(auth=api_key or config.notion_api_key)
        self.database_id = database_id or config.notion_database_id

    def exists(self, source_url: str) -> bool:
        """檢查「來源出處」是否已存在，避免重複寫入。"""
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
