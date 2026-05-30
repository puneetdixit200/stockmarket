from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from common import clean_value, normalise_symbol, now_iso


YFINANCE_FIELD_MAP = {
    "market_cap": ["marketCap", "enterpriseValue"],
    "pe_ratio": ["trailingPE", "forwardPE"],
    "pb_ratio": ["priceToBook"],
    "dividend_yield": ["dividendYield"],
    "book_value": ["bookValue"],
    "eps": ["trailingEps", "forwardEps"],
    "beta": ["beta"],
    "sector": ["sector"],
    "industry": ["industry"],
    "target_mean_price": ["targetMeanPrice"],
    "analyst_recommendation": ["recommendationKey"],
    "shares_outstanding": ["sharesOutstanding", "impliedSharesOutstanding"],
    "enterprise_value": ["enterpriseValue"],
}


def _import_yfinance():
    try:
        import yfinance as yf

        return yf
    except ImportError:
        return None


def safe_get_yf_field(info: dict[str, Any], logical_field: str, default: Any = None) -> Any:
    for candidate in YFINANCE_FIELD_MAP.get(logical_field, [logical_field]):
        value = info.get(candidate)
        if value is not None:
            return value
    return default


def _frame_to_history(frame: pd.DataFrame, field_candidates: list[str]) -> list[float | None]:
    if frame is None or frame.empty:
        return []
    for candidate in field_candidates:
        if candidate in frame.index:
            values = frame.loc[candidate].dropna().sort_index()
            return [float(v) for v in values.tail(5).tolist()]
    return []


class YFinanceCollector:
    def __init__(self, period: str = "3y", interval: str = "1d") -> None:
        self.period = period
        self.interval = interval
        self.yf = _import_yfinance()

    def collect_symbol(self, symbol: str) -> dict[str, Any]:
        clean_symbol = normalise_symbol(symbol)
        if self.yf is None:
            return {"symbol": clean_symbol, "_source": "unavailable", "_error": "yfinance is not installed"}
        for suffix in (".NS", ".BO"):
            ticker_symbol = f"{clean_symbol}{suffix}"
            try:
                ticker = self.yf.Ticker(ticker_symbol)
                info = ticker.info or {}
                if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
                    continue
                financials = getattr(ticker, "financials", pd.DataFrame())
                balance_sheet = getattr(ticker, "balance_sheet", pd.DataFrame())
                cashflow = getattr(ticker, "cashflow", pd.DataFrame())
                history = ticker.history(period=self.period, interval=self.interval, auto_adjust=False)
                data = {
                    "symbol": clean_symbol,
                    "ticker": ticker_symbol,
                    "company_name": info.get("longName") or info.get("shortName") or clean_symbol,
                    "last_price": info.get("currentPrice") or info.get("regularMarketPrice"),
                    "previous_close": info.get("previousClose"),
                    "year_high": info.get("fiftyTwoWeekHigh"),
                    "year_low": info.get("fiftyTwoWeekLow"),
                    "volume": info.get("volume"),
                    "currency": info.get("currency") or "INR",
                    "suffix_used": suffix,
                    "_source": "yfinance",
                    "_fetched_at": now_iso(),
                }
                for logical in YFINANCE_FIELD_MAP:
                    data[logical] = safe_get_yf_field(info, logical)
                data["revenue_history"] = _frame_to_history(financials, ["Total Revenue", "totalRevenue"])
                data["pat_history"] = _frame_to_history(financials, ["Net Income", "netIncome"])
                data["ebit_history"] = _frame_to_history(financials, ["EBIT", "Operating Income", "Ebit"])
                data["total_assets_history"] = _frame_to_history(balance_sheet, ["Total Assets", "totalAssets"])
                data["equity_history"] = _frame_to_history(
                    balance_sheet,
                    ["Total Equity Gross Minority Interest", "Stockholders Equity", "Common Stock Equity"],
                )
                data["total_debt_history"] = _frame_to_history(balance_sheet, ["Total Debt", "totalDebt"])
                data["cfo_history"] = _frame_to_history(cashflow, ["Operating Cash Flow", "Total Cash From Operating Activities"])
                data["capex_history"] = _frame_to_history(cashflow, ["Capital Expenditure", "capitalExpenditures"])
                data["price_history"] = self._history_records(history)
                return clean_value(data)
            except Exception as exc:
                logging.warning("yfinance fetch failed for %s: %s", ticker_symbol, exc)
        return {"symbol": clean_symbol, "_source": "unavailable", "_error": "no yfinance data for NSE or BSE suffix"}

    def _history_records(self, history: pd.DataFrame) -> list[dict[str, Any]]:
        if history is None or history.empty:
            return []
        frame = history.reset_index()
        records = []
        for _, row in frame.iterrows():
            date_value = row.get("Date") or row.get("Datetime")
            records.append(
                {
                    "date": pd.Timestamp(date_value).date().isoformat(),
                    "open": row.get("Open"),
                    "high": row.get("High"),
                    "low": row.get("Low"),
                    "close": row.get("Close"),
                    "volume": row.get("Volume"),
                }
            )
        return clean_value(records)
