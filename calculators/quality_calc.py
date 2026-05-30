from __future__ import annotations

from typing import Any

from common import mean_present, safe_div, to_float


def calculate_quality_metrics(data: dict[str, Any]) -> dict[str, Any]:
    revenue = _latest(data.get("revenue_history"))
    pat = _latest(data.get("pat_history"))
    ebit = _latest(data.get("ebit_history"))
    ebitda = _latest(data.get("ebitda_history")) or ebit
    assets = _latest(data.get("total_assets_history"))
    equity = _latest(data.get("equity_history"))
    debt = _latest(data.get("total_debt_history")) or to_float(data.get("total_debt"), 0)
    cfo = _latest(data.get("cfo_history"))
    capex = _latest(data.get("capex_history")) or 0
    cash = to_float(data.get("cash"), 0)
    current_assets = to_float(data.get("current_assets"))
    current_liabilities = to_float(data.get("current_liabilities"))
    interest_expense = abs(to_float(data.get("interest_expense"), 0) or 0)
    roe_values = [
        safe_div(p, e)
        for p, e in zip(data.get("pat_history") or [], data.get("equity_history") or [])
        if safe_div(p, e) is not None
    ]
    roce = safe_div(ebit, (equity or 0) + (debt or 0) - (cash or 0))
    roic = safe_div(ebit, (equity or 0) + (debt or 0))
    net_debt = (debt or 0) - (cash or 0)
    net_debt_ebitda = safe_div(net_debt, ebitda)
    fcf = cfo + capex if cfo is not None else None
    return {
        "gross_margin_pct": _pct(safe_div(data.get("gross_profit"), revenue)),
        "ebitda_margin_pct": _pct(safe_div(ebitda, revenue)),
        "net_margin_pct": _pct(safe_div(pat, revenue)),
        "roe_pct": _pct(mean_present(roe_values)),
        "roce_pct": _pct(roce),
        "roic_pct": _pct(roic),
        "roic_wacc_spread_pct": _spread(_pct(roic), data.get("wacc_pct")),
        "fcf_conversion_pct": _pct(safe_div(fcf, pat)),
        "cfo_to_pat": safe_div(cfo, pat),
        "net_debt": net_debt,
        "net_debt_ebitda": net_debt_ebitda,
        "debt_equity": safe_div(debt, equity),
        "interest_coverage": None if interest_expense == 0 else safe_div(ebit, interest_expense),
        "current_ratio": safe_div(current_assets, current_liabilities),
        "altman_z_score": _altman_z(data, assets, equity, ebit, revenue, market_cap=to_float(data.get("market_cap"))),
        "piotroski_score": _piotroski_score(data),
        "goodwill_to_equity_pct": _pct(safe_div(data.get("goodwill"), equity)),
    }


def _latest(values: Any) -> float | None:
    if not isinstance(values, list) or not values:
        return None
    for value in reversed(values):
        numeric = to_float(value)
        if numeric is not None:
            return numeric
    return None


def _pct(value: float | None) -> float | None:
    return value * 100 if value is not None else None


def _spread(value: float | None, benchmark: Any) -> float | None:
    bench = to_float(benchmark)
    if value is None or bench is None:
        return None
    return value - bench


def _altman_z(data: dict[str, Any], assets: float | None, equity: float | None, ebit: float | None, revenue: float | None, market_cap: float | None) -> float | None:
    if not assets:
        return None
    working_capital = (to_float(data.get("current_assets"), 0) or 0) - (to_float(data.get("current_liabilities"), 0) or 0)
    retained_earnings = to_float(data.get("retained_earnings"), 0) or 0
    total_liabilities = assets - (equity or 0)
    if total_liabilities <= 0:
        total_liabilities = 1
    return (
        1.2 * working_capital / assets
        + 1.4 * retained_earnings / assets
        + 3.3 * ((ebit or 0) / assets)
        + 0.6 * ((market_cap or equity or 0) / total_liabilities)
        + 1.0 * ((revenue or 0) / assets)
    )


def _piotroski_score(data: dict[str, Any]) -> int | None:
    pat_history = data.get("pat_history") or []
    cfo_history = data.get("cfo_history") or []
    assets_history = data.get("total_assets_history") or []
    debt_history = data.get("total_debt_history") or []
    current_assets = to_float(data.get("current_assets"))
    current_liabilities = to_float(data.get("current_liabilities"))
    score = 0
    latest_pat = _latest(pat_history)
    latest_cfo = _latest(cfo_history)
    if latest_pat is None and latest_cfo is None:
        return None
    if (latest_pat or 0) > 0:
        score += 1
    if (latest_cfo or 0) > 0:
        score += 1
    if latest_cfo is not None and latest_pat is not None and latest_cfo > latest_pat:
        score += 1
    if len(pat_history) >= 2 and len(assets_history) >= 2:
        roa_now = safe_div(pat_history[-1], assets_history[-1])
        roa_prev = safe_div(pat_history[-2], assets_history[-2])
        if roa_now is not None and roa_prev is not None and roa_now > roa_prev:
            score += 1
    if len(debt_history) >= 2 and to_float(debt_history[-1], 0) <= to_float(debt_history[-2], 0):
        score += 1
    if current_assets and current_liabilities and current_assets / current_liabilities > 1:
        score += 1
    if len(data.get("shares_history") or []) >= 2 and data["shares_history"][-1] <= data["shares_history"][-2]:
        score += 1
    if len(data.get("gross_margin_history") or []) >= 2 and data["gross_margin_history"][-1] > data["gross_margin_history"][-2]:
        score += 1
    if len(data.get("asset_turnover_history") or []) >= 2 and data["asset_turnover_history"][-1] > data["asset_turnover_history"][-2]:
        score += 1
    return score
