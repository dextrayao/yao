"""Render WeekReport to HTML using Jinja2 + inline CSS + inline SVG donut."""

from __future__ import annotations

import json
import math
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .aggregate import WeekReport

TPL_DIR = Path(__file__).resolve().parent.parent / "templates"
DEPT_PALETTE = [
    "#C96342",  # accent
    "#4F7B5F",
    "#C7813F",
    "#6B6960",
    "#B0463A",
    "#7E6A3E",
    "#5E6C8C",
    "#9A968B",
    "#3F594E",
    "#A56C3D",
]


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TPL_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _css() -> str:
    return (TPL_DIR / "base.css").read_text(encoding="utf-8")


def _donut_svg(dept_costs: dict[str, float], colors: dict[str, str]) -> str:
    """Render a simple stroked-arc donut chart (no JS, no external assets)."""
    total = sum(dept_costs.values())
    if total <= 0:
        return ""
    size, stroke = 200, 28
    cx = cy = size / 2
    r = (size - stroke) / 2
    circumference = 2 * math.pi * r

    parts: list[str] = [
        f'<svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" '
        'role="img" aria-label="Department cost breakdown">',
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
        'stroke="#E5E1D6" stroke-width="' + str(stroke) + '"/>',
    ]
    offset = 0.0
    items = sorted(dept_costs.items(), key=lambda kv: kv[1], reverse=True)
    for dept, cost in items:
        frac = cost / total
        length = frac * circumference
        color = colors.get(dept, "#9A968B")
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
            f'stroke="{color}" stroke-width="{stroke}" '
            f'stroke-dasharray="{length:.4f} {circumference - length:.4f}" '
            f'stroke-dashoffset="{-offset:.4f}" '
            f'transform="rotate(-90 {cx} {cy})" '
            'stroke-linecap="butt" />'
        )
        offset += length
    parts.append(
        f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" '
        'font-family="Tiempos Headline, Source Serif Pro, serif" '
        'font-size="18" fill="#1F1E1D">NT$</text>'
        f'<text x="{cx}" y="{cy + 18}" text-anchor="middle" '
        'font-family="Tiempos Headline, Source Serif Pro, serif" '
        f'font-size="22" fill="#1F1E1D">{total:,.0f}</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def _iso_week_number(iso_week: str) -> str:
    """`2026-W20` → `20`."""
    m = re.search(r"W(\d+)", iso_week)
    return m.group(1) if m else iso_week


def render_report(
    report: WeekReport, git_sha: str | None = None, tz: str = "Asia/Taipei"
) -> str:
    env = _env()
    tpl = env.get_template("report.html.j2")

    # Assign stable colors to departments by cost rank
    dept_sorted = sorted(
        report.department_costs.items(), key=lambda kv: kv[1], reverse=True
    )
    dept_colors = {
        dept: DEPT_PALETTE[i % len(DEPT_PALETTE)]
        for i, (dept, _) in enumerate(dept_sorted)
    }

    now = datetime.now(ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M %Z")

    return tpl.render(
        report=report,
        css=_css(),
        donut_svg=_donut_svg(report.department_costs, dept_colors),
        dept_sorted=dept_sorted,
        dept_colors=dept_colors,
        week_number=_iso_week_number(report.iso_week),
        generated_at=now,
        git_sha=git_sha,
    )


def render_index(entries: list[dict]) -> str:
    """entries: list of {iso_week, range, total_cost, total_hours, filename}."""
    env = _env()
    tpl = env.get_template("index.html.j2")
    sorted_entries = sorted(entries, key=lambda e: e["iso_week"], reverse=True)
    return tpl.render(css=_css(), entries=sorted_entries)


def scan_existing_reports(docs_dir: Path) -> list[dict]:
    """Build the index from per-week JSON sidecar files written next to each HTML."""
    weeks_dir = docs_dir / "weeks"
    out: list[dict] = []
    if not weeks_dir.exists():
        return out
    for meta_path in weeks_dir.glob("*.json"):
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            data["filename"] = data.get("filename") or (meta_path.stem + ".html")
            out.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return out
