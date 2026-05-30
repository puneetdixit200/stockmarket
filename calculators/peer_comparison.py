from __future__ import annotations

from typing import Any

import pandas as pd

from common import to_float


PEER_METRICS = ["pe_ratio", "pb_ratio", "ev_ebitda", "ev_sales", "roe_pct", "roce_pct", "net_margin_pct", "ebitda_margin_pct", "revenue_cagr_5y_pct", "debt_equity"]


def build_peer_comparison(records: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(records)
    if frame.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for _, company in frame.iterrows():
        sector = company.get("sector") or "Unknown"
        sector_group = frame[frame.get("sector", pd.Series(index=frame.index)).fillna("Unknown") == sector].copy()
        market_cap = to_float(company.get("market_cap"), 0) or 0
        sector_group["_distance"] = sector_group.get("market_cap", 0).apply(lambda value: abs((to_float(value, 0) or 0) - market_cap))
        peers = sector_group[sector_group.get("symbol") != company.get("symbol")].sort_values("_distance").head(3)
        row = {
            "symbol": company.get("symbol"),
            "name": company.get("company_name"),
            "sector": sector,
            "closest_peers": ",".join(peers.get("symbol", pd.Series(dtype=str)).astype(str).tolist()),
        }
        premium_notes: list[str] = []
        for metric in PEER_METRICS:
            own_value = to_float(company.get(metric))
            median_value = _median(sector_group.get(metric, pd.Series(dtype=float)).tolist())
            peer_value = _median(peers.get(metric, pd.Series(dtype=float)).tolist()) if not peers.empty else median_value
            row[f"{metric}_own"] = own_value
            row[f"{metric}_sector_median"] = median_value
            row[f"{metric}_closest_peer_avg"] = peer_value
            discount = _discount(own_value, peer_value)
            row[f"{metric}_premium_discount_pct"] = discount
            if discount is not None and metric in {"pe_ratio", "pb_ratio", "ev_ebitda"}:
                premium_notes.append(f"{metric}:{'discount' if discount > 0 else 'premium'} {abs(discount):.1f}%")
        row["relative_valuation_note"] = "; ".join(premium_notes[:4])
        rows.append(row)
    return pd.DataFrame(rows)


def _median(values: list[Any]) -> float | None:
    numeric = [to_float(value) for value in values]
    numeric = [value for value in numeric if value is not None]
    if not numeric:
        return None
    return float(pd.Series(numeric).median())


def _discount(value: float | None, peer_value: float | None) -> float | None:
    if value is None or peer_value in (None, 0):
        return None
    return (peer_value - value) / peer_value * 100
