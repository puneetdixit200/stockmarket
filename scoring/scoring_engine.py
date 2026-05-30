from __future__ import annotations

from typing import Any

from common import mean_present, score_ascending, score_descending, score_discount, to_float


SECTION_WEIGHTS = {
    "absolute_valuation": 0.12,
    "relative_valuation": 0.05,
    "profitability": 0.12,
    "balance_sheet": 0.10,
    "cash_flow": 0.10,
    "growth": 0.10,
    "governance": 0.10,
    "moat": 0.10,
    "macro_tailwinds": 0.05,
    "technical": 0.05,
    "risk_matrix": 0.08,
    "sentiment": 0.03,
}


if abs(sum(SECTION_WEIGHTS.values()) - 1.0) >= 1e-9:
    raise RuntimeError(f"Section weights must sum to 1.0, got {sum(SECTION_WEIGHTS.values())}")


def score_company_sections(metrics: dict[str, Any], company_type: str = "GENERAL") -> dict[str, dict[str, int | None]]:
    if company_type in {"BANK", "NBFC"}:
        from scoring.bank_scorer import score_bank_sections

        return score_bank_sections(metrics)
    if company_type == "INSURANCE":
        from scoring.insurance_scorer import score_insurance_sections

        return score_insurance_sections(metrics)
    return {
        "absolute_valuation": {
            "pe_vs_sector": score_discount(metrics.get("pe_discount_to_sector_pct"), 40, 20, -20, -40),
            "pb_vs_sector": score_discount(metrics.get("pb_discount_to_sector_pct"), 40, 20, -20, -40),
            "ev_ebitda_vs_sector": score_discount(metrics.get("ev_ebitda_discount_to_sector_pct"), 30, 10, -10, -30),
            "p_fcf": score_ascending(metrics.get("p_fcf"), [(12, 5), (18, 4), (25, 3), (40, 2), (10**9, 1)]),
            "peg_ratio": score_ascending(metrics.get("peg_ratio"), [(0.5, 5), (1.0, 4), (1.5, 3), (2.5, 2), (10**9, 1)]),
            "graham_margin": score_discount(metrics.get("graham_margin_of_safety_pct"), 50, 30, 10, -20),
            "earnings_yield_spread": score_descending(metrics.get("earnings_yield_spread_pct"), [(4, 5), (2, 4), (0, 3), (-2, 2), (-10**9, 1)]),
            "dcf_margin": score_discount(metrics.get("dcf_base_margin_of_safety_pct"), 40, 20, 0, -20),
            "fcf_yield": score_descending(metrics.get("fcf_yield_pct"), [(8, 5), (5, 4), (3, 3), (1, 2), (-10**9, 1)]),
        },
        "relative_valuation": {
            "pe_vs_peer": score_discount(metrics.get("pe_peer_discount_pct"), 30, 15, -15, -30),
            "ev_ebitda_vs_peer": score_discount(metrics.get("ev_ebitda_peer_discount_pct"), 30, 15, -15, -30),
            "ev_ic": score_ascending(metrics.get("ev_ic"), [(1, 5), (1.5, 4), (2.5, 3), (4, 2), (10**9, 1)]),
            "replacement_cost": score_ascending(metrics.get("price_to_replacement_cost"), [(0.8, 5), (1.2, 4), (2, 3), (3.5, 2), (10**9, 1)]),
        },
        "profitability": {
            "roe": score_descending(metrics.get("roe_pct"), [(25, 5), (18, 4), (12, 3), (8, 2), (-10**9, 1)]),
            "roce": score_descending(metrics.get("roce_pct"), [(25, 5), (20, 4), (15, 3), (10, 2), (-10**9, 1)]),
            "roic_spread": score_descending(metrics.get("roic_wacc_spread_pct"), [(10, 5), (5, 4), (0, 3), (-5, 2), (-10**9, 1)]),
            "net_margin_vs_sector": score_descending(metrics.get("net_margin_spread_bps"), [(500, 5), (200, 4), (-200, 3), (-500, 2), (-10**9, 1)]),
            "fcf_conversion": score_descending(metrics.get("fcf_conversion_pct"), [(90, 5), (75, 4), (50, 3), (25, 2), (-10**9, 1)]),
        },
        "balance_sheet": {
            "net_debt_ebitda": _score_net_debt(metrics.get("net_debt_ebitda")),
            "interest_coverage": score_descending(metrics.get("interest_coverage"), [(20, 5), (10, 4), (5, 3), (2, 2), (-10**9, 1)]),
            "altman_z": score_descending(metrics.get("altman_z_score"), [(3, 5), (2.5, 4), (2, 3), (1.8, 2), (-10**9, 1)]),
            "piotroski": score_descending(metrics.get("piotroski_score"), [(8, 5), (6, 4), (4, 3), (2, 2), (-10**9, 1)]),
            "current_ratio": score_descending(metrics.get("current_ratio"), [(3, 5), (2, 4), (1.5, 3), (1, 2), (-10**9, 1)]),
            "goodwill_to_equity": score_ascending(metrics.get("goodwill_to_equity_pct"), [(0, 5), (10, 4), (25, 3), (50, 2), (10**9, 1)]),
        },
        "cash_flow": {
            "fcf_yield": score_descending(metrics.get("fcf_yield_pct"), [(8, 5), (5, 4), (3, 3), (1, 2), (-10**9, 1)]),
            "cfo_to_pat": score_descending(metrics.get("cfo_to_pat"), [(1.2, 5), (1, 4), (0.8, 3), (0.6, 2), (-10**9, 1)]),
            "capex_intensity": score_ascending(metrics.get("capex_intensity_pct"), [(5, 5), (10, 4), (20, 3), (30, 2), (10**9, 1)]),
            "owner_earnings_growth": score_descending(metrics.get("owner_earnings_cagr_5y_pct"), [(20, 5), (12, 4), (8, 3), (3, 2), (-10**9, 1)]),
        },
        "growth": {
            "revenue_cagr": score_descending(metrics.get("revenue_cagr_5y_pct"), [(20, 5), (12, 4), (8, 3), (3, 2), (-10**9, 1)]),
            "pat_cagr": score_descending(metrics.get("pat_cagr_5y_pct"), [(20, 5), (12, 4), (8, 3), (3, 2), (-10**9, 1)]),
            "growth_consistency": score_descending(metrics.get("growth_consistency_score"), [(90, 5), (75, 4), (50, 3), (25, 2), (-10**9, 1)]),
        },
        "governance": {
            "promoter": score_descending(metrics.get("promoter_pct"), [(55, 5), (40, 4), (25, 3), (15, 2), (-10**9, 1)]),
            "pledge": score_ascending(metrics.get("pledge_pct"), [(0, 5), (5, 4), (15, 3), (25, 2), (10**9, 1)]),
            "board_independence": score_descending(metrics.get("board_independence_pct"), [(50, 5), (40, 4), (33, 3), (25, 2), (-10**9, 1)]),
            "auditor_quality": score_descending(metrics.get("auditor_quality_score"), [(5, 5), (4, 4), (3, 3), (2, 2), (-10**9, 1)]),
        },
        "moat": {
            "pricing_power": score_descending(metrics.get("pricing_power_spread_bps"), [(500, 5), (250, 4), (0, 3), (-250, 2), (-10**9, 1)]),
            "asset_efficiency": score_descending(metrics.get("asset_efficiency_spread_pct"), [(30, 5), (10, 4), (-10, 3), (-30, 2), (-10**9, 1)]),
            "moat_proxy": score_descending(metrics.get("moat_score_proxy"), [(80, 5), (60, 4), (40, 3), (20, 2), (-10**9, 1)]),
        },
        "macro_tailwinds": {
            "gdp_growth": score_descending(metrics.get("india_gdp_growth"), [(7, 5), (6, 4), (5, 3), (4, 2), (-10**9, 1)]),
            "sector_tailwind": score_descending(metrics.get("sector_tailwind_score"), [(5, 5), (4, 4), (3, 3), (2, 2), (-10**9, 1)]),
        },
        "technical": {
            "rsi": _score_rsi(metrics.get("rsi_14")),
            "drawdown": score_descending(metrics.get("potential_return_to_52w_high_pct"), [(30, 5), (20, 4), (10, 3), (0, 2), (-10**9, 1)]),
            "relative_strength": score_descending(metrics.get("relative_strength_6m_pct"), [(15, 5), (5, 4), (0, 3), (-10, 2), (-10**9, 1)]),
        },
        "risk_matrix": {
            "leverage": metrics.get("leverage_risk_score"),
            "beta": score_ascending(metrics.get("beta"), [(0.8, 5), (1.0, 4), (1.2, 3), (1.5, 2), (10**9, 1)]),
            "red_flags": score_ascending(len(metrics.get("risk_flags") or []), [(0, 5), (1, 4), (2, 3), (4, 2), (10**9, 1)]),
        },
        "sentiment": {
            "analyst_target_upside": score_descending(metrics.get("analyst_target_upside_pct"), [(30, 5), (15, 4), (0, 3), (-15, 2), (-10**9, 1)]),
            "recommendation": _score_recommendation(metrics.get("analyst_recommendation")),
        },
    }


