from __future__ import annotations

import logging
from typing import Any

import requests

from common import now_iso, to_float
from data_collectors.rbi_collector import RBICollector


class MacroCollector:
    def __init__(self, session: requests.Session | None = None, timeout: int = 20) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout
        self.rbi = RBICollector(self.session, timeout)

    def fetch_macro_data(self) -> dict[str, Any]:
        macro = self.rbi.fetch_gsec_10yr_yield()
        macro.update(
            {
                "india_gdp_growth": self._world_bank_latest("NY.GDP.MKTP.KD.ZG", 6.5),
                "india_cpi": self._world_bank_latest("FP.CPI.TOTL.ZG", 5.0),
                "usd_inr": 83.0,
                "brent_crude": 80.0,
                "macro_source": "world_bank_rbi_estimated",
                "macro_fetched_at": now_iso(),
            }
        )
        return macro

    def _world_bank_latest(self, indicator: str, fallback: float) -> float:
        url = f"https://api.worldbank.org/v2/country/IN/indicator/{indicator}"
        try:
            response = self.session.get(url, params={"format": "json", "per_page": 5}, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
            for row in payload[1]:
                value = to_float(row.get("value"))
                if value is not None:
                    return value
        except Exception as exc:
            logging.warning("World Bank fetch failed for %s: %s", indicator, exc)
        return fallback
