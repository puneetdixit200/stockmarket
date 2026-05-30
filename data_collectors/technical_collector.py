from __future__ import annotations

from typing import Any

import pandas as pd

from calculators.technical_calc import calculate_technical_indicators


def collect_technical_from_history(price_history: list[dict[str, Any]], index_history: pd.DataFrame | None = None) -> dict[str, Any]:
    if not price_history:
        return {}
    frame = pd.DataFrame(price_history)
    return calculate_technical_indicators(frame, index_history)
