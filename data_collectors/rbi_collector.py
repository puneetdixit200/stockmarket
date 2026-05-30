from __future__ import annotations

import logging
import re

import requests

from common import now_iso, to_float


class RBICollector:
    def __init__(self, session: requests.Session | None = None, timeout: int = 20) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout

    def fetch_gsec_10yr_yield(self) -> dict[str, float | str]:
        url = "https://www.rbi.org.in/Scripts/BS_NSDPDisplay.aspx"
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            matches = re.findall(r"10\s*Year[^0-9]{0,40}([0-9]+\.[0-9]+)", response.text, flags=re.I)
            for match in matches:
                value = to_float(match)
                if value is not None and 4 <= value <= 12:
                    return {"gsec_10yr_yield": value, "gsec_10yr_yield_source": "rbi", "fetched_at": now_iso()}
        except Exception as exc:
            logging.warning("RBI G-Sec yield fetch failed: %s", exc)
        return {"gsec_10yr_yield": 7.0, "gsec_10yr_yield_source": "estimated", "fetched_at": now_iso()}
