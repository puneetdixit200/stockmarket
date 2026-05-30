# Indian Equity Research Platform Design

## Goal

Build a Python codebase from the supplied `INDIAN EQUITY RESEARCH PLATFORM.docx` that can process the Nifty LargeMidcap 250 universe, use only free data sources, score companies across the requested 12 sections, and write the required research output files.

## Architecture

The project keeps the document's folder layout: `universe`, `data_collectors`, `calculators`, `scoring`, `confidence`, `database`, `outputs`, `tests`, and `main.py`. The pipeline has deterministic fixture mode for repeatable verification and live mode for NSE/yfinance/API-backed collection.

## Data Flow

1. Fetch or load a universe.
2. Collect data from yfinance, the hosted Indian Stock Market API, NSE, and optional Screener requests.
3. Merge data with source and timestamp columns.
4. Calculate DCF, valuation, quality, growth, cash-flow, governance, moat, risk, technical, confidence, and composite scores.
5. Write the required CSV/text outputs and SQLite state.

## Error Handling

Collectors return structured unavailable/error records instead of raising through the whole run. The pipeline records source success and data gaps in `run_summary.txt`.

## Testing

Unit tests cover confidence scoring, DCF, composite penalties, technical indicators, and end-to-end output creation from fixtures.
