import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from screener import fetch_ticker_info, passes_filters
from dcf import fetch_financials, build_historical_table, calc_wacc, project_fcf, terminal_value, intrinsic_price, RISK_FREE_RATE, RISK_FREE_SOURCE

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DCF Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap');

:root {
    --bg:       #0a0c10;
    --bg2:      #111318;
    --bg3:      #1a1d24;
    --border:   #252830;
    --accent:   #00e5a0;
    --accent2:  #0077ff;
    --warn:     #ff4d6d;
    --text:     #e8eaf0;
    --muted:    #6b7280;
    --pass:     #00e5a0;
    --fail:     #ff4d6d;
}

html, body, [class*="css"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Syne', sans-serif;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: var(--bg2) !important;
    border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] * { color: var(--text) !important; }

/* Headers */
h1, h2, h3 { font-family: 'Syne', sans-serif !important; font-weight: 800 !important; }
h1 { font-size: 2rem !important; letter-spacing: -0.03em; }

/* Metric cards */
[data-testid="metric-container"] {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem !important;
}
[data-testid="stMetricValue"] { font-family: 'Space Mono', monospace !important; font-size: 1.4rem !important; }
[data-testid="stMetricLabel"] { color: var(--muted) !important; font-size: 0.75rem !important; letter-spacing: 0.05em; text-transform: uppercase; }
[data-testid="stMetricDelta"] svg { display: none; }

/* Tabs */
button[data-baseweb="tab"] {
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.03em;
    color: var(--muted) !important;
    background: transparent !important;
    border-bottom: 2px solid transparent !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
}
[data-testid="stTabPanel"] { padding-top: 1.5rem; }

/* Inputs */
input, textarea, select, [data-baseweb="input"] input {
    background: var(--bg3) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 6px !important;
    font-family: 'Space Mono', monospace !important;
}
[data-baseweb="select"] > div {
    background: var(--bg3) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
}

/* Buttons */
button[kind="primary"], [data-testid="stButton"] > button {
    background: var(--accent) !important;
    color: #000 !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 6px !important;
    letter-spacing: 0.05em;
    transition: opacity 0.15s;
}
button[kind="primary"]:hover, [data-testid="stButton"] > button:hover { opacity: 0.85 !important; }

/* Number inputs */
[data-testid="stNumberInput"] input { font-family: 'Space Mono', monospace !important; }

/* Slider */
[data-testid="stSlider"] { accent-color: var(--accent); }

/* DataFrame */
[data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }

/* Divider */
hr { border-color: var(--border) !important; }

/* Pass/Fail badges */
.badge-pass {
    background: rgba(0,229,160,0.12);
    color: #00e5a0;
    border: 1px solid rgba(0,229,160,0.3);
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 700;
    font-family: 'Space Mono', monospace;
    letter-spacing: 0.05em;
}
.badge-fail {
    background: rgba(255,77,109,0.12);
    color: #ff4d6d;
    border: 1px solid rgba(255,77,109,0.3);
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 700;
    font-family: 'Space Mono', monospace;
    letter-spacing: 0.05em;
}
.section-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 0.5rem;
}
.ticker-header {
    font-family: 'Space Mono', monospace;
    font-size: 0.85rem;
    color: var(--muted);
}
.stAlert { border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Space Mono, monospace", color="#e8eaf0", size=11),
    margin=dict(l=10, r=10, t=40, b=10),
    xaxis=dict(gridcolor="#252830", showline=False, zeroline=False),
    yaxis=dict(gridcolor="#252830", showline=False, zeroline=False),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#252830"),
)
ACCENT   = "#00e5a0"
ACCENT2  = "#0077ff"
WARN     = "#ff4d6d"
AMBER    = "#f59e0b"

# ─── Helpers ──────────────────────────────────────────────────────────────────
def fmt_b(v):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "—"
    if abs(v) >= 1e9: return f"${v/1e9:,.1f}B"
    if abs(v) >= 1e6: return f"${v/1e6:,.0f}M"
    return f"${v:,.0f}"

