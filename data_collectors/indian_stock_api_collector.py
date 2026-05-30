from __future__ import annotations

import logging
import os
from typing import Any, Iterable
from urllib.parse import urljoin

import requests

from common import clean_value, normalise_symbol, now_iso


DEFAULT_BASE_URL = "http://65.0.104.9/"


class IndianStockAPICollector:
    """Client for the REST API documented by 0xramm/Indian-Stock-Market-API."""

    def __init__(
        self,
        base_url: str | None = None,
        session: requests.Session | None = None,
        timeout: int = 20,
    ) -> None:
        self.base_url = (base_url or os.getenv("INDIAN_STOCK_API_BASE_URL") or DEFAULT_BASE_URL).rstrip("/") + "/"
        self.session = session or requests.Session()
        self.timeout = timeout

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.session.get(urljoin(self.base_url, path.lstrip("/")), params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def search(self, query: str) -> dict[str, Any]:
        try:
            payload = self._get("/search", {"q": query})
            payload["_source"] = "indian_stock_api"
            payload["_fetched_at"] = now_iso()
            return payload
        except Exception as exc:
            logging.warning("Indian Stock API search failed for %s: %s", query, exc)
            return {"status": "error", "query": query, "message": str(exc), "_source": "unavailable"}

    def fetch_stock(self, symbol: str) -> dict[str, Any]:
        clean_symbol = normalise_symbol(symbol)
        try:
            payload = self._get("/stock", {"symbol": clean_symbol, "res": "num"})
            data = payload.get("data") or {}
            data.update(
                {
                    "symbol": clean_symbol,
                    "ticker": payload.get("ticker") or f"{clean_symbol}.NS",
                    "exchange": payload.get("exchange") or "NSE",
                    "_source": "indian_stock_api",
                    "_fetched_at": now_iso(),
                }
            )
            return clean_value(data)
        except Exception as exc:
            logging.warning("Indian Stock API stock fetch failed for %s: %s", clean_symbol, exc)
            return {"symbol": clean_symbol, "_source": "unavailable", "_error": str(exc)}

    def fetch_batch(self, symbols: Iterable[str], batch_size: int = 40) -> dict[str, dict[str, Any]]:
        cleaned = [normalise_symbol(symbol) for symbol in symbols]
        results: dict[str, dict[str, Any]] = {}
        for start in range(0, len(cleaned), batch_size):
            batch = cleaned[start : start + batch_size]
            try:
                payload = self._get("/stock/list", {"symbols": ",".join(batch), "res": "num"})
                stocks = payload.get("data") or payload.get("results") or []
                if isinstance(stocks, dict):
                    iterable = stocks.values()
                else:
                    iterable = stocks
                for item in iterable:
                    symbol = normalise_symbol(str(item.get("symbol") or item.get("ticker") or ""))
                    if symbol:
                        item["_source"] = "indian_stock_api"
                        item["_fetched_at"] = now_iso()
                        results[symbol] = clean_value(dict(item))
            except Exception as exc:
                logging.warning("Indian Stock API batch failed for %s: %s", batch, exc)
                for symbol in batch:
                    results[symbol] = {"symbol": symbol, "_source": "unavailable", "_error": str(exc)}
        for symbol in cleaned:
            if symbol not in results:
                results[symbol] = self.fetch_stock(symbol)
        return results
