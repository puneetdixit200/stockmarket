from __future__ import annotations

import logging
import sqlite3
from io import StringIO
from typing import Any

import pandas as pd
import requests

from common import now_iso, normalise_symbol


NSE_INDEX_URL = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20LARGEMIDCAP%20250"
NIFTY_CSV_URL = "https://www.niftyindices.com/IndexConstituent/ind_niftylargemidcap250list.csv"


class UniverseFetchError(RuntimeError):
    """Raised when the live universe and cache are unavailable."""


class NiftyLargeMidcap250Provider:
    def __init__(
        self,
        session: requests.Session | None = None,
        timeout: int = 20,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout
        self.conn = conn
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 Indian Equity Research Platform",
                "Accept": "application/json,text/csv,*/*",
                "Referer": "https://www.nseindia.com/",
            }
        )

    def fetch(self) -> pd.DataFrame:
        errors: list[str] = []
        for fetcher in (self._fetch_from_nse, self._fetch_from_niftyindices_csv, self._fetch_from_cache):
            try:
                frame = fetcher()
                if not frame.empty:
                    frame = self._normalise_frame(frame)
                    self._cache_universe(frame)
                    return frame
            except Exception as exc:
                errors.append(f"{fetcher.__name__}: {exc}")
                logging.warning("Universe fetch failed via %s: %s", fetcher.__name__, exc)
        raise UniverseFetchError("Cannot fetch Nifty LargeMidcap 250 universe. " + " | ".join(errors))

    def _fetch_from_nse(self) -> pd.DataFrame:
        self.session.get("https://www.nseindia.com", timeout=self.timeout)
        response = self.session.get(NSE_INDEX_URL, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("data") or []
        return pd.DataFrame(rows)

    def _fetch_from_niftyindices_csv(self) -> pd.DataFrame:
        response = self.session.get(NIFTY_CSV_URL, timeout=self.timeout)
        response.raise_for_status()
        return pd.read_csv(StringIO(response.text))

    def _fetch_from_cache(self) -> pd.DataFrame:
        if self.conn is None:
            return pd.DataFrame()
        rows = self.conn.execute(
            "SELECT symbol, company_name, isin, industry, series, weightage, fetched_at FROM universe"
        ).fetchall()
        return pd.DataFrame([dict(row) for row in rows])

    def _normalise_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        mapping = {
            "symbol": ["symbol", "Symbol", "SYMBOL"],
            "company_name": ["company_name", "Company Name", "companyName", "meta.companyName"],
            "isin": ["isin", "ISIN"],
            "industry": ["industry", "Industry", "sector", "Sector"],
            "series": ["series", "Series"],
            "weightage": ["weightage", "Weightage", "Weight(%)", "weight"],
        }
        rows: list[dict[str, Any]] = []
        for _, source in frame.iterrows():
            row: dict[str, Any] = {}
            for target, candidates in mapping.items():
                row[target] = next((source.get(c) for c in candidates if c in frame.columns), None)
            if row.get("symbol"):
                row["symbol"] = normalise_symbol(str(row["symbol"]))
                row["fetched_at"] = now_iso()
                rows.append(row)
        normalised = pd.DataFrame(rows).drop_duplicates(subset=["symbol"])
        return normalised.sort_values("symbol").reset_index(drop=True)

    def _cache_universe(self, frame: pd.DataFrame) -> None:
        if self.conn is None or frame.empty:
            return
        for row in frame.to_dict("records"):
            self.conn.execute(
                """
                INSERT INTO universe(symbol, company_name, isin, industry, series, weightage, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    company_name=excluded.company_name,
                    isin=excluded.isin,
                    industry=excluded.industry,
                    series=excluded.series,
                    weightage=excluded.weightage,
                    fetched_at=excluded.fetched_at
                """,
                (
                    row.get("symbol"),
                    row.get("company_name"),
                    row.get("isin"),
                    row.get("industry"),
                    row.get("series"),
                    row.get("weightage"),
                    row.get("fetched_at"),
                ),
            )
        self.conn.commit()
