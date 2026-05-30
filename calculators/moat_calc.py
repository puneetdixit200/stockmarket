from __future__ import annotations

from typing import Any

from common import safe_div, to_float


def calculate_moat_metrics(data: dict[str, Any], sector_medians: dict[str, Any] | None = None) -> dict[str, Any]:
    sector_medians = sector_medians or {}
    gross_margin = to_float(data.get("gross_margin_pct"))
    sector_gross_margin = to_float(sector_medians.get("gross_margin_pct"))
    asset_turnover = safe_div(data.get("revenue"), data.get("total_assets"))
    sector_asset_turnover = to_float(sector_medians.get("asset_turnover"))
    rd_pct = safe_div(data.get("rd_expense"), data.get("revenue"))
    return {
        "pricing_power_spread_bps": _spread_bps(gross_margin, sector_gross_margin),
        "asset_turnover": asset_turnover,
        "asset_efficiency_spread_pct": _spread_pct(asset_turnover, sector_asset_turnover),
        "rd_intensity_pct": rd_pct * 100 if rd_pct is not None else None,
        "market_share_proxy_pct": to_float(data.get("market_share_pct")),
        "brand_moat_proxy": to_float(data.get("advertising_to_sales_pct")),
        "moat_score_proxy": _score_proxy(gross_margin, sector_gross_margin, asset_turnover, sector_asset_turnover, rd_pct),
    }


def _spread_bps(value: float | None, median: float | None) -> float | None:
    if value is None or median is None:
        return None
    return (value - median) * 100


def _spread_pct(value: float | None, median: float | None) -> float | None:
    if value is None or median in (None, 0):
        return None
    return (value - median) / median * 100


def _score_proxy(gross_margin: float | None, sector_gross_margin: float | None, asset_turnover: float | None, sector_asset_turnover: float | None, rd_pct: float | None) -> float | None:
    signals = []
    if gross_margin is not None and sector_gross_margin is not None:
        signals.append(1 if gross_margin > sector_gross_margin else 0)
    if asset_turnover is not None and sector_asset_turnover is not None:
        signals.append(1 if asset_turnover > sector_asset_turnover else 0)
    if rd_pct is not None:
        signals.append(1 if rd_pct > 0.02 else 0)
    if not signals:
        return None
    return sum(signals) / len(signals) * 100
