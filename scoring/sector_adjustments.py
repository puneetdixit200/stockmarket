from __future__ import annotations

from typing import Any


def apply_sector_adjustments(section_scores: dict[str, dict[str, int | None]], company_type: str, metrics: dict[str, Any]) -> dict[str, dict[str, int | None]]:
    adjusted = {section: dict(scores) for section, scores in section_scores.items()}
    if company_type == "ASSET_HEAVY" and metrics.get("net_debt_ebitda") is not None:
        adjusted.setdefault("risk_matrix", {})["asset_heavy_leverage_watch"] = 2 if metrics["net_debt_ebitda"] > 4 else 4
    if company_type == "SERVICES" and metrics.get("fcf_conversion_pct") is not None:
        adjusted.setdefault("cash_flow", {})["service_fcf_quality"] = 5 if metrics["fcf_conversion_pct"] > 80 else 3
    return adjusted
