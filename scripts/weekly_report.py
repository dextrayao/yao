"""CLI entrypoint: generate one week's labor-cost report.

Usage:
  python -m scripts.weekly_report                  # last completed week (Mon–Sun)
  python -m scripts.weekly_report 2026-W16         # explicit ISO week
  python -m scripts.weekly_report --fixture tests/fixtures/week16.csv \\
      --salary tests/fixtures/salary.json --out /tmp/out.html
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .aggregate import aggregate
from .notion_client import SalaryRow, fetch_salary_table
from .render import render_index, render_report, scan_existing_reports
from .sheets_client import TimesheetRow, fetch_rows, filter_week

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
WEEKS_DIR = DOCS_DIR / "weeks"


def _iso_week_bounds(iso_week: str) -> tuple[date, date]:
    """`2026-W20` → (Mon 2026-05-11, Sun 2026-05-17)."""
    m = re.fullmatch(r"(\d{4})-W(\d{1,2})", iso_week)
    if not m:
        raise ValueError(f"Invalid ISO week: {iso_week}")
    year, week = int(m.group(1)), int(m.group(2))
    monday = date.fromisocalendar(year, week, 1)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _last_complete_week(tz: str = "Asia/Taipei") -> str:
    today = datetime.now(ZoneInfo(tz)).date()
    # ISO weekday: Mon=1, Sun=7. "Last complete week" = the week before
    # the current one (when run on Mon morning, we want Mon-Sun just past).
    last_monday = today - timedelta(days=today.isoweekday() + 6)
    year, week, _ = last_monday.isocalendar()
    return f"{year}-W{week:02d}"


def _load_fixture_rows(path: Path) -> list[TimesheetRow]:
    """Load timesheet rows from a CSV fixture with the same column order."""
    rows: list[TimesheetRow] = []
    with path.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)  # header
        for r in reader:
            if not r or not r[0].strip():
                continue
            padded = list(r) + [""] * (9 - len(r))
            try:
                y, m, d = (int(p) for p in padded[0].replace("-", "/").split("/"))
                log_date = date(y, m, d)
            except (ValueError, IndexError):
                continue
            rows.append(
                TimesheetRow(
                    log_date=log_date,
                    department=padded[1].strip(),
                    nickname=padded[2].strip(),
                    client=padded[3].strip(),
                    project=padded[4].strip(),
                    content=padded[5].strip(),
                    hours_raw=padded[6].strip(),
                    status=padded[7].strip(),
                )
            )
    return rows


def _load_fixture_salaries(path: Path) -> dict[str, SalaryRow]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, SalaryRow] = {}
    for r in data:
        out[r["full_name"]] = SalaryRow(
            full_name=r["full_name"],
            department=r["department"],
            title=r.get("title", ""),
            level=r.get("level", ""),
            monthly_salary=int(r["monthly_salary"]),
            daily_salary=int(r["daily_salary"]),
            active=bool(r.get("active", True)),
        )
    return out


def _git_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT), text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _write_outputs(html: str, report, html_path: Path, meta_path: Path) -> None:
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")
    meta = {
        "iso_week": report.iso_week,
        "range": f"{report.week_start} – {report.week_end}",
        "total_cost": report.total_cost,
        "total_hours": report.total_hours,
        "filename": html_path.name,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate weekly labor-cost report.")
    parser.add_argument("week", nargs="?", help="ISO week, e.g. 2026-W20")
    parser.add_argument("--fixture", type=Path, help="CSV timesheet fixture (for dry-run)")
    parser.add_argument("--salary", type=Path, help="JSON salary fixture")
    parser.add_argument("--out", type=Path, help="Override output HTML path")
    parser.add_argument(
        "--skip-index", action="store_true", help="Do not regenerate docs/index.html"
    )
    args = parser.parse_args(argv)

    iso_week = args.week or _last_complete_week()
    week_start, week_end = _iso_week_bounds(iso_week)
    print(f"[weekly-report] week={iso_week} range={week_start}–{week_end}", file=sys.stderr)

    if args.fixture:
        if not args.salary:
            print("--fixture requires --salary", file=sys.stderr)
            return 2
        rows = _load_fixture_rows(args.fixture)
        salaries = _load_fixture_salaries(args.salary)
        rows = filter_week(rows, week_start, week_end)
    else:
        sheet_id = os.environ["SHEET_ID"]
        salary_page = os.environ["SALARY_PAGE_ID"]
        print("[weekly-report] fetching salaries from Notion…", file=sys.stderr)
        salaries = fetch_salary_table(salary_page)
        print(f"[weekly-report] {len(salaries)} salary rows", file=sys.stderr)
        print("[weekly-report] fetching timesheet from Google Sheets…", file=sys.stderr)
        all_rows = fetch_rows(sheet_id)
        rows = filter_week(all_rows, week_start, week_end)
        print(f"[weekly-report] {len(rows)} timesheet rows in week", file=sys.stderr)

    report = aggregate(rows, salaries, week_start, week_end, iso_week)
    html = render_report(report, git_sha=_git_sha())

    html_path = args.out or (WEEKS_DIR / f"{iso_week}.html")
    meta_path = html_path.with_suffix(".json")
    _write_outputs(html, report, html_path, meta_path)
    print(f"[weekly-report] wrote {html_path}", file=sys.stderr)

    if not args.skip_index and not args.out:
        entries = scan_existing_reports(DOCS_DIR)
        (DOCS_DIR / "index.html").write_text(render_index(entries), encoding="utf-8")
        print(f"[weekly-report] wrote {DOCS_DIR / 'index.html'}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
