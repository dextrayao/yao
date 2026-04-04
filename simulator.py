"""退休精算整合引擎 — 模擬 51→65 歲逐年資產成長"""

from dataclasses import dataclass
from engines.tax_engine import TaxEngine
from engines.subsidy_engine import SubsidyEngine
from engines.invest_engine import InvestEngine
from engines.cashflow_engine import CashflowEngine


@dataclass
class RetirementParams:
    birth_year: int = 1975
    current_age: int = 51
    retirement_age: int = 65
    monthly_salary: int = 125_000
    labor_insurance_pension: int = 26_000   # 勞保年金 (65 歲起)
    labor_retirement_monthly: int = 13_500  # 勞退月領 (65 歲起)


@dataclass
class YearlySnapshot:
    age: int
    year: int
    gross_annual_income: int
    annual_tax: int
    annual_investment_contribution: int
    annual_expenses: int
    annual_subsidy: int
    year_end_portfolio: int
    monthly_surplus: int


class RetirementSimulator:
    def __init__(
        self,
        tax_engine: TaxEngine,
        subsidy_engine: SubsidyEngine,
        invest_engine: InvestEngine,
        cashflow_engine: CashflowEngine,
        params: RetirementParams | None = None,
    ):
        self.tax = tax_engine
        self.subsidy = subsidy_engine
        self.invest = invest_engine
        self.cashflow = cashflow_engine
        self.params = params or RetirementParams()

    def simulate(self) -> list[YearlySnapshot]:
        """逐年模擬從 current_age 到 retirement_age 的資產變化"""
        snapshots: list[YearlySnapshot] = []
        portfolio = float(self.invest.params.current_balance)
        years_to_simulate = self.params.retirement_age - self.params.current_age

        gross_annual = self.params.monthly_salary * 12
        annual_tax = self.tax.compute_tax(gross_annual)
        monthly_tax = round(annual_tax / 12)

        annual_subsidy = self.subsidy.annual_subsidy()
        subsidy_cashflow = self.subsidy.cashflow_contribution()

        annual_expenses = self.cashflow.total_monthly_expenses() * 12

        for year_idx in range(years_to_simulate):
            age = self.params.current_age + year_idx
            year = self.params.birth_year + age

            monthly_contrib = self.invest.monthly_contribution_at_year(year_idx)
            invest_result = self.invest.simulate_year(portfolio, year_idx)
            portfolio = invest_result["end_balance"]

            surplus = self.cashflow.monthly_surplus(
                self.params.monthly_salary,
                monthly_tax,
                monthly_contrib,
                subsidy_cashflow,
            )

            snapshots.append(YearlySnapshot(
                age=age,
                year=year,
                gross_annual_income=gross_annual,
                annual_tax=annual_tax,
                annual_investment_contribution=invest_result["contributions"],
                annual_expenses=annual_expenses,
                annual_subsidy=annual_subsidy,
                year_end_portfolio=round(portfolio),
                monthly_surplus=surplus,
            ))

        return snapshots

    def retirement_summary(self) -> dict:
        """65 歲退休摘要：被動收入、覆蓋率"""
        snapshots = self.simulate()
        if not snapshots:
            return {}

        final = snapshots[-1]
        final_portfolio = final.year_end_portfolio

        # 4% 安全提領率
        portfolio_monthly = round(final_portfolio * 0.04 / 12)
        pension = self.params.labor_insurance_pension
        retirement = self.params.labor_retirement_monthly
        total_passive = portfolio_monthly + pension + retirement

        monthly_expenses = self.cashflow.total_monthly_expenses()
        coverage_ratio = total_passive / monthly_expenses if monthly_expenses > 0 else 0

        return {
            "final_portfolio": final_portfolio,
            "portfolio_monthly_withdrawal": portfolio_monthly,
            "labor_insurance_pension": pension,
            "labor_retirement_monthly": retirement,
            "total_monthly_passive_income": total_passive,
            "monthly_expenses": monthly_expenses,
            "coverage_ratio": round(coverage_ratio, 2),
            "snapshots": snapshots,
        }
