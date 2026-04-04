"""投資複利模組 — 支援階段式投入與年度加碼"""

from dataclasses import dataclass, field


@dataclass
class InvestPhase:
    monthly_contribution: int   # 每月投入金額
    duration_years: int         # 持續年數


@dataclass
class InvestParams:
    phases: list[InvestPhase] = field(
        default_factory=lambda: [InvestPhase(15_000, 3), InvestPhase(30_000, 11)]
    )
    annual_bonus: int = 30_000      # 每年 8 月額外加碼 (退稅投入)
    annual_roi: float = 0.07        # 預期年化報酬率
    current_balance: int = 0        # 目前帳戶餘額


class InvestEngine:
    def __init__(self, params: InvestParams | None = None):
        self.params = params or InvestParams()

    @property
    def total_years(self) -> int:
        return sum(p.duration_years for p in self.params.phases)

    def monthly_contribution_at_year(self, year_index: int) -> int:
        """依年份索引 (0-based) 查詢當期每月投入金額"""
        cumulative = 0
        for phase in self.params.phases:
            cumulative += phase.duration_years
            if year_index < cumulative:
                return phase.monthly_contribution
        # 超過所有階段則沿用最後一期
        return self.params.phases[-1].monthly_contribution if self.params.phases else 0

    def simulate_year(self, starting_balance: float, year_index: int) -> dict:
        """模擬單一年度投資成長

        Returns:
            dict with keys: start_balance, end_balance, contributions, bonus, growth
        """
        monthly_rate = (1 + self.params.annual_roi) ** (1 / 12) - 1
        monthly_contrib = self.monthly_contribution_at_year(year_index)
        balance = float(starting_balance)
        total_contributions = 0
        bonus_added = 0

        for month in range(1, 13):
            balance += monthly_contrib
            total_contributions += monthly_contrib
            if month == 8:
                balance += self.params.annual_bonus
                bonus_added = self.params.annual_bonus
                total_contributions += self.params.annual_bonus
            balance *= (1 + monthly_rate)

        return {
            "start_balance": round(starting_balance),
            "end_balance": round(balance),
            "contributions": total_contributions,
            "bonus": bonus_added,
            "growth": round(balance - starting_balance - total_contributions),
        }

    def simulate_all(self) -> list[dict]:
        """逐年模擬所有階段，回傳每年快照 list"""
        results = []
        balance = float(self.params.current_balance)
        for year_idx in range(self.total_years):
            snapshot = self.simulate_year(balance, year_idx)
            snapshot["year_index"] = year_idx
            results.append(snapshot)
            balance = snapshot["end_balance"]
        return results
