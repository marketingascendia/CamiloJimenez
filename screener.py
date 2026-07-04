import yfinance as yf
import time


def fetch_ticker_info(ticker: str, retries: int = 3) -> dict | None:
    for attempt in range(1, retries + 1):
        try:
            t    = yf.Ticker(ticker)
            info = t.info
            if not info or info.get("regularMarketPrice") is None:
                return None
            return {
                "ticker":          ticker,
                "name":            info.get("longName", ""),
                "sector":          info.get("sector", ""),
                "industry":        info.get("industry", ""),
                "price":           info.get("regularMarketPrice"),
                "market_cap":      info.get("marketCap"),
                "pe_ratio":        info.get("trailingPE"),
                "pb_ratio":        info.get("priceToBook"),
                "ev_ebitda":       info.get("enterpriseToEbitda"),
                "profit_margin":   info.get("profitMargins"),
                "roe":             info.get("returnOnEquity"),
                "roa":             info.get("returnOnAssets"),
                "revenue_growth":  info.get("revenueGrowth"),
                "earnings_growth": info.get("earningsGrowth"),
                "dividend_yield":  info.get("dividendYield"),
                "avg_volume":      info.get("averageVolume"),
                "debt_to_equity":  info.get("debtToEquity") / 100
                                   if info.get("debtToEquity") is not None else None,
            }
        except Exception as e:
            if attempt < retries and ("rate" in str(e).lower() or "429" in str(e)):
                time.sleep(attempt * 5)
            else:
                raise
    return None


def passes_filters(row: dict, filters: dict) -> tuple[bool, list[str]]:
    failures = []

    def check(value, min_val, max_val, label):
        if value is None:
            failures.append(f"{label}: no data")
            return
        if min_val is not None and value < min_val:
            failures.append(f"{label} {value:.3f} < min {min_val}")
        if max_val is not None and value > max_val:
            failures.append(f"{label} {value:.3f} > max {max_val}")

    check(row["pe_ratio"],        None,                             filters.get("MAX_PE_RATIO"),        "P/E Ratio")
    check(row["pb_ratio"],        None,                             filters.get("MAX_PB_RATIO"),        "P/B Ratio")
    check(row["ev_ebitda"],       None,                             filters.get("MAX_EV_EBITDA"),       "EV/EBITDA")
    check(row["profit_margin"],   filters.get("MIN_PROFIT_MARGIN"), None,                               "Profit Margin")
    check(row["roe"],             filters.get("MIN_ROE"),           None,                               "ROE")
    check(row["roa"],             filters.get("MIN_ROA"),           None,                               "ROA")
    check(row["revenue_growth"],  filters.get("MIN_REVENUE_GROWTH"),None,                               "Revenue Growth")
    check(row["earnings_growth"], filters.get("MIN_EARNINGS_GROWTH"),None,                              "Earnings Growth")
    check(row["debt_to_equity"],  None,                             filters.get("MAX_DEBT_TO_EQUITY"),  "Debt/Equity")

    return len(failures) == 0, failures
