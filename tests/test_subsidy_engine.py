"""SubsidyEngine 單元測試"""

from engines.subsidy_engine import SubsidyEngine, SubsidyParams


def test_monthly_subsidy_with_children():
    engine = SubsidyEngine()
    # 5,000 * 2.0 = 10,000
    assert engine.monthly_subsidy() == 10_000


def test_monthly_subsidy_without_children():
    engine = SubsidyEngine(SubsidyParams(has_children=False))
    assert engine.monthly_subsidy() == 5_000


def test_annual_subsidy():
    engine = SubsidyEngine()
    assert engine.annual_subsidy() == 120_000


def test_cashflow_contribution_excluded():
    engine = SubsidyEngine(SubsidyParams(include_in_cashflow=False))
    assert engine.cashflow_contribution() == 0


def test_cashflow_contribution_included():
    engine = SubsidyEngine(SubsidyParams(include_in_cashflow=True))
    assert engine.cashflow_contribution() == 10_000


def test_custom_multiplier():
    engine = SubsidyEngine(SubsidyParams(base_monthly=3_000, child_multiplier=1.5))
    assert engine.monthly_subsidy() == 4_500
