from __future__ import annotations

from typing import Any

from common import to_float


def calculate_risk_metrics(data: dict[str, Any]) -> dict[str, Any]:
    net_debt_ebitda = to_float(data.get("net_debt_ebitda"), 0)
    beta = to_float(data.get("beta"), 1.0)
    promoter_pct = to_float(data.get("promoter_pct"))
    pledge_pct = to_float(data.get("pledge_pct"), 0)
    gnpa = to_float(data.get("gnpa_ratio"), 0)
    return {
        "beta": beta,
        "leverage_risk_score": _leverage_risk(net_debt_ebitda),
        "pledge_pct": pledge_pct,
        "concentration_risk_flag": promoter_pct is not None and promoter_pct > 75,
        "commodity_exposure_flag": bool(data.get("commodity_exposure_flag", False)),
        "currency_risk_flag": bool(data.get("currency_risk_flag", False)),
        "regulatory_risk_flag": bool(data.get("regulatory_risk_flag", False)),
        "gnpa_ratio": gnpa,
        "risk_flags": _risk_flags(data, net_debt_ebitda, pledge_pct, gnpa),
    }


def _leverage_risk(value: float | None) -> int:
    if value is None or value < 0:
        return 5
    if value <= 0.5:
        return 4
    if value <= 2:
        return 3
    if value <= 4:
        return 2
    return 1


def _risk_flags(data: dict[str, Any], net_debt_ebitda: float | None, pledge_pct: float | None, gnpa: float | None) -> list[str]:
    flags: list[str] = []
    if pledge_pct is not None and pledge_pct > 25:
        flags.append("PLEDGE_GT_25")
    if to_float(data.get("altman_z_score")) is not None and to_float(data.get("altman_z_score")) < 1.8:
        flags.append("ALTMAN_Z_LT_1_8")
    if to_float(data.get("piotroski_score")) is not None and to_float(data.get("piotroski_score")) < 3:
        flags.append("PIOTROSKI_LT_3")
    if net_debt_ebitda is not None and net_debt_ebitda > 5:
        flags.append("NET_DEBT_EBITDA_GT_5")
    if data.get("fcf_negative_3_consecutive"):
        flags.append("FCF_NEGATIVE_3Y")
    if data.get("audit_qualified_opinion"):
        flags.append("QUALIFIED_AUDIT")
    if gnpa is not None and gnpa > 7:
        flags.append("GNPA_GT_7")
    if data.get("sell_cluster_6m"):
        flags.append("INSIDER_SELL_CLUSTER")
    if to_float(data.get("data_confidence_score")) is not None and to_float(data.get("data_confidence_score")) < 30:
        flags.append("DATA_CONFIDENCE_LT_30")
    return flags
