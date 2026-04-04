"""CashflowEngine 單元測試"""

from engines.cashflow_engine import CashflowEngine, CashflowParams


def test_total_monthly_expenses():
    engine = CashflowEngine()
    # 18,000 + 25,000 + 10,000 = 53,000
    assert engine.total_monthly_expenses() == 53_000


def test_monthly_surplus():
    engine = CashflowEngine()
    surplus = engine.monthly_surplus(
        monthly_salary=125_000,
        monthly_tax=3_098,
        monthly_investment=15_000,
        subsidy_contribution=0,
    )
    # 125,000 - 3,098 - 15,000 - 53,000 = 53,902
    assert surplus == 53_902


def test_monthly_surplus_with_subsidy():
    engine = CashflowEngine()
    surplus = engine.monthly_surplus(
        monthly_salary=125_000,
        monthly_tax=3_098,
        monthly_investment=15_000,
        subsidy_contribution=10_000,
    )
    # 125,000 - 3,098 - 15,000 - 53,000 + 10,000 = 63,902
    assert surplus == 63_902


def test_expense_breakdown():
    engine = CashflowEngine()
    breakdown = engine.expense_breakdown()
    assert breakdown["房租"] == 18_000
    assert breakdown["生活費"] == 25_000
    assert breakdown["保險雜項"] == 10_000


def test_custom_expenses():
    engine = CashflowEngine(CashflowParams(rent=20_000, living=30_000, insurance_misc=5_000))
    assert engine.total_monthly_expenses() == 55_000
