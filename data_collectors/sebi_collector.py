from __future__ import annotations

import logging
from typing import Any

import requests

from common import now_iso, normalise_symbol


class SEBICollector:
    def __init__(self, session: requests.Session | None = None, timeout: int = 20) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout
        self.session.headers.update({"User-Agent": "Mozilla/5.0 Indian Equity Research Platform"})

    def fetch_insider_disclosures(self, symbol: str) -> dict[str, Any]:
        clean_symbol = normalise_symbol(symbol)
        url = "https://www.sebi.gov.in/sebiweb/ajax/home/getnewslistinfo.jsp"
        try:
            response = self.session.get(
                url,
                params={"nextValue": 1, "next": "n", "search": clean_symbol, "fromDate": "", "toDate": ""},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return {
                "symbol": clean_symbol,
                "raw_text": response.text[:10000],
                "_source": "sebi",
                "_fetched_at": now_iso(),
            }
        except Exception as exc:
            logging.warning("SEBI disclosure fetch failed for %s: %s", clean_symbol, exc)
            return {"symbol": clean_symbol, "raw_text": "", "_source": "unavailable", "_error": str(exc)}
