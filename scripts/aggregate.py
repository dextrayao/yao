"""Aggregate raw timesheet rows into a structured weekly report.

Cost basis: fully-loaded labor cost = monthly salary × 1.2551.
Hourly rate  = (daily_salary × 1.2551) / 8.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from .name_map import resolve
from .notion_client import SalaryRow
from .sheets_client import TimesheetRow

LOADED_COST_MULTIPLIER = 1.2551
WORK_HOURS_PER_DAY = 8

INTERNAL_CLIENT = "酷客創藝"
LEAVE_KEYWORDS = {"請假"}


@dataclass
class Contributor:
    full_name: str
    nickname: str
    department: str
    hours: float = 0.0
    cost: float = 0.0
    is_unknown: bool = False


@dataclass
class Project:
    name: str
    client: str
    hours: float = 0.0
    cost: float = 0.0
    contributors: dict[str, Contributor] = field(default_factory=dict)

    def add(self, contributor_key: str, contributor: Contributor) -> None:
        existing = self.contributors.get(contributor_key)
        if existing:
            existing.hours += contributor.hours
            existing.cost += contributor.cost
        else:
            self.contributors[contributor_key] = contributor


@dataclass
class ClientGroup:
    name: str
    hours: float = 0.0
    cost: float = 0.0
    projects: dict[str, Project] = field(default_factory=dict)

    def project(self, name: str) -> Project:
        if name not in self.projects:
            self.projects[name] = Project(name=name, client=self.name)
        return self.projects[name]


@dataclass
class DataQuality:
    rows_total: int = 0
    rows_used: int = 0
    rows_missing_hours: int = 0
    rows_missing_project: int = 0
    rows_unmapped_name: int = 0
    rows_no_salary: int = 0
    unknown_nicknames: set[str] = field(default_factory=set)


@dataclass
class WeekReport:
    iso_week: str
    week_start: date
    week_end: date
    total_hours: float = 0.0
    total_cost: float = 0.0
    billable_hours: float = 0.0
    billable_cost: float = 0.0
    internal_hours: float = 0.0
    internal_cost: float = 0.0
    leave_hours: float = 0.0
    leave_cost: float = 0.0
    unclassified_hours: float = 0.0
    unclassified_cost: float = 0.0
    clients: list[ClientGroup] = field(default_factory=list)
    internal_projects: list[Project] = field(default_factory=list)
    unclassified: list[Project] = field(default_factory=list)
    department_costs: dict[str, float] = field(default_factory=dict)
    department_hours: dict[str, float] = field(default_factory=dict)
    quality: DataQuality = field(default_factory=DataQuality)


_HOURS_RE = re.compile(r"(\d+(?:\.\d+)?)")


def parse_hours(raw: str) -> float:
    """Parse strings like '8hr', '0.5hr', '7.5', '8小時' → float.

    Returns 0.0 when no number is present.
    """
    if not raw:
        return 0.0
    m = _HOURS_RE.search(raw)
    if not m:
        return 0.0
    try:
        return float(m.group(1))
    except ValueError:
        return 0.0


def _hourly_rate(salary: SalaryRow) -> float:
    return salary.daily_salary * LOADED_COST_MULTIPLIER / WORK_HOURS_PER_DAY


def _department_average_daily(salaries: dict[str, SalaryRow], dept: str) -> float:
    members = [s for s in salaries.values() if s.department == dept and s.active]
    if not members:
        # Fall back to whole-company average
        members = [s for s in salaries.values() if s.active]
        if not members:
            return 0.0
    return sum(s.daily_salary for s in members) / len(members)


def _is_leave(project: str) -> bool:
    if not project:
        return False
    return any(k in project for k in LEAVE_KEYWORDS)


def aggregate(
    rows: list[TimesheetRow],
    salaries: dict[str, SalaryRow],
    week_start: date,
    week_end: date,
    iso_week: str,
) -> WeekReport:
    report = WeekReport(
        iso_week=iso_week, week_start=week_start, week_end=week_end
    )
    q = report.quality

    clients_by_name: dict[str, ClientGroup] = {}
    internal_by_project: dict[str, Project] = {}
    unclassified_by_project: dict[str, Project] = {}

    for row in rows:
        q.rows_total += 1
        hours = parse_hours(row.hours_raw)
        if hours <= 0:
            q.rows_missing_hours += 1
            continue

        full_name = resolve(row.nickname)
        is_unknown = full_name is None
        if is_unknown:
            q.rows_unmapped_name += 1
            q.unknown_nicknames.add(row.nickname)

        salary = salaries.get(full_name) if full_name else None
        if salary:
            daily = salary.daily_salary
            dept = salary.department or row.department
        else:
            # Fall back to department average daily salary
            daily = _department_average_daily(salaries, row.department)
            dept = row.department or "未知部門"
            q.rows_no_salary += 1

        hourly = daily * LOADED_COST_MULTIPLIER / WORK_HOURS_PER_DAY
        cost = hours * hourly

        # Per-department roll-up uses the salary table's department if available
        report.department_hours[dept] = report.department_hours.get(dept, 0.0) + hours
        report.department_costs[dept] = report.department_costs.get(dept, 0.0) + cost

        # Track totals
        report.total_hours += hours
        report.total_cost += cost

        # Categorize
        if _is_leave(row.project):
            report.leave_hours += hours
            report.leave_cost += cost
            continue

        if not row.project or not row.client:
            report.unclassified_hours += hours
            report.unclassified_cost += cost
            bucket = unclassified_by_project.setdefault(
                row.project or "(未填專案)",
                Project(name=row.project or "(未填專案)", client=row.client or "(未填客戶)"),
            )
            _add_contributor(bucket, full_name, row, dept, hours, cost, is_unknown)
            continue

        if row.client == INTERNAL_CLIENT:
            report.internal_hours += hours
            report.internal_cost += cost
            proj = internal_by_project.setdefault(
                row.project, Project(name=row.project, client=INTERNAL_CLIENT)
            )
            _add_contributor(proj, full_name, row, dept, hours, cost, is_unknown)
            continue

        report.billable_hours += hours
        report.billable_cost += cost
        client = clients_by_name.setdefault(row.client, ClientGroup(name=row.client))
        client.hours += hours
        client.cost += cost
        proj = client.project(row.project)
        _add_contributor(proj, full_name, row, dept, hours, cost, is_unknown)

        q.rows_used += 1

    # Sort: clients by cost desc; projects within client by cost desc;
    # contributors by cost desc.
    for cg in clients_by_name.values():
        for p in cg.projects.values():
            p.hours = sum(c.hours for c in p.contributors.values())
            p.cost = sum(c.cost for c in p.contributors.values())
        cg.projects = dict(
            sorted(cg.projects.items(), key=lambda kv: kv[1].cost, reverse=True)
        )

    report.clients = sorted(
        clients_by_name.values(), key=lambda c: c.cost, reverse=True
    )

    for p in internal_by_project.values():
        p.hours = sum(c.hours for c in p.contributors.values())
        p.cost = sum(c.cost for c in p.contributors.values())
    report.internal_projects = sorted(
        internal_by_project.values(), key=lambda p: p.cost, reverse=True
    )

    for p in unclassified_by_project.values():
        p.hours = sum(c.hours for c in p.contributors.values())
        p.cost = sum(c.cost for c in p.contributors.values())
    report.unclassified = sorted(
        unclassified_by_project.values(), key=lambda p: p.cost, reverse=True
    )

    return report


def _add_contributor(
    project: Project,
    full_name: str | None,
    row: TimesheetRow,
    dept: str,
    hours: float,
    cost: float,
    is_unknown: bool,
) -> None:
    key = full_name or f"未知:{row.nickname}"
    project.add(
        key,
        Contributor(
            full_name=full_name or row.nickname,
            nickname=row.nickname,
            department=dept,
            hours=hours,
            cost=cost,
            is_unknown=is_unknown,
        ),
    )
