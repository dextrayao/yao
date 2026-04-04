"""台灣所得稅計算模組 (2026 年參數)"""

from dataclasses import dataclass

# 累進稅率表: (下限, 上限, 稅率)
TAX_BRACKETS: list[tuple[int, float, float]] = [
    (0,         590_000,   0.05),
    (590_000,   1_330_000, 0.12),
    (1_330_000, 2_660_000, 0.20),
    (2_660_000, 4_980_000, 0.30),
    (4_980_000, float("inf"), 0.40),
]


@dataclass
class TaxParams:
    exemption: int = 101_000            # 每人免稅額
    standard_deduction: int = 136_000   # 標準扣除額
    salary_deduction: int = 227_000     # 薪資所得特別扣除額
    rent_deduction_cap: int = 180_000   # 房租特別扣除額上限
    dependents: int = 2                 # 扶養人數 (不含本人)
    annual_rent_paid: int = 216_000     # 年租金 (月租 18,000 * 12)
    use_rent_deduction: bool = True     # 是否使用房租扣除 (與租金補貼互斥)


class TaxEngine:
    def __init__(self, params: TaxParams | None = None):
        self.params = params or TaxParams()

    def total_exemption(self) -> int:
        """免稅額合計 = (本人 + 扶養人數) * 每人免稅額"""
        return (1 + self.params.dependents) * self.params.exemption

    def rent_deduction(self) -> int:
        """房租扣除額 (與租金補貼互斥)"""
        if not self.params.use_rent_deduction:
            return 0
        return min(self.params.annual_rent_paid, self.params.rent_deduction_cap)

    def total_deductions(self) -> int:
        """扣除額合計 = 標準扣除額 + 薪資扣除額 + 房租扣除額"""
        return (
            self.params.standard_deduction
            + self.params.salary_deduction
            + self.rent_deduction()
        )

    def taxable_income(self, gross_annual: int) -> int:
        """所得淨額 = 年收入 - 免稅額 - 扣除額 (最低為 0)"""
        return max(0, gross_annual - self.total_exemption() - self.total_deductions())

    def compute_tax(self, gross_annual: int) -> int:
        """依累進稅率計算應納稅額"""
        taxable = self.taxable_income(gross_annual)
        tax = 0.0
        for lower, upper, rate in TAX_BRACKETS:
            if taxable <= 0:
                break
            bracket_width = upper - lower
            taxed_in_bracket = min(taxable, bracket_width)
            tax += taxed_in_bracket * rate
            taxable -= taxed_in_bracket
        return round(tax)

    def monthly_tax(self, monthly_salary: int) -> int:
        """月均稅額 = 年稅 / 12"""
        annual_tax = self.compute_tax(monthly_salary * 12)
        return round(annual_tax / 12)
