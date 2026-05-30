from __future__ import annotations

from typing import Any

from common import score_ascending, score_descending
from scoring.scoring_engine import score_company_sections


def score_insurance_sections(metrics: dict[str, Any]) -> dict[str, dict[str, int | None]]:
    sections = score_company_sections({**metrics, "_company_type_override": "GENERAL"}, "GENERAL")
    sections["profitability"].update(
        {
            "combined_ratio": score_ascending(metrics.get("combined_ratio"), [(90, 5), (95, 4), (100, 3), (105, 2), (10**9, 1)]),
            "solvency": score_descending(metrics.get("solvency_ratio"), [(2.0, 5), (1.8, 4), (1.5, 3), (1.2, 2), (-10**9, 1)]),
        }
    )
    sections["growth"].update(
        {
            "premium_growth": score_descending(metrics.get("premium_growth"), [(20, 5), (12, 4), (8, 3), (3, 2), (-10**9, 1)]),
            "persistency": score_descending(metrics.get("persistency_ratio"), [(85, 5), (75, 4), (65, 3), (55, 2), (-10**9, 1)]),
        }
    )
    return sections
