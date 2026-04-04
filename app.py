"""2030 財富自由與 65 歲退休精算系統 — Streamlit Web 介面"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from engines.tax_engine import TaxEngine, TaxParams
from engines.subsidy_engine import SubsidyEngine, SubsidyParams
from engines.invest_engine import InvestEngine, InvestParams, InvestPhase
from engines.cashflow_engine import CashflowEngine, CashflowParams
from simulator import RetirementSimulator, RetirementParams


def main():
    st.set_page_config(
        page_title="2030 財富自由精算系統",
        page_icon="📊",
        layout="wide",
    )

    st.title("2030 財富自由與 65 歲退休精算系統")
    st.caption("模擬資產成長軌跡，掌握退休財務全貌")

    # ── Sidebar ──────────────────────────────────────────────
    with st.sidebar:
        st.header("個人資訊")
        birth_year = st.number_input("出生年", value=1975, min_value=1950, max_value=2000)
        current_age = 2026 - birth_year
        st.metric("現在年齡", f"{current_age} 歲")
        retirement_age = st.slider("目標退休年齡", 55, 70, 65)
        monthly_salary = st.number_input(
            "月薪 (NTD)", value=125_000, min_value=30_000, max_value=500_000, step=5_000
        )

        st.divider()
        st.header("稅務設定")
        dependents = st.number_input("扶養人數 (不含本人)", value=2, min_value=0, max_value=10)
        monthly_rent = st.number_input("月租金", value=18_000, min_value=0, step=1_000)
        receive_subsidy = st.checkbox("領取租金補貼", value=True)
        use_rent_deduction = not receive_subsidy
        if receive_subsidy:
            st.info("領取租金補貼時，不可同時申報房租扣除額")

        st.divider()
        st.header("補助設定")
        subsidy_base = st.number_input("基準補貼額 (月)", value=5_000, min_value=0, step=500)
        child_multiplier = st.number_input(
            "育兒加碼倍數", value=2.0, min_value=1.0, max_value=5.0, step=0.1
        )
        include_subsidy_in_cashflow = st.checkbox("補貼計入個人現金流", value=False)

        st.divider()
        st.header("投資設定")
        phase1_monthly = st.number_input(
            "階段 1 月投入", value=15_000, min_value=0, step=1_000
        )
        phase1_years = st.number_input("階段 1 年數", value=3, min_value=1, max_value=30)
        phase2_monthly = st.number_input(
            "階段 2 月投入", value=30_000, min_value=0, step=1_000
        )
        remaining_years = max(1, retirement_age - current_age - phase1_years)
        phase2_years = st.number_input(
            "階段 2 年數", value=remaining_years, min_value=1, max_value=30
        )
        annual_bonus = st.number_input("年度加碼 (8 月退稅投入)", value=30_000, min_value=0, step=5_000)
        annual_roi = st.slider("預期年化報酬率 (%)", 1.0, 15.0, 7.0, 0.5) / 100
        current_balance = st.number_input(
            "目前投資帳戶餘額", value=0, min_value=0, step=100_000
        )

        st.divider()
        st.header("每月開銷")
        expense_rent = st.number_input("房租", value=18_000, min_value=0, step=1_000, key="exp_rent")
        expense_living = st.number_input("生活費", value=25_000, min_value=0, step=1_000)
        expense_insurance = st.number_input("保險雜項", value=10_000, min_value=0, step=1_000)

        st.divider()
        st.header("退休收入")
        labor_pension = st.number_input("勞保年金 (月)", value=26_000, min_value=0, step=1_000)
        labor_retirement = st.number_input("勞退月領", value=13_500, min_value=0, step=500)

    # ── 建立引擎 ─────────────────────────────────────────────
    tax_engine = TaxEngine(TaxParams(
        dependents=dependents,
        annual_rent_paid=monthly_rent * 12,
        use_rent_deduction=use_rent_deduction,
    ))

    subsidy_engine = SubsidyEngine(SubsidyParams(
        base_monthly=subsidy_base,
        child_multiplier=child_multiplier,
        has_children=dependents > 0,
        include_in_cashflow=include_subsidy_in_cashflow,
    ))

    invest_engine = InvestEngine(InvestParams(
        phases=[
            InvestPhase(phase1_monthly, phase1_years),
            InvestPhase(phase2_monthly, phase2_years),
        ],
        annual_bonus=annual_bonus,
        annual_roi=annual_roi,
        current_balance=current_balance,
    ))

    cashflow_engine = CashflowEngine(CashflowParams(
        rent=expense_rent,
        living=expense_living,
        insurance_misc=expense_insurance,
    ))

    sim = RetirementSimulator(
        tax_engine, subsidy_engine, invest_engine, cashflow_engine,
        RetirementParams(
            birth_year=birth_year,
            current_age=current_age,
            retirement_age=retirement_age,
            monthly_salary=monthly_salary,
            labor_insurance_pension=labor_pension,
            labor_retirement_monthly=labor_retirement,
        ),
    )

    # ── 執行模擬 ─────────────────────────────────────────────
    summary = sim.retirement_summary()
    if not summary:
        st.warning("無法模擬，請確認參數設定。")
        return

    snapshots = summary["snapshots"]

    # ── KPI 指標列 ───────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("目前每月結餘", f"${snapshots[0].monthly_surplus:,.0f}")
    with col2:
        st.metric(f"{retirement_age} 歲總資產", f"${summary['final_portfolio']:,.0f}")
    with col3:
        st.metric("退休每月被動收入", f"${summary['total_monthly_passive_income']:,.0f}")
    with col4:
        st.metric("開銷覆蓋率", f"{summary['coverage_ratio']:.1f}x")

    st.divider()

    # ── 資產成長曲線圖 ───────────────────────────────────────
    st.subheader("資產成長軌跡")
    ages = [s.age for s in snapshots]
    portfolios = [s.year_end_portfolio for s in snapshots]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=ages, y=portfolios,
        mode="lines+markers",
        name="投資組合",
        line=dict(color="#1f77b4", width=3),
        hovertemplate="年齡: %{x} 歲<br>資產: $%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title="年齡",
        yaxis_title="資產 (NTD)",
        yaxis_tickformat=",",
        height=400,
        margin=dict(l=20, r=20, t=30, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── 年度明細表 ───────────────────────────────────────────
    st.subheader("年度明細")
    df = pd.DataFrame([
        {
            "年齡": s.age,
            "西元年": s.year,
            "年收入": s.gross_annual_income,
            "年稅額": s.annual_tax,
            "年投資": s.annual_investment_contribution,
            "年開銷": s.annual_expenses,
            "年補貼": s.annual_subsidy,
            "年末資產": s.year_end_portfolio,
            "月結餘": s.monthly_surplus,
        }
        for s in snapshots
    ])
    st.dataframe(
        df.style.format({
            "年收入": "{:,.0f}",
            "年稅額": "{:,.0f}",
            "年投資": "{:,.0f}",
            "年開銷": "{:,.0f}",
            "年補貼": "{:,.0f}",
            "年末資產": "{:,.0f}",
            "月結餘": "{:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

    # ── 退休收入摘要 ─────────────────────────────────────────
    st.divider()
    st.subheader("退休收入摘要")
    rcol1, rcol2 = st.columns(2)

    with rcol1:
        st.success(f"""
        **{retirement_age} 歲退休時：**
        - 投資組合總值：**${summary['final_portfolio']:,.0f}**
        - 4% 安全提領 (月)：**${summary['portfolio_monthly_withdrawal']:,.0f}**
        - 勞保年金 (月)：**${summary['labor_insurance_pension']:,.0f}**
        - 勞退月領：**${summary['labor_retirement_monthly']:,.0f}**
        ---
        - 每月被動收入合計：**${summary['total_monthly_passive_income']:,.0f}**
        - 每月開銷：**${summary['monthly_expenses']:,.0f}**
        - 覆蓋率：**{summary['coverage_ratio']:.1f} 倍**
        """)

    with rcol2:
        # 月現金流圓餅圖
        monthly_tax = tax_engine.monthly_tax(monthly_salary)
        current_invest = invest_engine.monthly_contribution_at_year(0)
        expenses = cashflow_engine.expense_breakdown()
        surplus = cashflow_engine.monthly_surplus(
            monthly_salary, monthly_tax, current_invest,
            subsidy_engine.cashflow_contribution(),
        )

        labels = ["所得稅", "投資", *expenses.keys(), "結餘"]
        values = [monthly_tax, current_invest, *expenses.values(), max(0, surplus)]

        pie_fig = go.Figure(data=[go.Pie(
            labels=labels, values=values,
            hole=0.4,
            textinfo="label+percent",
            hovertemplate="%{label}: $%{value:,.0f}<extra></extra>",
        )])
        pie_fig.update_layout(
            title="每月薪資分配",
            height=350,
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(pie_fig, use_container_width=True)


if __name__ == "__main__":
    main()
