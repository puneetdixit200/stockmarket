from __future__ import annotations

import logging
import time
from typing import Any

import pandas as pd
import requests

from common import clean_value, normalise_symbol, now_iso


class ScreenerCollector:
    def __init__(self, sleep_seconds: float = 2.5, timeout: int = 20, session: requests.Session | None = None) -> None:
        self.sleep_seconds = sleep_seconds
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 Indian Equity Research Platform"})

    def collect_symbol(self, symbol: str) -> dict[str, Any]:
        clean_symbol = normalise_symbol(symbol)
        url = f"https://www.screener.in/company/{clean_symbol}/consolidated/"
        try:
            time.sleep(self.sleep_seconds)
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 404:
                response = self.session.get(f"https://www.screener.in/company/{clean_symbol}/", timeout=self.timeout)
            response.raise_for_status()
            tables = pd.read_html(response.text)
            extracted = self._extract_tables(tables)
            extracted.update({"symbol": clean_symbol, "_source": "screener", "_fetched_at": now_iso()})
            return clean_value(extracted)
        except Exception as exc:
            logging.warning("Screener fetch failed for %s: %s", clean_symbol, exc)
            return {"symbol": clean_symbol, "_source": "unavailable", "_error": str(exc)}

    def _extract_tables(self, tables: list[pd.DataFrame]) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for table in tables:
            if table.empty:
                continue
            first_column = str(table.columns[0])
            if "Unnamed" in first_column and table.shape[1] >= 2:
                labels = table.iloc[:, 0].astype(str).str.lower()
                values = table.iloc[:, -1]
                for label, value in zip(labels, values):
                    if "promoter" in label:
                        data["promoter_pct"] = value
                    elif "pledge" in label:
                        data["pledge_pct"] = value
                    elif "roe" in label:
                        data["roe_pct"] = value
                    elif "roce" in label:
                        data["roce_pct"] = value
            if table.shape[0] > 2 and table.shape[1] > 2:
                title = " ".join(str(c).lower() for c in table.columns)
                if "sales" in title or "revenue" in title:
                    data.setdefault("screener_tables_count", 0)
                    data["screener_tables_count"] += 1
        return data
