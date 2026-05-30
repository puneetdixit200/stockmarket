from __future__ import annotations

from typing import Any

import pandas as pd

from common import to_float


MEDIAN_FIELDS = [
    "pe_ratio",
    "pb_ratio",
    "ev_ebitda",
    "ev_sales",
    "roe_pct",
    "roce_pct",
    "net_margin_pct",
    "ebitda_margin_pct",
    "revenue_cagr_5y_pct",
    "debt_equity",
]


def build_sector_median_database(universe_df: pd.DataFrame, all_company_data: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(all_company_data)
    if frame.empty:
        return pd.DataFrame(columns=["sector", "company_count", *MEDIAN_FIELDS])
    if "sector" not in frame:
        frame["sector"] = "Unknown"
    rows = []
    for sector, group in frame.groupby(frame["sector"].fillna("Unknown")):
        row = {"sector": sector, "company_count": len(group)}
        for field in MEDIAN_FIELDS:
            values = [to_float(value) for value in group.get(field, pd.Series(dtype=float)).tolist()]
            numeric = [value for value in values if value is not None]
            row[field] = float(pd.Series(numeric).median()) if numeric else None
        rows.append(row)
    return pd.DataFrame(rows)