def calculate_composite_score(company_scores: dict[str, dict[str, int | None]], company_data: dict[str, Any], confidence: dict[str, Any]) -> dict[str, Any]:
    section_scores: dict[str, float] = {}
    for section, params in company_scores.items():
        valid_scores = [value for value in params.values() if value is not None]
        if len(valid_scores) >= 1:
            section_scores[section] = sum(valid_scores) / len(valid_scores)
    available_sections = set(section_scores)
    total_available_weight = sum(weight for section, weight in SECTION_WEIGHTS.items() if section in available_sections)
    if total_available_weight == 0:
        return {"composite_score_100": 0, "verdict": "INSUFFICIENT_DATA", "section_scores": {}}
    weighted_score = sum(
        section_scores[section] * (SECTION_WEIGHTS[section] / total_available_weight)
        for section in available_sections
    )
    composite_100 = weighted_score * 20
    penalties_applied: list[str] = []
    composite_100 = _apply_penalties(composite_100, company_data, penalties_applied)
    composite_100 = round(max(min(composite_100, 100), 0), 1)
    verdict = next(v for threshold, v in ((85, "STRONG BUY"), (70, "BUY"), (55, "ACCUMULATE"), (40, "HOLD"), (25, "AVOID"), (0, "STRONG AVOID")) if composite_100 >= threshold)
    conf_score = to_float(confidence.get("confidence_score"), 100) or 100
    if conf_score < 50:
        verdict += "*"
    scored_sections = sorted(section_scores.items(), key=lambda item: item[1], reverse=True)
    return {
        "composite_score_100": composite_100,
        "verdict": verdict,
        "penalty_flags_applied": penalties_applied,
        "section_scores": {key: round(value * 20, 1) for key, value in section_scores.items()},
        "sections_scored": len(section_scores),
        "sections_total": len(SECTION_WEIGHTS),
        "weight_coverage_pct": round(total_available_weight * 100, 1),
        "top3_sections": [section for section, _ in scored_sections[:3]],
        "bottom3_sections": [section for section, _ in scored_sections[-3:]],
        "confidence_adjusted_score": round(composite_100 * (0.5 + conf_score / 200), 1),
    }


