from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd


SOURCE_UNAVAILABLE = "unavailable"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def to_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    if isinstance(value, (int, float, np.number)):
        if math.isnan(float(value)) or math.isinf(float(value)):
            return default
        return float(value)
    if isinstance(value, str):
        cleaned = (
            value.replace(",", "")
            .replace("%", "")
            .replace("x", "")
            .replace("₹", "")
            .strip()
        )
        if cleaned in {"", "-", "NA", "N/A", "nan", "None"}:
            return default
        scale = 1.0
        lowered = cleaned.lower()
        if lowered.endswith("cr"):
            cleaned = cleaned[:-2].strip()
        elif lowered.endswith("crore") or lowered.endswith("crores"):
            cleaned = cleaned.rsplit(" ", 1)[0]
        elif lowered.endswith("lakh") or lowered.endswith("lakhs"):
            cleaned = cleaned.rsplit(" ", 1)[0]
            scale = 0.01
        try:
            return float(cleaned) * scale
        except ValueError:
            return default
    return default


def safe_div(numerator: Any, denominator: Any, default: float | None = None) -> float | None:
    num = to_float(numerator)
    den = to_float(denominator)
    if num is None or den in (None, 0):
        return default
    return num / den


def clean_value(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        if math.isnan(float(value)) or math.isinf(float(value)):
            return None
        return float(value)
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): clean_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean_value(v) for v in value]
    return value


def json_dumps(value: Any) -> str:
    return json.dumps(clean_value(value), sort_keys=True, ensure_ascii=False)


def flatten_records(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    keys: set[str] = set()
    for record in records:
        keys.update(record.keys())
    ordered = sorted(keys)
    return [{key: clean_value(record.get(key)) for key in ordered} for record in records]


def first_present(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, float) and math.isnan(value):
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        return value
    return None


def cagr(values: Sequence[Any]) -> float | None:
    cleaned = [to_float(v) for v in values if to_float(v) not in (None, 0)]
    if len(cleaned) < 2:
        return None
    start, end = cleaned[0], cleaned[-1]
    if start is None or end is None or start <= 0:
        return None
    periods = len(cleaned) - 1
    return (end / start) ** (1 / periods) - 1


def bps_change(new_value: Any, old_value: Any) -> float | None:
    change = safe_div(to_float(new_value), 1)
    old = to_float(old_value)
    if change is None or old is None:
        return None
    return (change - old) * 10000


def score_descending(value: Any, bands: Sequence[tuple[float, int]], default: int | None = None) -> int | None:
    numeric = to_float(value)
    if numeric is None:
        return default
    for threshold, score in bands:
        if numeric >= threshold:
            return score
    return bands[-1][1] if bands else default


def score_ascending(value: Any, bands: Sequence[tuple[float, int]], default: int | None = None) -> int | None:
    numeric = to_float(value)
    if numeric is None:
        return default
    for threshold, score in bands:
        if numeric <= threshold:
            return score
    return bands[-1][1] if bands else default


def score_discount(discount_pct: Any, strong: float, good: float, neutral: float, expensive: float) -> int | None:
    value = to_float(discount_pct)
    if value is None:
        return None
    if value >= strong:
        return 5
    if value >= good:
        return 4
    if value >= neutral:
        return 3
    if value >= expensive:
        return 2
    return 1


def add_sourced_field(row: dict[str, Any], field: str, value: Any, source: str, fetched_at: str | None = None) -> None:
    row[field] = clean_value(value)
    row[f"{field}_source"] = source
    row[f"{field}_fetched_at"] = fetched_at or now_iso()


def normalise_symbol(symbol: str) -> str:
    return symbol.upper().replace(".NS", "").replace(".BO", "").strip()


def mean_present(values: Iterable[Any]) -> float | None:
    cleaned = [to_float(v) for v in values]
    numeric = [v for v in cleaned if v is not None]
    if not numeric:
        return None
    return float(sum(numeric) / len(numeric))