def fmt_pct(v):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "—"
    return f"{v*100:+.1f}%"

def fmt_x(v, decimals=2):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "—"
    return f"{v:.{decimals}f}x"

def color_margin(m):
    if m > 20:  return ACCENT
    if m < -20: return WARN
    return AMBER

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 DCF Analyzer")
    st.markdown('<div class="section-label">Ticker</div>', unsafe_allow_html=True)
    ticker_input = st.text_input("", placeholder="AAPL, MSFT, ADBE…", label_visibility="collapsed")
    analyze_btn  = st.button("Analyze →", use_container_width=True)

    st.divider()
    st.markdown('<div class="section-label">DCF Parameters</div>', unsafe_allow_html=True)

    use_manual_growth = st.toggle("Manual Growth Rate", value=False)
    manual_growth = st.number_input("FCF Growth Rate (%)", min_value=-30.0, max_value=50.0, value=8.0, step=0.5,
                                    disabled=not use_manual_growth,
                                    help="Solo aplica si activaste el toggle")

    use_manual_wacc = st.toggle("Manual WACC", value=False)
    manual_wacc = st.number_input("WACC (%)", min_value=1.0, max_value=30.0, value=9.0, step=0.25,
                                  disabled=not use_manual_wacc,
                                  help="Solo aplica si activaste el toggle")

    st.divider()
    st.markdown('<div class="section-label">Screener Filters</div>', unsafe_allow_html=True)
    with st.expander("Edit filters", expanded=False):
        f_max_pe    = st.number_input("Max P/E",            value=25.0,  step=1.0)
        f_max_pb    = st.number_input("Max P/B",            value=4.0,  step=0.5)
        f_max_eveb  = st.number_input("Max EV/EBITDA",      value=12.0,  step=1.0)
        f_min_pm    = st.number_input("Min Profit Margin %", value=10.0,  step=1.0)
        f_min_roe   = st.number_input("Min ROE %",           value=13.0, step=1.0)
        f_min_roa   = st.number_input("Min ROA %",           value=5.0,  step=0.5)
        f_min_rev_g = st.number_input("Min Revenue Growth %",value=7.0,  step=1.0)
        f_min_ear_g = st.number_input("Min Earnings Growth %",value=8.0, step=1.0)
        f_max_de    = st.number_input("Max Debt/Equity",     value=1.5,  step=0.1)


# ─── Session state ─────────────────────────────────────────────────────────────
if "data" not in st.session_state:
    st.session_state.data = None

# ─── Main area ────────────────────────────────────────────────────────────────
if not ticker_input or not analyze_btn:
    # Landing
    st.markdown("# Stock Screener & DCF Analyzer")
    st.markdown("##### Enter a ticker in the sidebar and click **Analyze →**")
    st.divider()
    cols = st.columns(4)
    items = [
        ("🔍", "Screener", "Valuation, profitability & growth filters"),
        ("📊", "Financials", "5-year income, cash flow & balance history"),
        ("💹", "DCF Model", "10-year intrinsic value with margin of safety"),
        ("🎛️", "Sensitivity", "WACC × Growth rate scenario matrix"),
    ]
    for col, (icon, title, desc) in zip(cols, items):
        col.markdown(f"**{icon} {title}**\n\n{desc}")
    st.stop()

# ─── Fetch data ────────────────────────────────────────────────────────────────
ticker = ticker_input.strip().upper()

