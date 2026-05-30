from __future__ import annotations

from typing import Any

from common import cagr, to_float


def calculate_growth_metrics(data: dict[str, Any]) -> dict[str, Any]:
    revenue_history = data.get("revenue_history") or []
    pat_history = data.get("pat_history") or []
    ebit_history = data.get("ebit_history") or []
    eps_history = data.get("eps_history") or []
    return {
        "revenue_cagr_5y_pct": _pct(cagr(revenue_history)),
        "pat_cagr_5y_pct": _pct(cagr(pat_history)),
        "ebit_cagr_5y_pct": _pct(cagr(ebit_history)),
        "eps_cagr_5y_pct": _pct(cagr(eps_history)) if eps_history else None,
        "sales_growth_latest_pct": _latest_growth(revenue_history),
        "pat_growth_latest_pct": _latest_growth(pat_history),
        "growth_consistency_score": _growth_consistency(revenue_history),
    }


def _pct(value: float | None) -> float | None:
    return value * 100 if value is not None else None


def _latest_growth(values: list[Any]) -> float | None:
    if len(values) < 2:
        return None
    prev = to_float(values[-2])
    curr = to_float(values[-1])
    if prev in (None, 0) or curr is None:
        return None
    return (curr / prev - 1) * 100


def _growth_consistency(values: list[Any]) -> float | None:
    if len(values) < 3:
        return None
    positives = 0
    comparisons = 0
    for prev, curr in zip(values, values[1:]):
        prev_f = to_float(prev)
        curr_f = to_float(curr)
        if prev_f is None or curr_f is None:
            continue
        comparisons += 1
        positives += 1 if curr_f >= prev_f else 0
    if comparisons == 0:
        return None
    return positives / comparisons * 100
