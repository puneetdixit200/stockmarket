from __future__ import annotations

from typing import Any

from common import to_float


def calculate_data_confidence(data: dict[str, Any], company_type: str) -> dict[str, Any]:
    score = 0.0
    missing_critical: list[str] = []
    field_completeness: dict[str, Any] = {}

    core_fields = {
        "revenue_history": data.get("revenue_history", []),
        "pat_history": data.get("pat_history", []),
        "total_assets_history": data.get("total_assets_history", []),
        "equity_history": data.get("equity_history", []),
        "cfo_history": data.get("cfo_history", []),
    }
    for field_name, history in core_fields.items():
        valid_years = _valid_years(history)
        points = min(8.0, valid_years * 1.6)
        score += points
        field_completeness[field_name] = {"years_available": valid_years, "points": points}
        if valid_years < 3:
            missing_critical.append(f"{field_name}: only {valid_years} years available")

    for field, points in (("promoter_pct", 7), ("pledge_pct", 7), ("total_directors", 6)):
        available = data.get(field) is not None
        score += points if available else 0
        field_completeness[field] = {"available": available, "points": points if available else 0}
        if not available:
            missing_critical.append(f"governance: {field} unavailable")

    price_dates = data.get("price_history_dates") or [row.get("date") for row in data.get("price_history", []) if isinstance(row, dict)]
    ohlcv_years = len(price_dates) / 252
    if ohlcv_years >= 3:
        score += 15
        technical_points = 15
    elif ohlcv_years >= 1:
        score += 10
        technical_points = 10
    else:
        technical_points = 0
        missing_critical.append("price_history: insufficient for technical analysis")
    field_completeness["price_history"] = {"years": round(ohlcv_years, 1), "points": technical_points}

    if company_type in {"BANK", "NBFC"}:
        for field in ("gnpa_ratio", "nim", "car", "casa_ratio", "pcr"):
            available = data.get(field) is not None
            score += 3.0 if available else 0
            field_completeness[field] = {"available": available, "points": 3.0 if available else 0}
            if not available:
                missing_critical.append(f"banking_metric: {field} unavailable")
    elif company_type == "INSURANCE":
        for field in ("combined_ratio", "solvency_ratio", "loss_ratio", "premium_growth"):
            available = data.get(field) is not None
            score += 3.75 if available else 0
            field_completeness[field] = {"available": available, "points": 3.75 if available else 0}
            if not available:
                missing_critical.append(f"insurance_metric: {field} unavailable")
    else:
        score += 15.0
        field_completeness["sector_specific"] = {"available": True, "points": 15.0, "note": "not_applicable_for_type"}

    for field, points in (("beta", 5), ("sector_median_pe", 5)):
        available = data.get(field) is not None
        score += points if available else 0
        field_completeness[field] = {"available": available, "points": points if available else 0}

    has_target = data.get("target_mean_price") is not None
    has_rec = data.get("analyst_recommendation") is not None
    score += (2.5 if has_target else 0) + (2.5 if has_rec else 0)
    field_completeness["analyst_sentiment"] = {"target_price": has_target, "recommendation": has_rec}

    score = min(100.0, score)
    grade = next(g for threshold, g in ((90, "A"), (75, "B"), (60, "C"), (45, "D"), (0, "F")) if score >= threshold)
    sources = {key.removesuffix("_source"): value for key, value in data.items() if key.endswith("_source")}
    return {
        "confidence_score": round(score, 1),
        "confidence_grade": grade,
        "field_completeness": field_completeness,
        "missing_critical_fields": missing_critical,
        "data_sources_used": sources,
    }


def _valid_years(history: Any) -> int:
    if not isinstance(history, list):
        return 0
    return sum(1 for value in history[-5:] if to_float(value) is not None)
