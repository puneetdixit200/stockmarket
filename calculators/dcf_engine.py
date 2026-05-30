from __future__ import annotations

from typing import Any

from common import cagr, safe_div, to_float


DCF_SCENARIOS = {
    "bear": {"growth_haircut": 0.60, "margin_haircut": 0.90, "terminal_growth": 0.035},
    "base": {"growth_haircut": 1.00, "margin_haircut": 1.00, "terminal_growth": 0.045},
    "bull": {"growth_haircut": 1.25, "margin_haircut": 1.08, "terminal_growth": 0.055},
}


def run_dcf_engine(data: dict[str, Any], macro: dict[str, Any]) -> dict[str, Any]:
    revenue_history = [to_float(v) for v in data.get("revenue_history", []) if to_float(v) is not None]
    ebit_history = [to_float(v) for v in data.get("ebit_history", []) if to_float(v) is not None]
    latest_revenue = revenue_history[-1] if revenue_history else to_float(data.get("revenue"), 0)
    latest_ebit = ebit_history[-1] if ebit_history else to_float(data.get("ebit"), 0)
    shares = to_float(data.get("shares_outstanding"))
    if shares and shares > 10_000_000:
        shares_cr = shares / 10_000_000
    else:
        shares_cr = shares or 1
    revenue_growth = cagr(revenue_history) if len(revenue_history) >= 2 else 0.08
    revenue_growth = max(min(revenue_growth or 0.08, 0.22), -0.05)
    ebit_margin = safe_div(latest_ebit, latest_revenue, 0.14) or 0.14
    tax_rate = min(max(to_float(data.get("tax_rate"), 0.25) or 0.25, 0.15), 0.35)
    beta = to_float(data.get("beta"), 1.0) or 1.0
    gsec = to_float(macro.get("gsec_10yr_yield"), 7.0) or 7.0
    market_risk_premium = to_float(macro.get("market_risk_premium"), 6.0) or 6.0
    cost_of_equity = gsec + beta * market_risk_premium
    debt_equity = max(to_float(data.get("debt_equity"), 0) or 0, 0)
    after_tax_debt = max(gsec + 1.5, 6.5) * (1 - tax_rate)
    equity_weight = 1 / (1 + debt_equity)
    debt_weight = 1 - equity_weight
    wacc_pct = equity_weight * cost_of_equity + debt_weight * after_tax_debt
    wacc = max(wacc_pct / 100, 0.085)
    flags: list[str] = []
    if latest_ebit is not None and latest_ebit < 0:
        flags.append("NEGATIVE_EBIT")
    if macro.get("gsec_10yr_yield_source") == "estimated":
        flags.append("USING_ESTIMATED_GSEC")
    results: dict[str, Any] = {
        "wacc_pct": round(wacc_pct, 2),
        "beta_used": beta,
        "revenue_growth_assumed_pct": round(revenue_growth * 100, 2),
        "ebit_margin_assumed_pct": round(ebit_margin * 100, 2),
        "key_flags": flags,
    }
    current_price = to_float(data.get("last_price"), 0) or 0
    for scenario_name, scenario in DCF_SCENARIOS.items():
        growth = revenue_growth * scenario["growth_haircut"]
        margin = max(ebit_margin * scenario["margin_haircut"], 0.01)
        terminal_growth = scenario["terminal_growth"]
        value, terminal_pct = _discounted_value(latest_revenue or 0, growth, margin, tax_rate, wacc, terminal_growth)
        if terminal_pct > 75:
            flags.append("HIGH_TERMINAL_VALUE_PCT")
        equity_value = max(value - (to_float(data.get("net_debt"), 0) or 0), 0)
        per_share = equity_value / shares_cr if shares_cr else 0
        results[f"{scenario_name}_dcf_value"] = round(per_share, 2)
        results[f"{scenario_name}_mos_pct"] = round((per_share - current_price) / per_share * 100, 2) if per_share else None
        results[f"{scenario_name}_terminal_growth_pct"] = round(terminal_growth * 100, 2)
    results["key_flags"] = sorted(set(flags))
    return results


def _discounted_value(revenue: float, growth: float, margin: float, tax_rate: float, wacc: float, terminal_growth: float) -> tuple[float, float]:
    forecast_value = 0.0
    current_revenue = revenue
    last_fcf = 0.0
    for year in range(1, 6):
        current_revenue *= 1 + growth
        nopat = current_revenue * margin * (1 - tax_rate)
        reinvestment = max(growth, 0) * current_revenue * 0.18
        fcf = nopat - reinvestment
        forecast_value += fcf / ((1 + wacc) ** year)
        last_fcf = fcf
    spread = max(wacc - terminal_growth, 0.02)
    terminal_value = last_fcf * (1 + terminal_growth) / spread
    terminal_present = terminal_value / ((1 + wacc) ** 5)
    total = forecast_value + terminal_present
    terminal_pct = terminal_present / total * 100 if total else 0
    return total, terminal_pct
