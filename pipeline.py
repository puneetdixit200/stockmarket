from __future__ import annotations

import argparse
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from calculators.cashflow_calc import calculate_cashflow_metrics
from calculators.dcf_engine import run_dcf_engine
from calculators.governance_calc import calculate_governance_metrics
from calculators.growth_calc import calculate_growth_metrics
from calculators.moat_calc import calculate_moat_metrics
from calculators.quality_calc import calculate_quality_metrics
from calculators.risk_calc import calculate_risk_metrics
from calculators.technical_calc import calculate_technical_indicators
from calculators.valuation_calc import calculate_valuation_metrics
from common import add_sourced_field, clean_value, first_present, now_iso, to_float
from confidence.data_confidence import calculate_data_confidence
from data_collectors.indian_stock_api_collector import IndianStockAPICollector
from data_collectors.macro_collector import MacroCollector
from data_collectors.nse_collector import NSECollector
from data_collectors.screener_collector import ScreenerCollector
from data_collectors.sector_median_collector import build_sector_median_database
from data_collectors.yfinance_collector import YFinanceCollector
from database.db import initialise_database
from reporting import write_all_outputs
from scoring.scoring_engine import calculate_composite_score, score_company_sections
from scoring.sector_adjustments import apply_sector_adjustments
from universe.nifty_largmidcap250 import NiftyLargeMidcap250Provider
from universe.sector_classifier import classify_company_type


@dataclass
class RunConfig:
    mode: str = "TEST"
    output_dir: str = "outputs"
    db_path: str = "database/stocks.db"
    limit: int | None = None
    symbols: list[str] | None = None
    offline_fixture: str | None = None
    skip_screener: bool = False
    screener_max_per_run: int = 25


