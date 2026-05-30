from __future__ import annotations

from typing import Any

from common import safe_div, to_float


def calculate_governance_metrics(data: dict[str, Any]) -> dict[str, Any]:
    promoter_pct = to_float(data.get("promoter_pct"))
    pledge_pct = to_float(data.get("pledge_pct"), 0)
    related_party = to_float(data.get("related_party_transactions_pct"), 0)
    remuneration = to_float(data.get("management_remuneration_pct_pat"), 0)
    total_directors = to_float(data.get("total_directors"))
    independent_directors = to_float(data.get("independent_directors"))
    return {
        "promoter_pct": promoter_pct,
        "pledge_pct": pledge_pct,
        "board_independence_pct": _pct(safe_div(independent_directors, total_directors)),
        "auditor_quality_score": to_float(data.get("auditor_quality_score"), 3),
        "related_party_transactions_pct": related_party,
        "management_remuneration_pct_pat": remuneration,
        "sell_cluster_6m": bool(data.get("sell_cluster_6m", False)),
        "audit_qualified_opinion": bool(data.get("audit_qualified_opinion", False)),
        "governance_risk_flags": _governance_flags(promoter_pct, pledge_pct, related_party, remuneration, data),
    }


def _pct(value: float | None) -> float | None:
    return value * 100 if value is not None else None


def _governance_flags(promoter_pct: float | None, pledge_pct: float | None, related_party: float | None, remuneration: float | None, data: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    if promoter_pct is not None and promoter_pct < 20:
        flags.append("LOW_PROMOTER_HOLDING")
    if pledge_pct is not None and pledge_pct > 25:
        flags.append("HIGH_PLEDGE")
    if related_party is not None and related_party > 10:
        flags.append("HIGH_RELATED_PARTY_TRANSACTIONS")
    if remuneration is not None and remuneration > 10:
        flags.append("HIGH_MANAGEMENT_REMUNERATION")
    if data.get("audit_qualified_opinion"):
        flags.append("QUALIFIED_AUDIT_OPINION")
    if data.get("sell_cluster_6m"):
        flags.append("INSIDER_SELL_CLUSTER")
    return flags
