"""租金補貼模組"""

from dataclasses import dataclass


@dataclass
class SubsidyParams:
    base_monthly: int = 5_000       # 基準補貼額 (台北市)
    child_multiplier: float = 2.0   # 育兒加碼倍數
    has_children: bool = True       # 是否有子女
    include_in_cashflow: bool = False  # 是否計入個人現金流 (False = 轉交他人)


class SubsidyEngine:
    def __init__(self, params: SubsidyParams | None = None):
        self.params = params or SubsidyParams()

    def monthly_subsidy(self) -> int:
        """每月實領補貼"""
        if self.params.has_children:
            return round(self.params.base_monthly * self.params.child_multiplier)
        return self.params.base_monthly

    def annual_subsidy(self) -> int:
        """年度補貼總額"""
        return self.monthly_subsidy() * 12

    def cashflow_contribution(self) -> int:
        """計入個人現金流的月補貼 (若轉交他人則為 0)"""
        if self.params.include_in_cashflow:
            return self.monthly_subsidy()
        return 0