class ResearchPipeline:
    def __init__(self, config: RunConfig) -> None:
        self.config = config
        self.conn = initialise_database(config.db_path)
        self.yfinance = YFinanceCollector()
        self.api = IndianStockAPICollector()
        self.nse = NSECollector()
        self.screener = ScreenerCollector()
        self.macro_collector = MacroCollector()

    def run(self) -> dict[str, Any]:
        started = time.perf_counter()
        raw_records = self._load_offline_fixture() if self.config.offline_fixture else self._collect_live_records()
        macro = self.macro_collector.fetch_macro_data()
        enriched_pre = [self._calculate_record(record, macro, {}) for record in raw_records]
        sector_medians_frame = build_sector_median_database(pd.DataFrame(enriched_pre), enriched_pre)
        sector_medians = {row["sector"]: row for row in sector_medians_frame.to_dict("records")}
        enriched_records = [self._calculate_record(record, macro, sector_medians.get(record.get("sector") or "Unknown", {})) for record in raw_records]
        completed = now_iso()
        run_stats = self._run_stats(raw_records, enriched_records, macro, started, completed)
        written = write_all_outputs(self.config.output_dir, raw_records, enriched_records, run_stats)
        return {"written": written, "run_stats": run_stats, "records": enriched_records}

    def _load_offline_fixture(self) -> list[dict[str, Any]]:
        fixture_path = Path(self.config.offline_fixture or "")
        records = json.loads(fixture_path.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise ValueError("offline fixture must contain a JSON array")
        return [clean_value(record) for record in records[: self.config.limit or len(records)]]

    def _collect_live_records(self) -> list[dict[str, Any]]:
        universe = self._universe()
        symbols = universe["symbol"].tolist()
        if self.config.symbols:
            requested = {symbol.upper().replace(".NS", "").replace(".BO", "") for symbol in self.config.symbols}
            universe = universe[universe["symbol"].isin(requested)]
            symbols = universe["symbol"].tolist()
        if self.config.limit:
            universe = universe.head(self.config.limit)
            symbols = symbols[: self.config.limit]
        api_batch = self.api.fetch_batch(symbols)
        records = []
        screener_attempts = 0
        for _, universe_row in universe.iterrows():
            symbol = universe_row["symbol"]
            yfinance_data = self.yfinance.collect_symbol(symbol)
            api_data = api_batch.get(symbol) or self.api.fetch_stock(symbol)
            nse_data = self.nse.fetch_quote(symbol)
            screener_data = {}
            if not self.config.skip_screener and screener_attempts < self.config.screener_max_per_run:
                screener_data = self.screener.collect_symbol(symbol)
                screener_attempts += 1
            records.append(self._merge_sources(dict(universe_row), yfinance_data, api_data, nse_data, screener_data))
        return records

    def _universe(self) -> pd.DataFrame:
        if self.config.symbols:
            rows = [{"symbol": symbol.upper().replace(".NS", "").replace(".BO", ""), "company_name": symbol, "industry": "", "sector": ""} for symbol in self.config.symbols]
            return pd.DataFrame(rows)
        provider = NiftyLargeMidcap250Provider(conn=self.conn)
        return provider.fetch()

    def _merge_sources(self, universe: dict[str, Any], yfinance_data: dict[str, Any], api_data: dict[str, Any], nse_data: dict[str, Any], screener_data: dict[str, Any]) -> dict[str, Any]:
        fetched_at = now_iso()
        symbol = universe.get("symbol")
        row: dict[str, Any] = {"symbol": symbol, "universe_fetched_at": universe.get("fetched_at") or fetched_at}
        add_sourced_field(row, "company_name", first_present(yfinance_data.get("company_name"), api_data.get("company_name"), universe.get("company_name"), symbol), _source(yfinance_data, api_data, universe), fetched_at)
        add_sourced_field(row, "sector", first_present(yfinance_data.get("sector"), api_data.get("sector"), nse_data.get("sector"), universe.get("industry"), "Unknown"), _source(yfinance_data, api_data, nse_data), fetched_at)
        add_sourced_field(row, "industry", first_present(yfinance_data.get("industry"), api_data.get("industry"), nse_data.get("industry"), universe.get("industry")), _source(yfinance_data, api_data, nse_data), fetched_at)
        for field in ("last_price", "previous_close", "year_high", "year_low", "volume", "market_cap", "pe_ratio", "dividend_yield", "book_value", "eps", "currency"):
            source, value = _first_sourced(field, yfinance_data, api_data, nse_data)
            add_sourced_field(row, field, value, source, fetched_at)
        for field in ("pb_ratio", "beta", "target_mean_price", "analyst_recommendation", "shares_outstanding", "enterprise_value"):
            add_sourced_field(row, field, yfinance_data.get(field), yfinance_data.get("_source", "unavailable"), fetched_at)
        for field in ("revenue_history", "pat_history", "ebit_history", "ebitda_history", "total_assets_history", "equity_history", "total_debt_history", "cfo_history", "capex_history", "price_history"):
            row[field] = yfinance_data.get(field) or []
            row[f"{field}_source"] = yfinance_data.get("_source", "unavailable")
            row[f"{field}_fetched_at"] = yfinance_data.get("_fetched_at") or fetched_at
        for field in ("promoter_pct", "pledge_pct", "roe_pct", "roce_pct"):
            if screener_data.get(field) is not None:
                add_sourced_field(row, field, screener_data.get(field), "screener", screener_data.get("_fetched_at") or fetched_at)
        row["source_status"] = {
            "yfinance": yfinance_data.get("_source"),
            "indian_stock_api": api_data.get("_source"),
            "nse_api": nse_data.get("_source"),
            "screener": screener_data.get("_source"),
        }
        return clean_value(row)

    def _calculate_record(self, raw: dict[str, Any], macro: dict[str, Any], sector_medians: dict[str, Any]) -> dict[str, Any]:
        data = dict(raw)
        company_type = classify_company_type(data.get("company_name"), data.get("sector"), data.get("industry"))
        data["company_type"] = company_type
        data.update(calculate_cashflow_metrics(data))
        data.update(calculate_quality_metrics(data))
        data["wacc_pct"] = 12.0
        data.update(run_dcf_engine(data, macro))
        data["base_dcf_value"] = data.get("base_dcf_value")
        data.update(calculate_valuation_metrics(data, sector_medians, macro))
        data.update(calculate_growth_metrics(data))
        data.update(calculate_governance_metrics(data))
        data.update(calculate_moat_metrics(data, sector_medians))
        if data.get("price_history"):
            data.update(calculate_technical_indicators(pd.DataFrame(data["price_history"])))
        data["sector_median_pe"] = sector_medians.get("pe_ratio")
        data.update({key: value for key, value in macro.items() if key not in data})
        data.update(calculate_risk_metrics(data))
        confidence = calculate_data_confidence(data, company_type)
        data["data_confidence_score"] = confidence["confidence_score"]
        data["data_confidence_grade"] = confidence["confidence_grade"]
        data["field_completeness"] = confidence["field_completeness"]
        data["missing_critical_fields"] = confidence["missing_critical_fields"]
        data["analyst_target_upside_pct"] = _upside(data.get("last_price"), data.get("target_mean_price"))
        section_scores = score_company_sections(data, company_type)
        section_scores = apply_sector_adjustments(section_scores, company_type, data)
        composite = calculate_composite_score(section_scores, data, confidence)
        data["parameter_scores"] = section_scores
        data.update(composite)
        return clean_value(data)

    def _run_stats(self, raw_records: list[dict[str, Any]], enriched_records: list[dict[str, Any]], macro: dict[str, Any], started: float, completed: str) -> dict[str, Any]:
        attempted = len(raw_records)
        return {
            "mode": self.config.mode,
            "companies_attempted": attempted,
            "companies_failed": sum(1 for row in raw_records if not row.get("last_price")),
            "completed_at": completed,
            "runtime_seconds": time.perf_counter() - started,
            "yfinance_success": _source_count(raw_records, "yfinance"),
            "indian_stock_api_success": _source_count(raw_records, "indian_stock_api"),
            "nse_success": _source_count(raw_records, "nse_api"),
            "screener_success": _source_count(raw_records, "screener"),
            "screener_attempted": min(attempted, self.config.screener_max_per_run) if not self.config.skip_screener else 0,
            "macro_status": "OK" if macro else "FAILED",
            "gsec_yield_source": macro.get("gsec_10yr_yield_source"),
            "next_steps": "Run with --mode FULL without --limit to process the full Nifty LargeMidcap 250 universe.",
        }


def _first_sourced(field: str, *sources: dict[str, Any]) -> tuple[str, Any]:
    for source in sources:
        value = source.get(field)
        if value is not None:
            return source.get("_source", "unavailable"), value
    return "unavailable", None


def _source(*sources: dict[str, Any]) -> str:
    for source in sources:
        if source.get("_source") and source.get("_source") != "unavailable":
            return source["_source"]
    return "unavailable"


def _source_count(records: list[dict[str, Any]], source_name: str) -> int:
    count = 0
    for row in records:
        status = row.get("source_status") or {}
        status_values = status.values() if isinstance(status, dict) else []
        field_sources = [value for key, value in row.items() if key.endswith("_source")]
        if any(value == source_name for value in status_values) or any(value == source_name for value in field_sources):
            count += 1
    return count


def _upside(price: Any, target: Any) -> float | None:
    price_f = to_float(price)
    target_f = to_float(target)
    if price_f in (None, 0) or target_f is None:
        return None
    return (target_f / price_f - 1) * 100


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Indian equity research platform.")
    parser.add_argument("--mode", choices=["FULL", "TEST", "RESUME"], default="TEST")
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--db-path", default="database/stocks.db")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--symbols", help="Comma-separated NSE symbols. Overrides live universe selection.")
    parser.add_argument("--offline-fixture", help="JSON fixture for deterministic local runs.")
    parser.add_argument("--skip-screener", action="store_true")
    parser.add_argument("--screener-max-per-run", type=int, default=25)
    return parser


def config_from_args(args: argparse.Namespace) -> RunConfig:
    symbols = [symbol.strip() for symbol in args.symbols.split(",")] if args.symbols else None
    return RunConfig(
        mode=args.mode,
        output_dir=args.output_dir,
        db_path=args.db_path,
        limit=args.limit,
        symbols=symbols,
        offline_fixture=args.offline_fixture,
        skip_screener=args.skip_screener,
        screener_max_per_run=args.screener_max_per_run,
    )