def section_average(scores: dict[str, int | None]) -> float | None:
    return mean_present([score for score in scores.values() if score is not None])


def _score_net_debt(value: Any) -> int | None:
    numeric = to_float(value)
    if numeric is None:
        return None
    if numeric < 0:
        return 5
    if numeric <= 0.5:
        return 4
    if numeric <= 2:
        return 3
    if numeric <= 4:
        return 2
    return 1


def _score_rsi(value: Any) -> int | None:
    numeric = to_float(value)
    if numeric is None:
        return None
    if 35 <= numeric <= 55:
        return 5
    if 28 <= numeric < 35 or 55 < numeric <= 65:
        return 4
    if 65 < numeric <= 75:
        return 3
    if numeric < 28:
        return 2
    return 1


def _score_recommendation(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).lower()
    if "strong" in text and "buy" in text:
        return 5
    if "buy" in text:
        return 4
    if "hold" in text:
        return 3
    if "sell" in text:
        return 1
    return 3


def _apply_penalties(composite_100: float, company_data: dict[str, Any], penalties_applied: list[str]) -> float:
    pledge = to_float(company_data.get("pledge_pct"), 0) or 0
    altman = to_float(company_data.get("altman_z_score"))
    piotroski = to_float(company_data.get("piotroski_score"))
    net_debt_ebitda = to_float(company_data.get("net_debt_ebitda"), 0) or 0
    gnpa = to_float(company_data.get("gnpa_ratio"), 0) or 0
    checks = [
        (pledge > 30, 0.85, f"HIGH_PLEDGE_{pledge:.0f}pct"),
        (altman is not None and altman < 1.8, 0.90, f"ALTMAN_Z_{altman:.1f}" if altman is not None else "ALTMAN_Z"),
        (piotroski is not None and piotroski < 3, 0.95, f"PIOTROSKI_{piotroski:.0f}" if piotroski is not None else "PIOTROSKI"),
        (bool(company_data.get("audit_qualified_opinion")), 0.85, "QUALIFIED_AUDIT_OPINION"),
        (bool(company_data.get("sell_cluster_6m")), 0.90, "INSIDER_CLUSTER_SELLING"),
        (net_debt_ebitda > 5, 0.90, f"NET_DEBT_EBITDA_{net_debt_ebitda:.1f}x"),
        (gnpa > 7, 0.85, f"HIGH_GNPA_{gnpa:.1f}pct"),
        (bool(company_data.get("fcf_negative_3_consecutive")), 0.92, "FCF_NEGATIVE_3YR"),
    ]
    for triggered, multiplier, flag in checks:
        if triggered:
            composite_100 *= multiplier
            penalties_applied.append(flag)
    return composite_100
