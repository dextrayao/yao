"""InvestEngine 單元測試"""

from engines.invest_engine import InvestEngine, InvestParams, InvestPhase


def test_total_years():
    engine = InvestEngine()
    assert engine.total_years == 14  # 3 + 11


def test_monthly_contribution_phase1():
    engine = InvestEngine()
    assert engine.monthly_contribution_at_year(0) == 15_000
    assert engine.monthly_contribution_at_year(2) == 15_000


def test_monthly_contribution_phase2():
    engine = InvestEngine()
    assert engine.monthly_contribution_at_year(3) == 30_000
    assert engine.monthly_contribution_at_year(13) == 30_000


def test_monthly_contribution_beyond_phases():
    engine = InvestEngine()
    # 超過 14 年，沿用最後一期
    assert engine.monthly_contribution_at_year(20) == 30_000


def test_simulate_year_zero_roi():
    engine = InvestEngine(InvestParams(
        phases=[InvestPhase(10_000, 1)],
        annual_bonus=30_000,
        annual_roi=0.0,
        current_balance=0,
    ))
    result = engine.simulate_year(0, 0)
    # 12 months * 10,000 + 30,000 bonus = 150,000
    assert result["end_balance"] == 150_000
    assert result["contributions"] == 150_000
    assert result["growth"] == 0


def test_simulate_year_with_roi():
    engine = InvestEngine(InvestParams(
        phases=[InvestPhase(10_000, 1)],
        annual_bonus=0,
        annual_roi=0.12,
        current_balance=0,
    ))
    result = engine.simulate_year(0, 0)
    # With 12% ROI, end balance should be > 120,000 (pure contributions)
    assert result["end_balance"] > 120_000
    assert result["growth"] > 0


def test_simulate_year_with_starting_balance():
    engine = InvestEngine(InvestParams(
        phases=[InvestPhase(0, 1)],
        annual_bonus=0,
        annual_roi=0.10,
        current_balance=0,
    ))
    result = engine.simulate_year(1_000_000, 0)
    # 1M * 10% ≈ 100K growth
    assert result["end_balance"] > 1_000_000
    assert result["growth"] > 90_000


def test_simulate_all_length():
    engine = InvestEngine()
    results = engine.simulate_all()
    assert len(results) == 14


def test_simulate_all_monotonic():
    engine = InvestEngine()
    results = engine.simulate_all()
    for i in range(1, len(results)):
        assert results[i]["end_balance"] > results[i - 1]["end_balance"]
