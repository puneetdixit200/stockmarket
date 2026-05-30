from __future__ import annotations

import math
from typing import Any

from common import cagr, safe_div, to_float


def calculate_valuation_metrics(data: dict[str, Any], sector_medians: dict[str, Any] | None = None, macro: dict[str, Any] | None = None) -> dict[str, Any]:
    sector_medians = sector_medians or {}
    macro = macro or {}
    price = to_float(data.get("last_price"))
    eps = to_float(data.get("eps") or data.get("earnings_per_share"))
    book_value = to_float(data.get("book_value"))
    market_cap = to_float(data.get("market_cap"))
    enterprise_value = to_float(data.get("enterprise_value")) or market_cap
    revenue = _latest(data.get("revenue_history")) or to_float(data.get("revenue"))
    ebitda = _latest(data.get("ebitda_history")) or to_float(data.get("ebitda"))
    cfo = _latest(data.get("cfo_history"))
    capex = _latest(data.get("capex_history")) or 0
    fcf = data.get("free_cash_flow")
    if fcf is None and cfo is not None:
        fcf = cfo + capex
    pe = to_float(data.get("pe_ratio")) or safe_div(price, eps)
    pb = to_float(data.get("pb_ratio")) or safe_div(price, book_value)
    ev_ebitda = safe_div(enterprise_value, ebitda)
    ev_sales = safe_div(enterprise_value, revenue)
    fcf_yield = safe_div(fcf, market_cap)
    p_fcf = safe_div(market_cap, fcf)
    revenue_growth = cagr(data.get("revenue_history") or [])
    peg = safe_div(pe, (revenue_growth or 0) * 100)
    graham_number = None
    if eps is not None and eps > 0 and book_value is not None and book_value > 0:
        graham_number = math.sqrt(22.5 * eps * book_value)
    earnings_yield = safe_div(eps, price)
    gsec = to_float(macro.get("gsec_10yr_yield"), 7.0)
    earnings_yield_spread = (earnings_yield * 100 - gsec) if earnings_yield is not None else None
    dcf_base = to_float(data.get("base_dcf_value"))
    return {
        "pe_ratio": pe,
        "pb_ratio": pb,
        "ev_ebitda": ev_ebitda,
        "ev_sales": ev_sales,
        "fcf_yield_pct": fcf_yield * 100 if fcf_yield is not None else None,
        "p_fcf": p_fcf,
        "peg_ratio": peg,
        "graham_number": graham_number,
        "graham_margin_of_safety_pct": _margin_of_safety(price, graham_number),
        "earnings_yield_pct": earnings_yield * 100 if earnings_yield is not None else None,
        "earnings_yield_spread_pct": earnings_yield_spread,
        "pe_discount_to_sector_pct": _discount_to_median(pe, sector_medians.get("pe_ratio")),
        "pb_discount_to_sector_pct": _discount_to_median(pb, sector_medians.get("pb_ratio")),
        "ev_ebitda_discount_to_sector_pct": _discount_to_median(ev_ebitda, sector_medians.get("ev_ebitda")),
        "dcf_base_margin_of_safety_pct": _margin_of_safety(price, dcf_base),
    }


def _latest(values: Any) -> float | None:
    if not isinstance(values, list) or not values:
        return None
    for value in reversed(values):
        numeric = to_float(value)
        if numeric is not None:
            return numeric
    return None


def _discount_to_median(value: Any, median: Any) -> float | None:
    value_f = to_float(value)
    median_f = to_float(median)
    if value_f is None or median_f in (None, 0):
        return None
    return (median_f - value_f) / median_f * 100


def _margin_of_safety(price: Any, fair_value: Any) -> float | None:
    price_f = to_float(price)
    fair_f = to_float(fair_value)
    if price_f is None or fair_f in (None, 0):
        return None
    return (fair_f - price_f) / fair_f * 100
