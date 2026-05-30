from __future__ import annotations

from typing import Any

from common import score_ascending, score_descending
from scoring.scoring_engine import score_company_sections


def score_bank_sections(metrics: dict[str, Any]) -> dict[str, dict[str, int | None]]:
    sections = score_company_sections({**metrics, "_company_type_override": "GENERAL"}, "GENERAL")
    sections["profitability"].update(
        {
            "nim": score_descending(metrics.get("nim"), [(4.5, 5), (3.5, 4), (3.0, 3), (2.5, 2), (-10**9, 1)]),
            "roa": score_descending(metrics.get("roa_pct"), [(1.8, 5), (1.2, 4), (0.8, 3), (0.4, 2), (-10**9, 1)]),
        }
    )
    sections["balance_sheet"].update(
        {
            "gnpa": score_ascending(metrics.get("gnpa_ratio"), [(1.5, 5), (2.5, 4), (4, 3), (7, 2), (10**9, 1)]),
            "capital_adequacy": score_descending(metrics.get("car"), [(18, 5), (15, 4), (12, 3), (10, 2), (-10**9, 1)]),
            "casa": score_descending(metrics.get("casa_ratio"), [(45, 5), (35, 4), (25, 3), (15, 2), (-10**9, 1)]),
        }
    )
    return sections
