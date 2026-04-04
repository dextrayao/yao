"""TaxEngine 單元測試"""

from engines.tax_engine import TaxEngine, TaxParams


def test_total_exemption_default():
    engine = TaxEngine()
    # (1 + 2) * 101,000 = 303,000
    assert engine.total_exemption() == 303_000


def test_total_exemption_no_dependents():
    engine = TaxEngine(TaxParams(dependents=0))
    assert engine.total_exemption() == 101_000


def test_rent_deduction_enabled():
    engine = TaxEngine(TaxParams(annual_rent_paid=216_000, use_rent_deduction=True))
    # cap at 180,000
    assert engine.rent_deduction() == 180_000


def test_rent_deduction_disabled_with_subsidy():
    engine = TaxEngine(TaxParams(use_rent_deduction=False))
    assert engine.rent_deduction() == 0


def test_rent_deduction_below_cap():
    engine = TaxEngine(TaxParams(annual_rent_paid=100_000, use_rent_deduction=True))
    assert engine.rent_deduction() == 100_000


def test_total_deductions_with_rent():
    engine = TaxEngine()
    # 136,000 + 227,000 + 180,000 = 543,000
    assert engine.total_deductions() == 543_000


def test_taxable_income_default():
    engine = TaxEngine()
    gross = 125_000 * 12  # 1,500,000
    # 1,500,000 - 303,000 - 543,000 = 654,000
    assert engine.taxable_income(gross) == 654_000


def test_taxable_income_floor_at_zero():
    engine = TaxEngine()
    assert engine.taxable_income(100_000) == 0


def test_compute_tax_default():
    engine = TaxEngine()
    gross = 125_000 * 12  # 1,500,000
    # taxable = 654,000
    # 590,000 * 5% = 29,500
    # 64,000 * 12% = 7,680
    # total = 37,180
    assert engine.compute_tax(gross) == 37_180


def test_compute_tax_zero_income():
    engine = TaxEngine()
    assert engine.compute_tax(0) == 0


def test_compute_tax_high_income():
    engine = TaxEngine(TaxParams(dependents=0, use_rent_deduction=False))
    # gross = 6,000,000
    # exemption = 101,000, deductions = 136,000 + 227,000 = 363,000
    # taxable = 6,000,000 - 101,000 - 363,000 = 5,536,000
    # 590,000 * 5% = 29,500
    # 740,000 * 12% = 88,800
    # 1,330,000 * 20% = 266,000
    # 2,320,000 * 30% = 696,000
    # 556,000 * 40% = 222,400
    # total = 1,302,700
    assert engine.compute_tax(6_000_000) == 1_302_700


def test_monthly_tax():
    engine = TaxEngine()
    monthly = engine.monthly_tax(125_000)
    # 37,180 / 12 ≈ 3,098
    assert monthly == 3098
