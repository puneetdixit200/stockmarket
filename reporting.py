from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from common import clean_value, flatten_records, now_iso, to_float
from calculators.peer_comparison import build_peer_comparison
from universe.sector_classifier import key_monitoring_metrics


OUTPUT_FILENAMES = [
    "master_data_raw.csv",
    "master_scores.csv",
    "top50_opportunities.csv",
    "red_flags.csv",
    "technical_opportunities.csv",
    "dcf_valuations.csv",
    "peer_comparison.csv",
    "monitoring_dashboard.csv",
    "run_summary.txt",
]


def write_all_outputs(
    output_dir: str | Path,
    raw_records: list[dict[str, Any]],
    enriched_records: list[dict[str, Any]],
    run_stats: dict[str, Any],
) -> dict[str, Path]:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    written["master_data_raw.csv"] = _write_csv(path / "master_data_raw.csv", raw_records)
    written["master_scores.csv"] = _write_csv(path / "master_scores.csv", _master_scores(enriched_records))
    top50 = _top_opportunities(enriched_records)
    written["top50_opportunities.csv"] = _write_csv(path / "top50_opportunities.csv", top50)
    written["red_flags.csv"] = _write_csv(path / "red_flags.csv", _red_flags(enriched_records))
    written["technical_opportunities.csv"] = _write_csv(path / "technical_opportunities.csv", _technical_opportunities(enriched_records))
    written["dcf_valuations.csv"] = _write_csv(path / "dcf_valuations.csv", _dcf_valuations(enriched_records))
    written["peer_comparison.csv"] = _write_csv(path / "peer_comparison.csv", build_peer_comparison(enriched_records).to_dict("records"))
    written["monitoring_dashboard.csv"] = _write_csv(path / "monitoring_dashboard.csv", _monitoring_dashboard(top50))
    summary_path = path / "run_summary.txt"
    summary_path.write_text(_run_summary(run_stats, enriched_records), encoding="utf-8")
    written["run_summary.txt"] = summary_path
    return written


def _write_csv(path: Path, records: list[dict[str, Any]] | pd.DataFrame) -> Path:
    if isinstance(records, pd.DataFrame):
        frame = records
    else:
        frame = pd.DataFrame(flatten_records(records)) if records else pd.DataFrame()
    frame.to_csv(path, index=False)
    return path


