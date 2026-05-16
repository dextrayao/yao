"""Fetch the salary table from the Notion `💰 人力成本分析` page.

Parses the two HTML-like tables on the page (現役人員 and 離職人員) and
returns a dict keyed by full name. Network calls go through the public
Notion API (https://api.notion.com/v1).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

import requests

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


@dataclass(frozen=True)
class SalaryRow:
    full_name: str
    department: str
    title: str
    level: str
    monthly_salary: int
    daily_salary: int
    active: bool


class NotionError(RuntimeError):
    pass


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _get(path: str, token: str) -> dict:
    r = requests.get(f"{NOTION_API}{path}", headers=_headers(token), timeout=30)
    if r.status_code != 200:
        raise NotionError(f"Notion API {path} -> {r.status_code}: {r.text}")
    return r.json()


def _list_block_children(block_id: str, token: str) -> list[dict]:
    out: list[dict] = []
    cursor: str | None = None
    while True:
        path = f"/blocks/{block_id}/children?page_size=100"
        if cursor:
            path += f"&start_cursor={cursor}"
        data = _get(path, token)
        out.extend(data.get("results", []))
        if not data.get("has_more"):
            return out
        cursor = data.get("next_cursor")


def _rich_text(rich: list[dict]) -> str:
    return "".join(seg.get("plain_text", "") for seg in rich)


def _to_int(s: str) -> int:
    digits = re.sub(r"[^0-9]", "", s or "")
    return int(digits) if digits else 0


def _heading_text(block: dict) -> str:
    t = block.get("type", "")
    if t.startswith("heading_"):
        return _rich_text(block[t].get("rich_text", []))
    if t == "paragraph":
        return _rich_text(block["paragraph"].get("rich_text", []))
    return ""


def _read_table(table_block_id: str, token: str) -> list[list[str]]:
    rows = _list_block_children(table_block_id, token)
    parsed: list[list[str]] = []
    for row in rows:
        if row.get("type") != "table_row":
            continue
        cells = row["table_row"].get("cells", [])
        parsed.append([_rich_text(cell) for cell in cells])
    return parsed


def fetch_salary_table(page_id: str, token: str | None = None) -> dict[str, SalaryRow]:
    """Return {full_name: SalaryRow} for active + former staff on the page."""
    token = token or os.environ["NOTION_TOKEN"]

    top_blocks = _list_block_children(page_id, token)

    # Walk blocks in order, remembering the most recent heading_3 text.
    # The first `table` after a heading containing "現役人員" is active staff;
    # the first table after "離職人員" is former staff.
    current_section = ""
    active_table_id: str | None = None
    former_table_id: str | None = None

    for b in top_blocks:
        text = _heading_text(b)
        if text:
            if "現役人員" in text:
                current_section = "active"
            elif "離職人員" in text:
                current_section = "former"
            else:
                # Other headings end the salary sections we care about
                if current_section in {"active", "former"} and "人員" not in text:
                    current_section = ""
        if b.get("type") == "table":
            tid = b["id"]
            if current_section == "active" and active_table_id is None:
                active_table_id = tid
            elif current_section == "former" and former_table_id is None:
                former_table_id = tid

    if not active_table_id:
        raise NotionError("Could not locate the 現役人員 table on the page")

    out: dict[str, SalaryRow] = {}

    active_rows = _read_table(active_table_id, token)
    # First row is the header
    for cells in active_rows[1:]:
        if len(cells) < 6 or not cells[1].strip():
            continue
        full_name = cells[1].strip()
        out[full_name] = SalaryRow(
            full_name=full_name,
            department=cells[0].strip(),
            title=cells[2].strip(),
            level=cells[3].strip(),
            monthly_salary=_to_int(cells[4]),
            daily_salary=_to_int(cells[5]),
            active=True,
        )

    if former_table_id:
        former_rows = _read_table(former_table_id, token)
        for cells in former_rows[1:]:
            if len(cells) < 6 or not cells[1].strip():
                continue
            full_name = cells[1].strip()
            # Don't overwrite active staff if a same-name rejoiner exists
            if full_name in out:
                continue
            out[full_name] = SalaryRow(
                full_name=full_name,
                department=cells[0].strip(),
                title=cells[2].strip(),
                level=cells[3].strip(),
                monthly_salary=_to_int(cells[4]),
                daily_salary=_to_int(cells[5]),
                active=False,
            )

    return out