with st.spinner(f"Fetching data for {ticker}…"):
    try:
        row = fetch_ticker_info(ticker)
        if row is None:
            st.error(f"No data found for **{ticker}**. Check the ticker symbol.")
            st.stop()

        filters = dict(
            MAX_PE_RATIO=f_max_pe, MAX_PB_RATIO=f_max_pb, MAX_EV_EBITDA=f_max_eveb,
            MIN_PROFIT_MARGIN=f_min_pm/100, MIN_ROE=f_min_roe/100, MIN_ROA=f_min_roa/100,
            MIN_REVENUE_GROWTH=f_min_rev_g/100, MIN_EARNINGS_GROWTH=f_min_ear_g/100,
            MAX_DEBT_TO_EQUITY=f_max_de,
        )
        passed, failures = passes_filters(row, filters)

        (income, cashflow, balance), info = fetch_financials(ticker)
        hist      = build_historical_table(income, cashflow, balance)
        wacc_calc = calc_wacc(info, balance, income)

        st.session_state.data = dict(
            row=row, passed=passed, failures=failures,
            hist=hist, wacc_calc=wacc_calc, info=info,
            balance=balance, income=income,
        )
    except Exception as e:
        st.error(f"Error fetching **{ticker}**: {e}")
        st.stop()

d = st.session_state.data
row, passed, failures = d["row"], d["passed"], d["failures"]
hist, wacc_calc, info  = d["hist"], d["wacc_calc"], d["info"]

# ─── Header ────────────────────────────────────────────────────────────────────
name   = info.get("longName", ticker)
sector = info.get("sector", "—")
price  = row.get("price") or 0.0
shares = info.get("sharesOutstanding", 1)

badge = '<span class="badge-pass">PASS</span>' if passed else '<span class="badge-fail">FAIL</span>'
st.markdown(f"## {ticker} &nbsp; {badge}", unsafe_allow_html=True)
st.markdown(f'<div class="ticker-header">{name} &nbsp;·&nbsp; {sector}</div>', unsafe_allow_html=True)
st.divider()

# ─── KPI row ───────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Price",         f"${price:,.2f}")
k2.metric("Market Cap",    fmt_b(row.get("market_cap")))
k3.metric("P/E Ratio",     f"{row.get('pe_ratio'):.1f}x" if row.get("pe_ratio") else "—")
k4.metric("P/B Ratio",     f"{row.get('pb_ratio'):.2f}x" if row.get("pb_ratio") else "—")
k5.metric("ROE",           fmt_pct(row.get("roe")))
k6.metric("Profit Margin", fmt_pct(row.get("profit_margin")))

st.divider()