def _master_scores(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for record in sorted(records, key=lambda item: to_float(item.get("composite_score_100"), -1) or -1, reverse=True):
        row = {
            "Ticker": record.get("symbol"),
            "Name": record.get("company_name"),
            "Sector": record.get("sector"),
            "Type": record.get("company_type"),
            "Price": record.get("last_price"),
            "MarketCap": record.get("market_cap"),
            "DataConfidence": record.get("data_confidence_score"),
            "DataConfidenceGrade": record.get("data_confidence_grade"),
            "WeightCoveragePct": record.get("weight_coverage_pct"),
            "CompositeScore100": record.get("composite_score_100"),
            "ConfidenceAdjustedScore": record.get("confidence_adjusted_score"),
            "Verdict": record.get("verdict"),
            "PenaltyFlags": ",".join(record.get("penalty_flags_applied") or []),
            "Top3Sections": ",".join(record.get("top3_sections") or []),
            "Bottom3Sections": ",".join(record.get("bottom3_sections") or []),
        }
        for section, score in (record.get("section_scores") or {}).items():
            row[f"{section}_subtotal_20"] = score
        for section, params in (record.get("parameter_scores") or {}).items():
            for param, score in params.items():
                row[f"{section}_{param}_score"] = score
        rows.append(clean_value(row))
    return rows


def _top_opportunities(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    candidates = [
        record
        for record in records
        if (to_float(record.get("composite_score_100"), 0) or 0) > 65
        and (to_float(record.get("data_confidence_score"), 0) or 0) > 50
    ]
    for record in sorted(candidates, key=lambda item: to_float(item.get("composite_score_100"), 0) or 0, reverse=True)[:50]:
        rows.append(
            {
                "Ticker": record.get("symbol"),
                "Name": record.get("company_name"),
                "Sector": record.get("sector"),
                "Type": record.get("company_type"),
                "CompositeScore100": record.get("composite_score_100"),
                "ConfidenceGrade": record.get("data_confidence_grade"),
                "Thesis": _thesis(record),
                "BearDCF": record.get("bear_dcf_value"),
                "BaseDCF": record.get("base_dcf_value"),
                "BullDCF": record.get("bull_dcf_value"),
                "AnalystConsensusTarget": record.get("target_mean_price"),
                "Verdict": record.get("verdict"),
            }
        )
    return rows


def _red_flags(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        flags = record.get("risk_flags") or []
        if flags:
            rows.append(
                {
                    "Ticker": record.get("symbol"),
                    "Name": record.get("company_name"),
                    "FlagCount": len(flags),
                    "Flags": ",".join(flags),
                    "PledgePct": record.get("pledge_pct"),
                    "AltmanZ": record.get("altman_z_score"),
                    "Piotroski": record.get("piotroski_score"),
                    "NetDebtEBITDA": record.get("net_debt_ebitda"),
                    "GNPA": record.get("gnpa_ratio"),
                    "DataConfidence": record.get("data_confidence_score"),
                }
            )
    return sorted(rows, key=lambda row: row["FlagCount"], reverse=True)


def _technical_opportunities(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        rsi = to_float(record.get("rsi_14"))
        distance_low = to_float(record.get("distance_from_52w_low_pct"))
        composite = to_float(record.get("composite_score_100"), 0) or 0
        confidence = to_float(record.get("data_confidence_score"), 0) or 0
        piotroski = to_float(record.get("piotroski_score"), 0) or 0
        if rsi is not None and 28 <= rsi <= 50 and distance_low is not None and distance_low <= 15 and composite > 55 and confidence > 50 and piotroski > 5:
            rows.append(
                {
                    "Ticker": record.get("symbol"),
                    "Name": record.get("company_name"),
                    "RSI14": rsi,
                    "DistanceFrom52wLowPct": distance_low,
                    "CompositeScore100": composite,
                    "SupportLevel": record.get("support_level"),
                    "SuggestedStopLoss": record.get("suggested_stop_loss"),
                    "PotentialReturnTo52wHighPct": record.get("potential_return_to_52w_high_pct"),
                }
            )
    return rows


def _dcf_valuations(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        rows.append(
            {
                "Ticker": record.get("symbol"),
                "CurrentPrice": record.get("last_price"),
                "BearDCF": record.get("bear_dcf_value"),
                "BaseDCF": record.get("base_dcf_value"),
                "BullDCF": record.get("bull_dcf_value"),
                "BearMoS%": record.get("bear_mos_pct"),
                "BaseMoS%": record.get("base_mos_pct"),
                "BullMoS%": record.get("bull_mos_pct"),
                "WACCUsed%": record.get("wacc_pct"),
                "BetaUsed": record.get("beta_used"),
                "RevenueGrowthAssumed%": record.get("revenue_growth_assumed_pct"),
                "EBITMarginAssumed%": record.get("ebit_margin_assumed_pct"),
                "TerminalGrowth%": record.get("base_terminal_growth_pct"),
                "DataConfidence": record.get("data_confidence_score"),
                "KeyFlags": ",".join(record.get("key_flags") or []),
            }
        )
    return rows


def _monitoring_dashboard(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        company_type = record.get("Type") or record.get("company_type") or "GENERAL"
        score = to_float(record.get("CompositeScore100") or record.get("composite_score_100"), 0) or 0
        risk = to_float(record.get("risk_matrix_subtotal_20") or record.get("risk_score"), 10) or 10
        rows.append(
            {
                "Ticker": record.get("Ticker") or record.get("symbol"),
                "Name": record.get("Name") or record.get("company_name"),
                "MetricsToTrack": ", ".join(key_monitoring_metrics(company_type)),
                "ExitTrigger1": "Sell if composite score falls below 50",
                "ExitTrigger2": "Sell if two new red flags appear in one quarter",
                "ExitTrigger3": "Review if data confidence falls below 45",
                "NextKnownCatalystDate": record.get("next_earnings_date") or "",
                "BearTarget": record.get("BearDCF") or record.get("bear_dcf_value"),
                "BaseTarget": record.get("BaseDCF") or record.get("base_dcf_value"),
                "BullTarget": record.get("BullDCF") or record.get("bull_dcf_value"),
                "MaxPositionSizePct": round(min(max(score / 20 - risk / 10, 1), 8), 1),
            }
        )
    return rows


def _thesis(record: dict[str, Any]) -> str:
    sections = record.get("top3_sections") or []
    names = ", ".join(section.replace("_", " ") for section in sections[:2]) or "balanced fundamentals"
    mos = to_float(record.get("base_mos_pct"))
    mos_text = f" with {mos:.1f}% base DCF margin of safety" if mos is not None else ""
    return f"Strong {names}{mos_text}; confidence grade {record.get('data_confidence_grade')}."


def _run_summary(run_stats: dict[str, Any], records: list[dict[str, Any]]) -> str:
    attempted = run_stats.get("companies_attempted", len(records))
    confidence_counts = {grade: sum(1 for row in records if row.get("data_confidence_grade") == grade) for grade in ["A", "B", "C", "D", "F"]}
    low_confidence = sum(1 for row in records if (to_float(row.get("data_confidence_score"), 0) or 0) < 50)
    red_flag_rows = _red_flags(records)
    gaps = []
    for row in records:
        missing = row.get("missing_critical_fields") or []
        if missing:
            gaps.append(f"{row.get('symbol')}: {', '.join(missing[:5])}")
    return "\n".join(
        [
            "RUN SUMMARY",
            "===========",
            f"Timestamp: {run_stats.get('completed_at') or now_iso()}",
            f"Mode: {run_stats.get('mode')}",
            "Universe: Nifty LargeMidcap 250",
            "PROCESSING RESULTS",
            "------------------",
            f"Total companies attempted: {attempted}",
            f"Successfully fully scored: {sum(1 for row in records if (to_float(row.get('data_confidence_score'), 0) or 0) >= 75)}",
            f"Partially scored (>50% confidence): {sum(1 for row in records if 50 <= (to_float(row.get('data_confidence_score'), 0) or 0) < 75)}",
            f"Scored with low confidence (<50%): {low_confidence}",
            f"Failed (no data): {run_stats.get('companies_failed', 0)}",
            "DATA SOURCE PERFORMANCE",
            "-----------------------",
            f"yfinance success rate: {run_stats.get('yfinance_success', 0)}/{attempted}",
            f"Indian Stock API success rate: {run_stats.get('indian_stock_api_success', 0)}/{attempted}",
            f"NSE API success rate: {run_stats.get('nse_success', 0)}/{attempted}",
            f"Screener success rate: {run_stats.get('screener_success', 0)}/{run_stats.get('screener_attempted', 0)}",
            f"Macro data: {run_stats.get('macro_status', 'OK')}",
            f"G-Sec yield source: {run_stats.get('gsec_yield_source')}",
            "DATA QUALITY SUMMARY",
            "--------------------",
            f"Companies with full data (confidence A): {confidence_counts['A']}",
            f"Companies with good data (confidence B): {confidence_counts['B']}",
            f"Companies with partial data (confidence C): {confidence_counts['C']}",
            f"Companies with poor data (confidence D/F): {confidence_counts['D'] + confidence_counts['F']}",
            "COMPANIES WITH SPECIFIC DATA GAPS",
            "----------------------------------",
            "\n".join(gaps) if gaps else "None",
            "SCREENER BLOCKING",
            "-----------------",
            run_stats.get("screener_note") or "No Screener blocking detected during this run.",
            "RED FLAGS FOUND",
            "---------------",
            f"Companies with 3+ red flags: {sum(1 for row in red_flag_rows if row['FlagCount'] >= 3)}",
            f"Companies with pledge > 25%: {sum(1 for row in records if (to_float(row.get('pledge_pct'), 0) or 0) > 25)}",
            "RUNTIME",
            "-------",
            f"Total runtime: {run_stats.get('runtime_seconds', 0):.1f}s",
            f"Average per company: {run_stats.get('runtime_seconds', 0) / attempted if attempted else 0:.2f}s",
            "NEXT STEPS",
            "----------",
            run_stats.get("next_steps") or "Run with --mode FULL to process the entire live universe.",
        ]
    )
