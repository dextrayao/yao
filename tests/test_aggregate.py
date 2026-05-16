from datetime import date

from scripts.aggregate import (
    LOADED_COST_MULTIPLIER,
    WORK_HOURS_PER_DAY,
    aggregate,
)
from scripts.notion_client import SalaryRow
from scripts.sheets_client import TimesheetRow


def _salary(name, dept, daily):
    return SalaryRow(
        full_name=name,
        department=dept,
        title="",
        level="",
        monthly_salary=daily * 22,
        daily_salary=daily,
        active=True,
    )


def _row(d, dept, nick, client, project, hours):
    return TimesheetRow(
        log_date=d,
        department=dept,
        nickname=nick,
        client=client,
        project=project,
        content="",
        hours_raw=f"{hours}hr",
        status="",
    )


def test_billable_cost_uses_loaded_multiplier():
    salaries = {"陳興宜": _salary("陳興宜", "動畫特效部", 2500)}
    rows = [_row(date(2026, 5, 12), "動畫特效部", "興宜", "富邦育樂", "林志傑退休展", 8)]
    rpt = aggregate(rows, salaries, date(2026, 5, 11), date(2026, 5, 17), "2026-W20")

    expected_cost = 8 * (2500 * LOADED_COST_MULTIPLIER / WORK_HOURS_PER_DAY)
    assert abs(rpt.total_cost - expected_cost) < 0.01
    assert abs(rpt.billable_cost - expected_cost) < 0.01
    assert rpt.leave_cost == 0
    assert len(rpt.clients) == 1
    fubon = rpt.clients[0]
    assert fubon.name == "富邦育樂"
    proj = next(iter(fubon.projects.values()))
    assert proj.name == "林志傑退休展"
    assert len(proj.contributors) == 1


def test_leave_excluded_from_project_costs():
    salaries = {"林旅歐": _salary("林旅歐", "動畫特效部", 2818)}
    rows = [
        _row(date(2026, 5, 12), "動畫特效部", "旅歐", "酷客創藝", "請假", 8),
        _row(date(2026, 5, 13), "動畫特效部", "旅歐", "鴻海科技", "智運中心", 8),
    ]
    rpt = aggregate(rows, salaries, date(2026, 5, 11), date(2026, 5, 17), "2026-W20")

    one_day = 2818 * LOADED_COST_MULTIPLIER
    assert abs(rpt.leave_cost - one_day) < 0.01
    assert abs(rpt.billable_cost - one_day) < 0.01
    assert len(rpt.clients) == 1
    assert rpt.clients[0].name == "鴻海科技"


def test_internal_separated_from_clients():
    salaries = {"楊舒帆": _salary("楊舒帆", "創意部", 2045)}
    rows = [
        _row(date(2026, 5, 12), "創意部", "舒帆", "酷客創藝", "自媒體", 4),
        _row(date(2026, 5, 13), "創意部", "舒帆", "富邦育樂", "林志傑退休展", 4),
    ]
    rpt = aggregate(rows, salaries, date(2026, 5, 11), date(2026, 5, 17), "2026-W20")

    assert len(rpt.clients) == 1  # 富邦育樂 only
    assert len(rpt.internal_projects) == 1
    assert rpt.internal_projects[0].name == "自媒體"
    assert rpt.billable_cost > 0
    assert rpt.internal_cost > 0


def test_unknown_nickname_falls_back_to_dept_average():
    salaries = {
        "蘇芸瑩": _salary("蘇芸瑩", "創意部", 2045),
        "魏子凌": _salary("魏子凌", "創意部", 1818),
    }
    # Unknown nickname "新人" in 創意部
    rows = [_row(date(2026, 5, 12), "創意部", "新人", "鴻海科技", "智慧城市科專", 8)]
    rpt = aggregate(rows, salaries, date(2026, 5, 11), date(2026, 5, 17), "2026-W20")

    assert rpt.quality.rows_unmapped_name == 1
    assert rpt.quality.rows_no_salary == 1
    assert "新人" in rpt.quality.unknown_nicknames
    # Cost > 0 because we fell back to dept average
    assert rpt.billable_cost > 0


def test_blank_project_goes_to_unclassified():
    salaries = {"楊舒帆": _salary("楊舒帆", "創意部", 2045)}
    rows = [_row(date(2026, 5, 12), "創意部", "舒帆", "", "", 2)]
    rpt = aggregate(rows, salaries, date(2026, 5, 11), date(2026, 5, 17), "2026-W20")

    assert len(rpt.clients) == 0
    assert len(rpt.unclassified) == 1
    assert rpt.unclassified_cost > 0


def test_missing_hours_skipped():
    salaries = {"楊舒帆": _salary("楊舒帆", "創意部", 2045)}
    rows = [
        _row(date(2026, 5, 12), "創意部", "舒帆", "鴻海科技", "X", 0),
        TimesheetRow(
            log_date=date(2026, 5, 12),
            department="創意部",
            nickname="舒帆",
            client="鴻海科技",
            project="Y",
            content="",
            hours_raw="",
            status="",
        ),
    ]
    rpt = aggregate(rows, salaries, date(2026, 5, 11), date(2026, 5, 17), "2026-W20")
    assert rpt.quality.rows_missing_hours == 2
    assert rpt.total_cost == 0


def test_department_rollup():
    salaries = {
        "楊舒帆": _salary("楊舒帆", "創意部", 2045),
        "陳興宜": _salary("陳興宜", "動畫特效部", 2500),
    }
    rows = [
        _row(date(2026, 5, 12), "創意部", "舒帆", "鴻海", "A", 8),
        _row(date(2026, 5, 12), "動畫特效部", "興宜", "鴻海", "B", 4),
    ]
    rpt = aggregate(rows, salaries, date(2026, 5, 11), date(2026, 5, 17), "2026-W20")

    assert "創意部" in rpt.department_costs
    assert "動畫特效部" in rpt.department_costs
    assert rpt.department_hours["創意部"] == 8
    assert rpt.department_hours["動畫特效部"] == 4