# ─── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["🔍 Screener", "📊 Financials", "💹 DCF Model", "🎛️ Sensitivity"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — SCREENER
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    col_l, col_r = st.columns([1, 1], gap="large")

    with col_l:
        st.markdown("#### Screener Result")
        status_color = "#00e5a0" if passed else "#ff4d6d"
        status_text  = "✓ Passed all filters" if passed else f"✗ Failed {len(failures)} filter(s)"
        st.markdown(f'<div style="color:{status_color};font-family:Space Mono,monospace;font-size:1rem;font-weight:700;margin-bottom:1rem">{status_text}</div>', unsafe_allow_html=True)

        if not passed and failures:
            st.markdown("**Filters failed:**")
            for f in failures:
                st.markdown(f'<div style="color:#ff4d6d;font-family:Space Mono,monospace;font-size:0.8rem;margin:2px 0">✗ {f}</div>', unsafe_allow_html=True)

    with col_r:
        st.markdown("#### All Metrics")
        metrics_data = {
            "Metric": ["Price", "Market Cap", "P/E Ratio", "P/B Ratio", "EV/EBITDA",
                       "Profit Margin", "ROE", "ROA", "Revenue Growth",
                       "Earnings Growth", "Dividend Yield", "Debt/Equity"],
            "Value": [
                f"${row.get('price'):,.2f}" if row.get("price") else "—",
                fmt_b(row.get("market_cap")),
                f"{row.get('pe_ratio'):.2f}" if row.get("pe_ratio") else "—",
                f"{row.get('pb_ratio'):.2f}" if row.get("pb_ratio") else "—",
                f"{row.get('ev_ebitda'):.2f}" if row.get("ev_ebitda") else "—",
                fmt_pct(row.get("profit_margin")),
                fmt_pct(row.get("roe")),
                fmt_pct(row.get("roa")),
                fmt_pct(row.get("revenue_growth")),
                fmt_pct(row.get("earnings_growth")),
                fmt_pct(row.get("dividend_yield")),
                f"{row.get('debt_to_equity'):.2f}" if row.get("debt_to_equity") else "—",
            ],
        }
        st.dataframe(pd.DataFrame(metrics_data), hide_index=True, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — FINANCIALS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    if hist.empty:
        st.warning("No historical financial data available.")
    else:
        # ── Revenue & Net Income bar chart ────────────────────────────────────
        st.markdown("#### Revenue & Net Income (USD Billions)")
        years = hist.index.astype(str).tolist()
        fig = go.Figure()
        if "Revenue" in hist.columns:
            fig.add_trace(go.Bar(
                x=years, y=hist["Revenue"]/1e9, name="Revenue",
                marker_color=ACCENT2, opacity=0.85,
            ))
        if "Net_Income" in hist.columns:
            fig.add_trace(go.Bar(
                x=years, y=hist["Net_Income"]/1e9, name="Net Income",
                marker_color=ACCENT, opacity=0.9,
            ))
        _layout1 = {**PLOTLY_LAYOUT, "legend": dict(orientation="h", y=1.1)}
        fig.update_layout(**_layout1, barmode="group", height=300,
                          yaxis_title="USD Billions")
        st.plotly_chart(fig, use_container_width=True)

        # ── FCF chart ─────────────────────────────────────────────────────────
        if "FCF" in hist.columns and "Op_CF" in hist.columns:
            st.markdown("#### Free Cash Flow vs Operating Cash Flow (USD Billions)")
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=years, y=hist["Op_CF"]/1e9, name="Operating CF",
                marker_color=ACCENT2, opacity=0.7,
            ))
            fig2.add_trace(go.Scatter(
                x=years, y=hist["FCF"]/1e9, name="FCF",
                mode="lines+markers",
                line=dict(color=ACCENT, width=2.5),
                marker=dict(size=8, color=ACCENT),
            ))
            _layout2 = {**PLOTLY_LAYOUT, "legend": dict(orientation="h", y=1.1)}
            fig2.update_layout(**_layout2, height=280,
                               yaxis_title="USD Billions")
            st.plotly_chart(fig2, use_container_width=True)

        # ── YoY Growth heatmap-style table ────────────────────────────────────
        st.markdown("#### Year-over-Year Growth (%)")
        yoy_cols = [c for c in ["Revenue_YoY%", "Op_Income_YoY%", "Net_Income_YoY%", "FCF_YoY%"] if c in hist.columns]
        if yoy_cols:
            yoy_df = hist[yoy_cols].copy()
            yoy_df.columns = [c.replace("_YoY%", "") for c in yoy_cols]
            yoy_df = yoy_df.map(lambda x: f"{x:+.1f}%" if pd.notna(x) else "—")
            st.dataframe(yoy_df, use_container_width=True)

        # ── Balance table ─────────────────────────────────────────────────────
        st.markdown("#### Balance Sheet Summary (USD Billions)")
        bal_cols = [c for c in ["Debt", "Cash", "Equity"] if c in hist.columns]
        if bal_cols:
            bal_df = hist[bal_cols].copy()
            for c in bal_df.columns:
                bal_df[c] = bal_df[c].map(lambda x: f"${x/1e9:,.2f}B" if pd.notna(x) else "—")
            st.dataframe(bal_df, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — DCF MODEL
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    fcf_series = hist["FCF"].dropna() if "FCF" in hist.columns else pd.Series(dtype=float)
    base_fcf   = fcf_series.tail(3).mean() if len(fcf_series) >= 2 else None

    if base_fcf is None or base_fcf <= 0:
        st.warning("Insufficient or negative FCF history — DCF not available.")
    else:
        # ── Interactive parameter sliders ─────────────────────────────────────
        st.markdown("#### DCF Parameters")
        hist_growth = (
            hist["FCF_YoY%"].dropna().tail(3).mean() / 100
            if "FCF_YoY%" in hist.columns else 0.08
        )
        hist_growth = min(max(hist_growth, -0.30), 0.40)

        pc1, pc2, pc3 = st.columns(3)
        with pc1:
            if use_manual_growth:
                growth_used = manual_growth / 100
                st.metric("FCF Growth Rate", f"{growth_used*100:.1f}%", "manual")
            else:
                growth_pct = st.slider(
                    "FCF Growth Rate (%)",
                    min_value=-20.0, max_value=40.0,
                    value=round(hist_growth * 100, 1), step=0.5,
                )
                growth_used = growth_pct / 100
        with pc2:
            if use_manual_wacc:
                wacc_used = manual_wacc / 100
                st.metric("WACC", f"{wacc_used*100:.2f}%", "manual")
            else:
                wacc_pct = st.slider(
                    "WACC (%)",
                    min_value=3.0, max_value=20.0,
                    value=round(wacc_calc * 100, 2), step=0.25,
                )
                wacc_used = wacc_pct / 100
        with pc3:
            perp_growth_pct = st.slider("Perpetual Growth (%)", min_value=1.0, max_value=4.0, value=2.5, step=0.1)
            perp_growth = perp_growth_pct / 100
        rf1, rf2, rf3 = st.columns(3)
        with rf1:
            st.metric("Risk-Free Rate", f"{RISK_FREE_RATE*100:.2f}%", RISK_FREE_SOURCE)

        # Net cash
        last_row = hist.iloc[-1]
        c_val  = last_row.get("Cash", 0) or 0
        d_val  = last_row.get("Debt", 0) or 0
        net_cash = (0 if (isinstance(c_val, float) and np.isnan(c_val)) else c_val) \
                 - (0 if (isinstance(d_val, float) and np.isnan(d_val)) else d_val)

        fcfs_5  = project_fcf(base_fcf, growth_used, 5)
        fcfs_10 = project_fcf(base_fcf, growth_used, 10)
        tv_5    = terminal_value(fcfs_5[-1],  wacc_used, perp_growth)
        tv_10   = terminal_value(fcfs_10[-1], wacc_used, perp_growth)
        price_5  = intrinsic_price(fcfs_5,  tv_5,  wacc_used, net_cash, shares)
        price_10 = intrinsic_price(fcfs_10, tv_10, wacc_used, net_cash, shares)
        margin_5  = (price_5  - price) / price * 100 if price else 0
        margin_10 = (price_10 - price) / price * 100 if price else 0

        st.divider()

        # ── Valuation result cards ────────────────────────────────────────────
        st.markdown("#### Intrinsic Value vs Current Price")
        vc1, vc2, vc3 = st.columns(3)
        vc1.metric("Current Price",       f"${price:,.2f}")
        vc2.metric("Intrinsic Value (5yr)", f"${price_5:,.2f}", f"{margin_5:+.1f}%")
        vc3.metric("Intrinsic Value (10yr)",f"${price_10:,.2f}", f"{margin_10:+.1f}%")

        st.divider()

        # ── FCF Projection chart ──────────────────────────────────────────────
        st.markdown("#### Projected FCF — 10 Years")
        proj_years = [f"Y{i}" for i in range(1, 11)]
        pvs = [f / (1 + wacc_used) ** i for i, f in enumerate(fcfs_10, 1)]
        fig3 = go.Figure()
        fig3.add_trace(go.Bar(
            x=proj_years, y=[f/1e9 for f in fcfs_10], name="Projected FCF",
            marker_color=ACCENT2, opacity=0.8,
        ))
        fig3.add_trace(go.Scatter(
            x=proj_years, y=[p/1e9 for p in pvs], name="PV (discounted)",
            mode="lines+markers", line=dict(color=ACCENT, width=2.5),
            marker=dict(size=7),
        ))
        _layout3 = {**PLOTLY_LAYOUT, "legend": dict(orientation="h", y=1.1)}
        fig3.update_layout(**_layout3, height=300,
                           yaxis_title="USD Billions")
        st.plotly_chart(fig3, use_container_width=True)

        # ── Margin of safety gauge ────────────────────────────────────────────
        st.markdown("#### Margin of Safety")
        gc1, gc2 = st.columns(2)
        for col, label, margin, p_intr in [
            (gc1, "5-Year Horizon", margin_5, price_5),
            (gc2, "10-Year Horizon", margin_10, price_10),
        ]:
            bar_color = color_margin(margin)
            verdict   = "UNDERVALUED" if margin > 20 else ("OVERVALUED" if margin < -20 else "FAIR VALUE")
            col.markdown(f"**{label}**")
            fig_g = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=margin,
                delta={"reference": 0, "valueformat": ".1f", "suffix": "%"},
                number={"suffix": "%", "valueformat": ".1f",
                        "font": {"family": "Space Mono", "color": bar_color}},
                gauge={
                    "axis": {"range": [-100, 100], "tickfont": {"family": "Space Mono", "size": 10}},
                    "bar": {"color": bar_color},
                    "bgcolor": "#1a1d24",
                    "bordercolor": "#252830",
                    "steps": [
                        {"range": [-100, -20], "color": "rgba(255,77,109,0.15)"},
                        {"range": [-20, 20],   "color": "rgba(245,158,11,0.10)"},
                        {"range": [20, 100],   "color": "rgba(0,229,160,0.15)"},
                    ],
                    "threshold": {"line": {"color": "white", "width": 2}, "thickness": 0.8, "value": 0},
                },
                title={"text": verdict, "font": {"family": "Syne", "color": bar_color, "size": 13}},
            ))
            fig_g.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", height=220,
                margin=dict(l=20, r=20, t=30, b=10),
                font=dict(color="#e8eaf0"),
            )
            col.plotly_chart(fig_g, use_container_width=True)

        # ── Detailed projection table ─────────────────────────────────────────
        st.markdown("#### Year-by-Year DCF Table")
        tbl_rows = []
        for i, (f, pv) in enumerate(zip(fcfs_10, pvs), 1):
            tbl_rows.append({
                "Year": f"Y{i}",
                "Projected FCF": fmt_b(f),
                "PV (discounted)": fmt_b(pv),
                "Cumulative PV": fmt_b(sum(pvs[:i])),
            })
        st.dataframe(pd.DataFrame(tbl_rows), hide_index=True, use_container_width=True)

        # ── TV breakdown ──────────────────────────────────────────────────────
        pv_fcfs_10 = sum(pvs)
        pv_tv_10   = tv_10 / (1 + wacc_used) ** 10
        total_eq   = pv_fcfs_10 + pv_tv_10 + net_cash
        fig_pie = go.Figure(go.Pie(
            labels=["PV of FCFs", "PV of Terminal Value", "Net Cash"],
            values=[max(pv_fcfs_10, 0), max(pv_tv_10, 0), max(net_cash, 0)],
            hole=0.55,
            marker=dict(colors=[ACCENT2, ACCENT, AMBER]),
            textfont=dict(family="Space Mono", size=11),
        ))
        _layout_pie = {**PLOTLY_LAYOUT, "legend": dict(orientation="h", y=-0.1)}
        fig_pie.update_layout(
            **_layout_pie, height=300,
            title=dict(text="Value Composition (10yr)", font=dict(size=13)),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — SENSITIVITY
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    fcf_series2 = hist["FCF"].dropna() if "FCF" in hist.columns else pd.Series(dtype=float)
    base_fcf2   = fcf_series2.tail(3).mean() if len(fcf_series2) >= 2 else None

    if base_fcf2 is None or base_fcf2 <= 0:
        st.warning("Insufficient FCF data for sensitivity analysis.")
    else:
        st.markdown("#### Sensitivity Analysis — Intrinsic Value (10yr)")
        st.caption("Each cell shows intrinsic price. Green = undervalued vs current price, Red = overvalued.")

        sc1, sc2 = st.columns(2)
        with sc1:
            wacc_center = round(wacc_calc * 100, 1)
            wacc_range  = st.slider("WACC range (±%)", 1.0, 5.0, 3.0, 0.5)
        with sc2:
            hist_g2 = (
                hist["FCF_YoY%"].dropna().tail(3).mean()
                if "FCF_YoY%" in hist.columns else 8.0
            )
            hist_g2 = min(max(hist_g2, -20.0), 35.0)
            growth_center = round(hist_g2, 1)
            growth_range  = st.slider("Growth range (±%)", 2.0, 15.0, 8.0, 1.0)

        wacc_steps   = np.round(np.linspace(wacc_center - wacc_range, wacc_center + wacc_range, 7), 2)
        growth_steps = np.round(np.linspace(growth_center - growth_range, growth_center + growth_range, 7), 1)

        last_row2 = hist.iloc[-1]
        c2 = last_row2.get("Cash", 0) or 0
        d2 = last_row2.get("Debt", 0) or 0
        nc2 = (0 if (isinstance(c2, float) and np.isnan(c2)) else c2) \
            - (0 if (isinstance(d2, float) and np.isnan(d2)) else d2)

        matrix = []
        for w in wacc_steps:
            row_vals = []
            for g in growth_steps:
                w_r = w / 100
                g_r = g / 100
                if w_r <= 0.025:
                    row_vals.append(np.nan)
                    continue
                fs  = project_fcf(base_fcf2, g_r, 10)
                tv  = terminal_value(fs[-1], w_r, 0.025)
                ip  = intrinsic_price(fs, tv, w_r, nc2, shares)
                row_vals.append(ip)
            matrix.append(row_vals)

        matrix_np = np.array(matrix, dtype=float)

        # Color by margin vs current price
        margin_matrix = (matrix_np - price) / price * 100 if price else matrix_np

        fig_h = go.Figure(go.Heatmap(
            z=margin_matrix,
            x=[f"{g:.1f}%" for g in growth_steps],
            y=[f"{w:.2f}%" for w in wacc_steps],
            colorscale=[
                [0.0,  "#ff4d6d"],
                [0.35, "#f59e0b"],
                [0.5,  "#252830"],
                [0.65, "#0077ff"],
                [1.0,  "#00e5a0"],
            ],
            zmid=0,
            text=[[f"${v:,.0f}" if not np.isnan(v) else "—" for v in row] for row in matrix_np],
            texttemplate="%{text}",
            textfont=dict(family="Space Mono", size=10),
            colorbar=dict(
                title=dict(text="Margin of Safety %", font=dict(family="Syne", size=11)),
                tickfont=dict(family="Space Mono"),
                ticksuffix="%",
            ),
            hovertemplate="WACC: %{y}<br>Growth: %{x}<br>Price: %{text}<extra></extra>",
        ))
        fig_h.update_layout(
            **PLOTLY_LAYOUT,
            height=420,
            xaxis_title="FCF Growth Rate",
            yaxis_title="WACC",
            title=dict(
                text=f"Intrinsic Value vs Current Price (${price:,.2f}) — 10yr Horizon",
                font=dict(family="Syne", size=13),
            ),
        )
        st.plotly_chart(fig_h, use_container_width=True)

        # ── Text matrix table ──────────────────────────────────────────────────
        st.markdown("#### Intrinsic Price Table")
        tbl_df = pd.DataFrame(
            matrix_np,
            index=[f"WACC {w:.2f}%" for w in wacc_steps],
            columns=[f"g={g:.1f}%" for g in growth_steps],
        )
        # Format as $X,XXX
        tbl_styled = tbl_df.map(lambda x: f"${x:,.0f}" if not np.isnan(x) else "—")
        st.dataframe(tbl_styled, use_container_width=True)

        st.caption(f"🟢 Green = intrinsic > current price (${price:,.2f}) = undervalued &nbsp;·&nbsp; 🔴 Red = overvalued")
