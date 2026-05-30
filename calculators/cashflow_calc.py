from __future__ import annotations

from typing import Any

from common import cagr, safe_div, to_float


def calculate_cashflow_metrics(data: dict[str, Any]) -> dict[str, Any]:
    cfo_history = [to_float(v) for v in data.get("cfo_history", [])]
    capex_history = [to_float(v) for v in data.get("capex_history", [])]
    pat_history = [to_float(v) for v in data.get("pat_history", [])]
    revenue_history = [to_float(v) for v in data.get("revenue_history", [])]
    fcf_history = []
    for index, cfo in enumerate(cfo_history):
        capex = capex_history[index] if index < len(capex_history) and capex_history[index] is not None else 0
        fcf_history.append(None if cfo is None else cfo + capex)
    latest_revenue = _latest(revenue_history)
    latest_fcf = _latest(fcf_history)
    latest_cfo = _latest(cfo_history)
    latest_pat = _latest(pat_history)
    dividends_paid = abs(to_float(data.get("dividends_paid"), 0) or 0)
    return {
        "free_cash_flow": latest_fcf,
        "free_cash_flow_history": fcf_history,
        "owner_earnings": latest_fcf,
        "fcf_negative_3_consecutive": _last_n_negative(fcf_history, 3),
        "cfo_to_pat": safe_div(latest_cfo, latest_pat),
        "capex_intensity_pct": _pct(safe_div(abs(_latest(capex_history) or 0), latest_revenue)),
        "owner_earnings_cagr_5y_pct": _pct(cagr([v for v in fcf_history if v is not None])),
        "dividend_payout_cfo_pct": _pct(safe_div(dividends_paid, latest_cfo)),
        "buyback_yield_pct": _pct(safe_div(abs(to_float(data.get("buybacks"), 0) or 0), data.get("market_cap"))),
    }


def _latest(values: list[float | None]) -> float | None:
    for value in reversed(values):
        if value is not None:
            return value
    return None


def _pct(value: float | None) -> float | None:
    return value * 100 if value is not None else None


def _last_n_negative(values: list[float | None], n: int) -> bool:
    cleaned = [v for v in values if v is not None]
    return len(cleaned) >= n and all(v < 0 for v in cleaned[-n:])
