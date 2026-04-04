"""現金流與開銷模組"""

from dataclasses import dataclass


@dataclass
class CashflowParams:
    rent: int = 18_000              # 房租
    living: int = 25_000            # 生活費
    insurance_misc: int = 10_000    # 保險雜項


class CashflowEngine:
    def __init__(self, params: CashflowParams | None = None):
        self.params = params or CashflowParams()

    def total_monthly_expenses(self) -> int:
        """每月總開銷"""
        return self.params.rent + self.params.living + self.params.insurance_misc

    def monthly_surplus(
        self,
        monthly_salary: int,
        monthly_tax: int,
        monthly_investment: int,
        subsidy_contribution: int = 0,
    ) -> int:
        """每月結餘 = 薪資 - 稅 - 投資 - 開銷 + 補貼"""
        return (
            monthly_salary
            - monthly_tax
            - monthly_investment
            - self.total_monthly_expenses()
            + subsidy_contribution
        )

    def expense_breakdown(self) -> dict[str, int]:
        """開銷明細"""
        return {
            "房租": self.params.rent,
            "生活費": self.params.living,
            "保險雜項": self.params.insurance_misc,
        }
