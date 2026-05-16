"""Read the 工作日誌2026 Google Sheet via the Sheets API."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

COLUMN_DATE = 0
COLUMN_DEPT = 1
COLUMN_NAME = 2
COLUMN_CLIENT = 3
COLUMN_PROJECT = 4
COLUMN_CONTENT = 5
COLUMN_HOURS = 6
COLUMN_STATUS = 7
COLUMN_NEXT = 8


@dataclass(frozen=True)
class TimesheetRow:
    log_date: date
    department: str
    nickname: str
    client: str
    project: str
    content: str
    hours_raw: str
    status: str


def _service():
    # Lazy-imported so fixture-based dry-runs don't need google-auth/cryptography.
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    sa_json = os.environ.get("GOOGLE_SA_JSON")
    if not sa_json:
        raise RuntimeError("GOOGLE_SA_JSON env var is not set")
    info = json.loads(sa_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _parse_date(s: str) -> date | None:
    s = (s or "").strip()
    if not s:
        return None
    # Sheet uses "2026/4/1" style — and occasionally other separators.
    for sep in ("/", "-", "."):
        if sep in s:
            parts = s.split(sep)
            if len(parts) == 3:
                try:
                    y, m, d = (int(p) for p in parts)
                    return date(y, m, d)
                except ValueError:
                    return None
    return None


def fetch_rows(spreadsheet_id: str, sheet_range: str = "A:I") -> list[TimesheetRow]:
    """Fetch every row from the first worksheet, dropping the header row."""
    svc = _service()
    resp = (
        svc.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=sheet_range)
        .execute()
    )
    values = resp.get("values", [])
    if not values:
        return []

    rows: list[TimesheetRow] = []
    for raw in values[1:]:
        # Pad short rows so indexing is safe
        padded = raw + [""] * (9 - len(raw))
        log_date = _parse_date(padded[COLUMN_DATE])
        if not log_date:
            continue
        rows.append(
            TimesheetRow(
                log_date=log_date,
                department=padded[COLUMN_DEPT].strip(),
                nickname=padded[COLUMN_NAME].strip(),
                client=padded[COLUMN_CLIENT].strip(),
                project=padded[COLUMN_PROJECT].strip(),
                content=padded[COLUMN_CONTENT].strip(),
                hours_raw=padded[COLUMN_HOURS].strip(),
                status=padded[COLUMN_STATUS].strip(),
            )
        )
    return rows


def filter_week(
    rows: list[TimesheetRow], week_start: date, week_end: date
) -> list[TimesheetRow]:
    return [r for r in rows if week_start <= r.log_date <= week_end]
