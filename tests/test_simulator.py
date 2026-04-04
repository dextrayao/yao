"""RetirementSimulator 整合測試"""

from engines.tax_engine import TaxEngine
from engines.subsidy_engine import SubsidyEngine
from engines.invest_engine import InvestEngine, InvestParams, InvestPhase
from engines.cashflow_engine import CashflowEngine
from simulator import RetirementSimulator, RetirementParams


def _make_simulator(**overrides) -> RetirementSimulator:
    params = RetirementParams(**overrides) if overrides else RetirementParams()
    invest_params = InvestParams(
        phases=[
            InvestPhase(15_000, 3),
            InvestPhase(30_000, params.retirement_age - params.current_age - 3),
        ],
    )
    return RetirementSimulator(
        TaxEngine(),
        SubsidyEngine(),
        InvestEngine(invest_params),
        CashflowEngine(),
        params,
    )


def test_simulate_length():
    sim = _make_simulator()
    snapshots = sim.simulate()
    # 65 - 51 = 14 years
    assert len(snapshots) == 14


def test_simulate_age_range():
    sim = _make_simulator()
    snapshots = sim.simulate()
    assert snapshots[0].age == 51
    assert snapshots[-1].age == 64  # last simulated year is age 64 (retiring at 65)


def test_portfolio_grows():
    sim = _make_simulator()
    snapshots = sim.simulate()
    for i in range(1, len(snapshots)):
        assert snapshots[i].year_end_portfolio > snapshots[i - 1].year_end_portfolio


def test_retirement_summary_keys():
    sim = _make_simulator()
    summary = sim.retirement_summary()
    expected_keys = {
        "final_portfolio",
        "portfolio_monthly_withdrawal",
        "labor_insurance_pension",
        "labor_retirement_monthly",
        "total_monthly_passive_income",
        "monthly_expenses",
        "coverage_ratio",
        "snapshots",
    }
    assert set(summary.keys()) == expected_keys


def test_retirement_summary_positive_values():
    sim = _make_simulator()
    summary = sim.retirement_summary()
    assert summary["final_portfolio"] > 0
    assert summary["total_monthly_passive_income"] > 0
    assert summary["coverage_ratio"] > 0


def test_retirement_summary_passive_income_components():
    sim = _make_simulator()
    summary = sim.retirement_summary()
    expected_total = (
        summary["portfolio_monthly_withdrawal"]
        + summary["labor_insurance_pension"]
        + summary["labor_retirement_monthly"]
    )
    assert summary["total_monthly_passive_income"] == expected_total


def test_custom_retirement_age():
    sim = _make_simulator(retirement_age=60)
    snapshots = sim.simulate()
    # 60 - 51 = 9 years
    assert len(snapshots) == 9


def test_empty_simulation():
    sim = _make_simulator(current_age=65, retirement_age=65)
    summary = sim.retirement_summary()
    assert summary == {}
