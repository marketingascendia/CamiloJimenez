import yfinance as yf
import pandas as pd
import numpy as np

FALLBACK_RATE  = 0.0375   # Fallback si yfinance falla (3.75%)
MARKET_PREMIUM = 0.055
 
 
def get_risk_free_rate() -> tuple[float, str]:
    """
    Obtiene la tasa libre de riesgo desde Yahoo Finance (^TNX).
    ^TNX es el 10-Year Treasury Yield Index, cotiza en porcentaje (ej. 4.33).
 
    Returns:
        (rate: float, source: str)
    """
    try:
        tnx  = yf.Ticker("^TNX")
        rate = tnx.fast_info.get("lastPrice")
        if rate and rate > 0:
            rate = rate / 100   # 4.33 → 0.0433
            print(f"  [WACC] Risk-Free Rate (^TNX): {rate*100:.2f}%")
            return rate, "Yahoo Finance ^TNX"
    except Exception as e:
        print(f"  [WACC] Error obteniendo ^TNX: {e} — usando fallback")
 
    return FALLBACK_RATE, f"fallback ({FALLBACK_RATE*100:.2f}%)"


# ─── Carga la tasa al importar el módulo (una sola vez por sesión) ─────────────
RISK_FREE_RATE, RISK_FREE_SOURCE = get_risk_free_rate()


def _safe(val, default=None):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return default
    return val


def _get_annual_series(df: pd.DataFrame, row_keys: list) -> pd.Series | None:
    for key in row_keys:
        for idx in df.index:
            if key.lower() in str(idx).lower():
                row = df.loc[idx].dropna()
                row.index = pd.to_datetime(row.index)
                return row.sort_index()
    return None


def fetch_financials(ticker: str):
    t = yf.Ticker(ticker)
    info     = t.info
    income   = t.financials
    cashflow = t.cashflow
    balance  = t.balance_sheet
    return (income, cashflow, balance), info


def build_historical_table(income, cashflow, balance) -> pd.DataFrame:
    revenue    = _get_annual_series(income,   ["Total Revenue", "Revenue"])
    op_income  = _get_annual_series(income,   ["Operating Income", "Ebit"])
    net_income = _get_annual_series(income,   ["Net Income"])
    op_cf      = _get_annual_series(cashflow, ["Operating Cash Flow", "Total Cash From Operating"])
    capex      = _get_annual_series(cashflow, ["Capital Expenditure", "Capital Expenditures"])
    total_debt = _get_annual_series(balance,  ["Total Debt", "Long Term Debt"])
    cash       = _get_annual_series(balance,  ["Cash And Cash Equivalents", "Cash"])
    equity     = _get_annual_series(balance,  ["Total Stockholder Equity", "Stockholders Equity", "Common Stock Equity"])

    frames = {
        "Revenue": revenue, "Op_Income": op_income, "Net_Income": net_income,
        "Op_CF": op_cf, "CapEx": capex, "Debt": total_debt, "Cash": cash, "Equity": equity,
    }
    combined = pd.DataFrame({k: v for k, v in frames.items() if v is not None})
    combined = combined.sort_index().tail(5)

    if "Op_CF" in combined.columns and "CapEx" in combined.columns:
        combined["FCF"] = combined["Op_CF"] + combined["CapEx"]

    for col in ["Revenue", "Op_Income", "Net_Income", "FCF"]:
        if col in combined.columns:
            combined[f"{col}_YoY%"] = combined[col].pct_change() * 100

    combined.index = combined.index.year
    combined.index.name = "Year"
    return combined


def calc_wacc(info: dict, balance, income) -> float:
    beta   = _safe(info.get("beta"), 1.0)
    cost_e = RISK_FREE_RATE + beta * MARKET_PREMIUM

    int_exp  = _get_annual_series(income,  ["Interest Expense"])
    tot_debt = _get_annual_series(balance, ["Total Debt", "Long Term Debt"])

    if int_exp is not None and tot_debt is not None and len(int_exp) and len(tot_debt):
        avg_debt = tot_debt.tail(3).mean()
        avg_int  = abs(int_exp.tail(3).mean())
        cost_d   = avg_int / avg_debt if avg_debt else 0.04
        cost_d   = min(cost_d, 0.15)
    else:
        cost_d = 0.04

    tax_exp = _get_annual_series(income, ["Tax Provision", "Income Tax Expense"])
    pre_tax = _get_annual_series(income, ["Pretax Income", "Income Before Tax"])
    if tax_exp is not None and pre_tax is not None and len(tax_exp) and len(pre_tax):
        tax_rate = abs(tax_exp.tail(3).mean()) / abs(pre_tax.tail(3).mean())
        tax_rate = min(max(tax_rate, 0.10), 0.40)
    else:
        tax_rate = 0.21

    mkt_cap   = _safe(info.get("marketCap"), 1)
    debt_last = tot_debt.iloc[-1] if tot_debt is not None and len(tot_debt) else 0
    total_v   = mkt_cap + max(debt_last, 0)
    w_e = mkt_cap / total_v
    w_d = max(debt_last, 0) / total_v

    return w_e * cost_e + w_d * cost_d * (1 - tax_rate)


def project_fcf(base_fcf: float, growth_rate: float, years: int) -> list:
    return [base_fcf * (1 + growth_rate) ** y for y in range(1, years + 1)]


def terminal_value(fcf_last: float, wacc: float, perpetual_growth: float) -> float:
    if wacc <= perpetual_growth:
        return 0.0
    return fcf_last * (1 + perpetual_growth) / (wacc - perpetual_growth)


def intrinsic_price(fcfs: list, tv: float, wacc: float, net_cash: float, shares: float) -> float:
    if not shares:
        return 0.0
    pv_fcfs = sum(f / (1 + wacc) ** (i + 1) for i, f in enumerate(fcfs))
    pv_tv   = tv / (1 + wacc) ** len(fcfs)
    return (pv_fcfs + pv_tv + net_cash) / shares
