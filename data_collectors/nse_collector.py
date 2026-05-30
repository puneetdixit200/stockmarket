from __future__ import annotations

import logging
from typing import Any

import requests

from common import clean_value, normalise_symbol, now_iso


class NSESessionManager:
    def __init__(self, timeout: int = 20, session: requests.Session | None = None) -> None:
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 Indian Equity Research Platform",
                "Accept": "application/json,text/plain,*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.nseindia.com/",
            }
        )
        self._primed = False

    def prime(self) -> None:
        if self._primed:
            return
        self.session.get("https://www.nseindia.com", timeout=self.timeout)
        self._primed = True

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.prime()
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()


class NSECollector:
    def __init__(self, manager: NSESessionManager | None = None) -> None:
        self.manager = manager or NSESessionManager()

    def fetch_quote(self, symbol: str) -> dict[str, Any]:
        clean_symbol = normalise_symbol(symbol)
        url = "https://www.nseindia.com/api/quote-equity"
        try:
            payload = self.manager.get_json(url, {"symbol": clean_symbol})
            price_info = payload.get("priceInfo") or {}
            security_info = payload.get("securityInfo") or {}
            industry_info = payload.get("industryInfo") or {}
            row = {
                "symbol": clean_symbol,
                "last_price": price_info.get("lastPrice"),
                "previous_close": price_info.get("previousClose"),
                "year_high": price_info.get("weekHighLow", {}).get("max"),
                "year_low": price_info.get("weekHighLow", {}).get("min"),
                "isin": security_info.get("isin"),
                "sector": industry_info.get("macro"),
                "industry": industry_info.get("industry"),
                "_source": "nse_api",
                "_fetched_at": now_iso(),
            }
            return clean_value(row)
        except Exception as exc:
            logging.warning("NSE quote fetch failed for %s: %s", clean_symbol, exc)
            return {"symbol": clean_symbol, "_source": "unavailable", "_error": str(exc)}

    def fetch_corporate_actions(self, symbol: str) -> dict[str, Any]:
        clean_symbol = normalise_symbol(symbol)
        url = "https://www.nseindia.com/api/corporates-corporateActions"
        try:
            payload = self.manager.get_json(url, {"index": "equities", "symbol": clean_symbol})
            return {
                "symbol": clean_symbol,
                "corporate_actions": payload,
                "_source": "nse_api",
                "_fetched_at": now_iso(),
            }
        except Exception as exc:
            logging.warning("NSE corporate actions fetch failed for %s: %s", clean_symbol, exc)
            return {"symbol": clean_symbol, "corporate_actions": [], "_source": "unavailable", "_error": str(exc)}
