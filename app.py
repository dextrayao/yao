"""2030 財富自由與 65 歲退休精算系統 — Streamlit Web 介面 v2"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from engines.tax_engine import TaxEngine, TaxParams
from engines.subsidy_engine import SubsidyEngine, SubsidyParams
from engines.invest_engine import InvestEngine, InvestParams, InvestPhase
from engines.cashflow_engine import CashflowEngine, CashflowParams
from engines.stock_engine import StockEngine, StockHolding
from simulator import RetirementSimulator, RetirementParams


# ── 工具函式 ─────────────────────────────────────────────────
def fmt(n: float) -> str:
    """格式化金額：加千分位"""
    return f"{n:,.0f}"


def run_simulation(
    birth_year, current_age, retirement_age, monthly_salary,
    dependents, monthly_rent, use_rent_deduction,
    subsidy_base, child_multiplier, include_subsidy_in_cashflow,
    phase1_monthly, phase1_years, phase2_monthly, phase2_years,
    annual_bonus, annual_roi, current_balance,
    expense_rent, expense_living, expense_insurance,
    labor_pension, labor_retirement,
):
    """根據所有參數建立引擎並執行模擬"""
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
    return sim, tax_engine, subsidy_engine, invest_engine, cashflow_engine


def main():
    st.set_page_config(
        page_title="2030 財富自由精算系統",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # ── 自訂 CSS ─────────────────────────────────────────────
    st.markdown("""
    <style>
    /* KPI 卡片 */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #667eea11, #764ba211);
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    div[data-testid="stMetric"] label {
        font-size: 0.85rem !important;
        color: #666 !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 700 !important;
    }
    /* 側邊欄標題 */
    .sidebar-section-title {
        font-size: 0.9rem;
        font-weight: 600;
        color: #444;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 8px;
        margin-bottom: 4px;
    }
    /* 退休就緒度燈號 */
    .readiness-badge {
        display: inline-block;
        padding: 6px 18px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 1.1rem;
        margin: 4px 0;
    }
    .badge-green { background: #d4edda; color: #155724; }
    .badge-yellow { background: #fff3cd; color: #856404; }
    .badge-red { background: #f8d7da; color: #721c24; }
    </style>
    """, unsafe_allow_html=True)

    # ── 頂部標題 ─────────────────────────────────────────────
    st.markdown("## 2030 財富自由與 65 歲退休精算系統")
    st.markdown("*拉動左側參數，即時看到你的退休財務全貌*")

    # ── Sidebar ──────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 參數控制面板")

        # — 個人資訊 —
        with st.expander("👤 個人資訊", expanded=True):
            birth_year = st.number_input("出生年", value=1975, min_value=1950, max_value=2005)
            current_age = 2026 - birth_year
            retirement_age = st.slider("目標退休年齡", 55, 70, 65)
            years_to_go = retirement_age - current_age
            st.markdown(
                f"現年 **{current_age}** 歲 → 退休還有 **{years_to_go}** 年"
            )
            monthly_salary = st.slider(
                "月薪 (萬)", 3.0, 50.0, 12.5, 0.5,
                format="%.1f 萬",
            )
            monthly_salary_ntd = round(monthly_salary * 10_000)

        # — 稅務 —
        with st.expander("🧾 稅務設定"):
            dependents = st.slider("扶養人數 (不含本人)", 0, 10, 2)
            monthly_rent = st.slider("月租金 (千)", 0, 50, 18, format="%d 千")
            monthly_rent_ntd = monthly_rent * 1_000
            receive_subsidy = st.toggle("領取租金補貼", value=True)
            use_rent_deduction = not receive_subsidy
            if receive_subsidy:
                st.caption("⚠️ 領補貼時不可申報房租扣除額")

        # — 補助 —
        with st.expander("🏠 租金補助"):
            subsidy_base = st.slider("基準補貼 (月)", 0, 15_000, 5_000, 500)
            child_multiplier = st.slider("育兒加碼倍數", 1.0, 5.0, 2.0, 0.1)
            include_subsidy_in_cashflow = st.toggle("補貼計入個人現金流", value=False)
            effective_subsidy = round(subsidy_base * child_multiplier) if dependents > 0 else subsidy_base
            st.caption(f"實領：${fmt(effective_subsidy)}/月")

        # — 投資 —
        with st.expander("📈 投資設定", expanded=True):
            phase1_monthly = st.slider("前期每月投入 (萬)", 0.0, 10.0, 1.5, 0.5, format="%.1f 萬")
            phase1_monthly_ntd = round(phase1_monthly * 10_000)
            phase1_years = st.slider("前期年數", 1, max(1, years_to_go - 1), min(3, max(1, years_to_go - 1)))
            phase2_monthly = st.slider("後期每月投入 (萬)", 0.0, 10.0, 3.0, 0.5, format="%.1f 萬")
            phase2_monthly_ntd = round(phase2_monthly * 10_000)
            phase2_years = max(1, years_to_go - phase1_years)
            st.caption(f"後期自動 {phase2_years} 年（到退休）")
            annual_bonus = st.slider("年度加碼 (8月退稅)", 0, 100_000, 30_000, 5_000)
            annual_roi = st.slider(
                "預期年化報酬率", 1.0, 15.0, 7.0, 0.5,
                format="%.1f%%",
                help="台股大盤長期平均約 7-9%，保守可設 5%",
            )
            annual_roi_decimal = annual_roi / 100
            current_balance = st.number_input(
                "目前帳戶餘額", value=0, min_value=0, step=100_000,
                help="你現有的投資組合總值",
            )

        # — 開銷 —
        with st.expander("💰 每月開銷"):
            expense_rent = st.slider("房租", 0, 50_000, 18_000, 1_000)
            expense_living = st.slider("生活費", 0, 80_000, 25_000, 1_000)
            expense_insurance = st.slider("保險雜項", 0, 30_000, 10_000, 1_000)
            total_expense = expense_rent + expense_living + expense_insurance
            st.caption(f"每月開銷合計：${fmt(total_expense)}")

        # — 退休收入 —
        with st.expander("🏦 退休法定收入"):
            labor_pension = st.slider("勞保年金 (月)", 0, 50_000, 26_000, 1_000)
            labor_retirement = st.slider("勞退月領", 0, 30_000, 13_500, 500)
            st.caption(f"法定收入合計：${fmt(labor_pension + labor_retirement)}/月")

    # ── 執行模擬 ─────────────────────────────────────────────
    sim, tax_engine, subsidy_engine, invest_engine, cashflow_engine = run_simulation(
        birth_year, current_age, retirement_age, monthly_salary_ntd,
        dependents, monthly_rent_ntd, use_rent_deduction,
        subsidy_base, child_multiplier, include_subsidy_in_cashflow,
        phase1_monthly_ntd, phase1_years, phase2_monthly_ntd, phase2_years,
        annual_bonus, annual_roi_decimal, current_balance,
        expense_rent, expense_living, expense_insurance,
        labor_pension, labor_retirement,
    )

    summary = sim.retirement_summary()
    if not summary:
        st.warning("退休年齡需大於目前年齡，請調整左側參數。")
        return

    snapshots = summary["snapshots"]

    # ── 退休就緒度燈號 ───────────────────────────────────────
    ratio = summary["coverage_ratio"]
    if ratio >= 1.5:
        badge_class, badge_text, badge_desc = "badge-green", "財務自由", "被動收入遠超支出，恭喜！"
    elif ratio >= 1.0:
        badge_class, badge_text, badge_desc = "badge-yellow", "基本達標", "剛好覆蓋開銷，建議再加碼"
    else:
        badge_class, badge_text, badge_desc = "badge-red", "尚有缺口", "需提高投資或降低開銷"

    st.markdown(
        f'<span class="readiness-badge {badge_class}">{badge_text}</span>'
        f'&nbsp;&nbsp;{badge_desc}',
        unsafe_allow_html=True,
    )

    # ── KPI 指標列 ───────────────────────────────────────────
    st.markdown("")
    col1, col2, col3, col4, col5 = st.columns(5)
    monthly_tax = tax_engine.monthly_tax(monthly_salary_ntd)
    current_invest = invest_engine.monthly_contribution_at_year(0)

    with col1:
        surplus = cashflow_engine.monthly_surplus(
            monthly_salary_ntd, monthly_tax, current_invest,
            subsidy_engine.cashflow_contribution(),
        )
        st.metric("每月結餘", f"${fmt(surplus)}")
    with col2:
        st.metric("年繳所得稅", f"${fmt(tax_engine.compute_tax(monthly_salary_ntd * 12))}")
    with col3:
        st.metric(f"{retirement_age} 歲總資產", f"${fmt(summary['final_portfolio'])}")
    with col4:
        st.metric("退休月被動收入", f"${fmt(summary['total_monthly_passive_income'])}")
    with col5:
        st.metric("開銷覆蓋率", f"{ratio:.1f} 倍")

    # ── 主要圖表區 ───────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 資產成長曲線",
        "🔬 壓力測試",
        "📋 年度明細",
        "🧮 退休收入拆解",
        "📊 股票持倉",
    ])

    # ── Tab 1: 資產成長 ──────────────────────────────────────
    with tab1:
        ages = [s.age for s in snapshots]
        portfolios = [s.year_end_portfolio for s in snapshots]
        contributions_cumulative = []
        cum = current_balance
        for s in snapshots:
            cum += s.annual_investment_contribution
            contributions_cumulative.append(cum)

        fig = go.Figure()

        # 累計投入 (面積)
        fig.add_trace(go.Scatter(
            x=ages, y=contributions_cumulative,
            mode="lines",
            name="累計投入本金",
            fill="tozeroy",
            fillcolor="rgba(99, 110, 250, 0.1)",
            line=dict(color="rgba(99, 110, 250, 0.4)", width=1, dash="dot"),
            hovertemplate="年齡: %{x} 歲<br>累計投入: $%{y:,.0f}<extra></extra>",
        ))

        # 資產曲線
        fig.add_trace(go.Scatter(
            x=ages, y=portfolios,
            mode="lines+markers",
            name="投資組合總值",
            line=dict(color="#636EFA", width=3),
            marker=dict(size=7),
            hovertemplate="年齡: %{x} 歲<br>總資產: $%{y:,.0f}<extra></extra>",
        ))

        # 里程碑標記
        milestones = [100, 300, 500, 1000]
        for m in milestones:
            target = m * 10_000
            if portfolios[-1] >= target >= portfolios[0]:
                fig.add_hline(
                    y=target, line_dash="dash", line_color="#aaa", line_width=1,
                    annotation_text=f"{m} 萬", annotation_position="top left",
                    annotation_font_color="#888",
                )

        fig.update_layout(
            xaxis_title="年齡",
            yaxis_title="金額 (NTD)",
            yaxis_tickformat=",",
            height=450,
            margin=dict(l=20, r=20, t=10, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

        # 投資成長洞察
        if len(portfolios) > 1:
            final = portfolios[-1]
            total_contrib = contributions_cumulative[-1]
            total_growth = final - total_contrib
            growth_pct = (total_growth / total_contrib * 100) if total_contrib > 0 else 0
            ic1, ic2, ic3 = st.columns(3)
            with ic1:
                st.metric("累計投入本金", f"${fmt(total_contrib)}")
            with ic2:
                st.metric("投資增值", f"${fmt(total_growth)}", f"+{growth_pct:.0f}%")
            with ic3:
                st.metric("複利效果倍數", f"{final / total_contrib:.2f}x" if total_contrib > 0 else "N/A")

    # ── Tab 2: 壓力測試 ──────────────────────────────────────
    with tab2:
        st.markdown("#### 不同報酬率情境下的退休資產")
        st.caption("如果市場表現不如預期，你的退休金會怎樣？")

        test_rois = [0.03, 0.05, 0.07, 0.09, 0.11]
        stress_fig = go.Figure()

        colors = ["#EF553B", "#FFA15A", "#636EFA", "#00CC96", "#AB63FA"]
        stress_results = []

        for roi, color in zip(test_rois, colors):
            test_sim, *_ = run_simulation(
                birth_year, current_age, retirement_age, monthly_salary_ntd,
                dependents, monthly_rent_ntd, use_rent_deduction,
                subsidy_base, child_multiplier, include_subsidy_in_cashflow,
                phase1_monthly_ntd, phase1_years, phase2_monthly_ntd, phase2_years,
                annual_bonus, roi, current_balance,
                expense_rent, expense_living, expense_insurance,
                labor_pension, labor_retirement,
            )
            test_summary = test_sim.retirement_summary()
            if not test_summary:
                continue
            test_snapshots = test_summary["snapshots"]
            test_ages = [s.age for s in test_snapshots]
            test_portfolios = [s.year_end_portfolio for s in test_snapshots]

            is_current = abs(roi - annual_roi_decimal) < 0.001
            stress_fig.add_trace(go.Scatter(
                x=test_ages, y=test_portfolios,
                mode="lines+markers" if is_current else "lines",
                name=f"ROI {roi*100:.0f}%" + (" ← 你的設定" if is_current else ""),
                line=dict(color=color, width=4 if is_current else 2),
                marker=dict(size=6) if is_current else dict(size=0),
                hovertemplate=f"ROI {roi*100:.0f}%<br>年齡: %{{x}} 歲<br>資產: $%{{y:,.0f}}<extra></extra>",
            ))

            final_portfolio = test_summary["final_portfolio"]
            passive = test_summary["total_monthly_passive_income"]
            stress_results.append({
                "報酬率": f"{roi*100:.0f}%",
                "退休資產": fmt(final_portfolio),
                "月被動收入": fmt(passive),
                "覆蓋率": f"{test_summary['coverage_ratio']:.1f}x",
            })

        stress_fig.update_layout(
            xaxis_title="年齡",
            yaxis_title="資產 (NTD)",
            yaxis_tickformat=",",
            height=450,
            margin=dict(l=20, r=20, t=10, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified",
        )
        st.plotly_chart(stress_fig, use_container_width=True)

        # 壓力測試摘要表
        st.dataframe(
            pd.DataFrame(stress_results),
            use_container_width=True,
            hide_index=True,
        )

    # ── Tab 3: 年度明細 ──────────────────────────────────────
    with tab3:
        df = pd.DataFrame([
            {
                "年齡": s.age,
                "西元年": s.year,
                "年收入": s.gross_annual_income,
                "年稅額": s.annual_tax,
                "年投資額": s.annual_investment_contribution,
                "年開銷": s.annual_expenses,
                "年末資產": s.year_end_portfolio,
                "月結餘": s.monthly_surplus,
            }
            for s in snapshots
        ])
        st.dataframe(
            df.style.format({
                "年收入": "${:,.0f}",
                "年稅額": "${:,.0f}",
                "年投資額": "${:,.0f}",
                "年開銷": "${:,.0f}",
                "年末資產": "${:,.0f}",
                "月結餘": "${:,.0f}",
            }).background_gradient(subset=["年末資產"], cmap="Blues"),
            use_container_width=True,
            hide_index=True,
            height=530,
        )

    # ── Tab 4: 退休收入拆解 ──────────────────────────────────
    with tab4:
        rcol1, rcol2 = st.columns([1, 1])

        with rcol1:
            st.markdown("#### 退休每月收入來源")
            income_sources = {
                "投資提領 (4% SWR)": summary["portfolio_monthly_withdrawal"],
                "勞保年金": summary["labor_insurance_pension"],
                "勞退月領": summary["labor_retirement_monthly"],
            }

            bar_fig = go.Figure()
            bar_colors = ["#636EFA", "#EF553B", "#00CC96"]
            for (label, value), color in zip(income_sources.items(), bar_colors):
                bar_fig.add_trace(go.Bar(
                    x=[value], y=[label], orientation="h",
                    name=label,
                    marker_color=color,
                    text=[f"${fmt(value)}"],
                    textposition="auto",
                    hovertemplate=f"{label}: $%{{x:,.0f}}<extra></extra>",
                ))
            bar_fig.add_vline(
                x=summary["monthly_expenses"],
                line_dash="dash", line_color="red", line_width=2,
                annotation_text=f"每月開銷 ${fmt(summary['monthly_expenses'])}",
                annotation_position="top",
            )
            bar_fig.update_layout(
                showlegend=False,
                height=250,
                margin=dict(l=20, r=20, t=10, b=20),
                xaxis_title="金額 (NTD/月)",
                xaxis_tickformat=",",
                barmode="stack",
            )
            st.plotly_chart(bar_fig, use_container_width=True)

            # 退休數字摘要
            total_passive = summary["total_monthly_passive_income"]
            expenses = summary["monthly_expenses"]
            net = total_passive - expenses

            if net >= 0:
                st.success(
                    f"每月被動收入 **${fmt(total_passive)}** "
                    f"- 開銷 **${fmt(expenses)}** "
                    f"= 每月盈餘 **${fmt(net)}**"
                )
            else:
                st.error(
                    f"每月被動收入 **${fmt(total_passive)}** "
                    f"- 開銷 **${fmt(expenses)}** "
                    f"= 每月缺口 **${fmt(abs(net))}**"
                )

        with rcol2:
            st.markdown("#### 目前每月薪資分配")
            expenses_breakdown = cashflow_engine.expense_breakdown()
            surplus_now = cashflow_engine.monthly_surplus(
                monthly_salary_ntd, monthly_tax, current_invest,
                subsidy_engine.cashflow_contribution(),
            )

            pie_labels = ["所得稅", "投資", *expenses_breakdown.keys(), "結餘"]
            pie_values = [monthly_tax, current_invest, *expenses_breakdown.values(), max(0, surplus_now)]
            pie_colors = ["#EF553B", "#636EFA", "#FFA15A", "#00CC96", "#AB63FA", "#19D3F3"]

            pie_fig = go.Figure(data=[go.Pie(
                labels=pie_labels, values=pie_values,
                hole=0.45,
                textinfo="label+percent",
                textfont_size=12,
                marker=dict(colors=pie_colors[:len(pie_labels)]),
                hovertemplate="%{label}: $%{value:,.0f} (%{percent})<extra></extra>",
            )])
            pie_fig.update_layout(
                height=350,
                margin=dict(l=10, r=10, t=10, b=10),
                showlegend=False,
            )
            st.plotly_chart(pie_fig, use_container_width=True)

            # 薪資配置建議
            invest_pct = current_invest / monthly_salary_ntd * 100
            if invest_pct < 20:
                st.info(f"目前投資占薪資 {invest_pct:.0f}%，建議提高到 20% 以上加速累積")
            elif invest_pct < 30:
                st.success(f"投資占薪資 {invest_pct:.0f}%，配置合理！")
            else:
                st.success(f"投資占薪資 {invest_pct:.0f}%，積極配置，注意保留緊急備用金")

    # ── Tab 5: 股票持倉 ─────────────────────────────────────
    with tab5:
        st.markdown("#### 我的股票持倉")
        st.caption("輸入你持有的股票，自動抓取即時股價計算市值。台股代號加 .TW（例：2330.TW），美股直接輸入（例：AAPL）")

        # 持股輸入區
        if "stock_holdings" not in st.session_state:
            st.session_state.stock_holdings = []

        with st.expander("新增股票", expanded=True):
            scol1, scol2, scol3, scol4 = st.columns([2, 1, 1, 1])
            with scol1:
                new_symbol = st.text_input("股票代號", placeholder="例: 2330.TW", key="new_symbol")
            with scol2:
                new_shares = st.number_input("持有股數", min_value=0.0, value=0.0, step=1.0, key="new_shares")
            with scol3:
                new_cost = st.number_input("買入均價", min_value=0.0, value=0.0, step=1.0, key="new_cost")
            with scol4:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("新增", type="primary", use_container_width=True):
                    if new_symbol.strip() and new_shares > 0:
                        st.session_state.stock_holdings.append({
                            "symbol": new_symbol.strip().upper(),
                            "shares": new_shares,
                            "cost": new_cost,
                        })
                        st.rerun()

        # 顯示已輸入的持股清單 & 允許刪除
        if st.session_state.stock_holdings:
            holdings_df = pd.DataFrame(st.session_state.stock_holdings)
            holdings_df.columns = ["股票代號", "持有股數", "買入均價"]

            ecol1, ecol2 = st.columns([3, 1])
            with ecol1:
                st.dataframe(holdings_df, use_container_width=True, hide_index=True)
            with ecol2:
                delete_idx = st.selectbox(
                    "選擇要刪除的股票",
                    options=range(len(st.session_state.stock_holdings)),
                    format_func=lambda i: st.session_state.stock_holdings[i]["symbol"],
                    key="delete_stock_idx",
                )
                if st.button("刪除選取", type="secondary"):
                    st.session_state.stock_holdings.pop(delete_idx)
                    st.rerun()

            # 建立 StockEngine 並抓取報價
            stock_engine = StockEngine([
                StockHolding(
                    symbol=h["symbol"],
                    shares=h["shares"],
                    cost_per_share=h["cost"],
                )
                for h in st.session_state.stock_holdings
            ])

            with st.spinner("正在抓取即時股價..."):
                quotes = stock_engine.fetch_quotes()

            if quotes:
                positions = stock_engine.get_positions()
                if positions:
                    # KPI
                    total_mv = stock_engine.total_market_value()
                    total_pl = stock_engine.total_profit_loss()
                    total_cost = sum(p.cost_basis for p in positions)
                    total_pl_pct = (total_pl / total_cost * 100) if total_cost > 0 else 0

                    sk1, sk2, sk3 = st.columns(3)
                    with sk1:
                        st.metric("持倉總市值", f"${fmt(total_mv)}")
                    with sk2:
                        st.metric("總損益", f"${fmt(total_pl)}", f"{total_pl_pct:+.1f}%")
                    with sk3:
                        st.metric(
                            "佔退休目標比例",
                            f"{total_mv / summary['final_portfolio'] * 100:.1f}%"
                            if summary["final_portfolio"] > 0 else "N/A",
                        )

                    # 持倉明細表
                    pos_data = []
                    for p in positions:
                        pos_data.append({
                            "股票": f"{p.symbol} ({p.name})",
                            "股數": p.shares,
                            "現價": p.price,
                            "市值": p.market_value,
                            "成本": p.cost_basis,
                            "損益": p.profit_loss,
                            "損益率": f"{p.profit_loss_pct:+.1f}%",
                            "今日漲跌": f"{p.change_pct:+.1f}%",
                        })

                    pos_df = pd.DataFrame(pos_data)
                    st.dataframe(
                        pos_df.style.format({
                            "股數": "{:,.0f}",
                            "現價": "${:,.2f}",
                            "市值": "${:,.0f}",
                            "成本": "${:,.0f}",
                            "損益": "${:,.0f}",
                        }),
                        use_container_width=True,
                        hide_index=True,
                    )

                    # 持倉圓餅圖
                    if len(positions) > 1:
                        stock_pie = go.Figure(data=[go.Pie(
                            labels=[p.symbol for p in positions],
                            values=[p.market_value for p in positions],
                            hole=0.4,
                            textinfo="label+percent",
                            hovertemplate="%{label}: $%{value:,.0f} (%{percent})<extra></extra>",
                        )])
                        stock_pie.update_layout(
                            title="持倉分布",
                            height=350,
                            margin=dict(l=10, r=10, t=40, b=10),
                        )
                        st.plotly_chart(stock_pie, use_container_width=True)

                    # 提示：將股票市值加入投資餘額
                    st.info(
                        f"提示：你的股票持倉市值為 **${fmt(total_mv)}**。"
                        f"如果要納入退休試算，可以將左側「目前帳戶餘額」設為 **${fmt(current_balance + total_mv)}**"
                    )
                else:
                    st.warning("無法取得報價，請確認股票代號是否正確。")
            else:
                st.warning("無法連線至 Yahoo Finance，請稍後再試。你也可以繼續使用其他功能。")
        else:
            st.info("尚未新增任何股票。點擊上方「新增」按鈕開始建立你的持倉清單。")

    # ── 底部小白指南 ─────────────────────────────────────────
    st.divider()
    with st.expander("💡 新手指南：看不懂？點這裡", expanded=False):
        st.markdown("""
        **怎麼用這個工具？**

        1. **左邊側邊欄**：調整你的個人參數（薪水、開銷、投資金額等）
        2. **上方燈號**：綠色 = 安全、黃色 = 剛好、紅色 = 要加油
        3. **四個分頁**：點擊切換看不同分析

        ---

        **關鍵名詞解釋：**

        | 名詞 | 意思 |
        |------|------|
        | **年化報酬率 (ROI)** | 投資每年平均賺多少 %。台股長期約 7-9%，保守用 5% |
        | **4% 安全提領率 (SWR)** | 退休後每年從投資帳戶提領 4%，統計上可撐 30 年不用完 |
        | **覆蓋率** | 被動收入 / 每月開銷。> 1 倍代表收入夠用 |
        | **勞保年金** | 政府每月發的退休金，依你的投保年資與薪資計算 |
        | **勞退月領** | 雇主每月幫你提撥 6% 到個人帳戶，退休後分期領回 |
        | **壓力測試** | 模擬最壞情況：如果投資報酬率只有 3%，你的錢夠嗎？ |
        | **股票持倉** | 輸入你買的股票，自動算出總市值和損益 |

        ---

        **快速建議：**
        - 每月至少投資薪水的 **20%**
        - 壓力測試的 **3% 情境**如果也是綠燈，你就很安全了
        - 側邊欄的參數隨便拉，不會壞掉，多玩幾次就懂了！
        """)


if __name__ == "__main__":
    main()
