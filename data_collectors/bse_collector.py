from __future__ import annotations

import logging
from typing import Any

import requests

from common import clean_value, now_iso


class BSECollector:
    def __init__(self, session: requests.Session | None = None, timeout: int = 20) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout
        self.session.headers.update({"User-Agent": "Mozilla/5.0 Indian Equity Research Platform"})

    def fetch_quote_by_code(self, bse_code: str) -> dict[str, Any]:
        url = "https://api.bseindia.com/BseIndiaAPI/api/StockReachGraph/w"
        try:
            response = self.session.get(url, params={"scripcode": bse_code, "flag": "0"}, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
            return {"bse_code": bse_code, "quote": payload, "_source": "bse_api", "_fetched_at": now_iso()}
        except Exception as exc:
            logging.warning("BSE quote fetch failed for %s: %s", bse_code, exc)
            return {"bse_code": bse_code, "_source": "unavailable", "_error": str(exc)}

    def fetch_corporate_filings(self, bse_code: str) -> dict[str, Any]:
        url = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"
        try:
            response = self.session.get(
                url,
                params={"strCat": "-1", "strPrevDate": "", "strScrip": bse_code, "strSearch": "P", "strToDate": ""},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return {"bse_code": bse_code, "filings": response.json(), "_source": "bse_api", "_fetched_at": now_iso()}
        except Exception as exc:
            logging.warning("BSE filings fetch failed for %s: %s", bse_code, exc)
            return {"bse_code": bse_code, "filings": [], "_source": "unavailable", "_error": str(exc)}
