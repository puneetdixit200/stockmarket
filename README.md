# Indian Equity Research Platform

Python research pipeline for the Nifty LargeMidcap 250 universe. It collects free public market data, calculates valuation/quality/growth/cash-flow/governance/moat/risk/technical metrics, scores companies across the 12-section framework from the supplied product document, and writes the required analysis outputs.

The hosted REST API from `https://github.com/0xramm/Indian-Stock-Market-API.git` is integrated through `data_collectors/indian_stock_api_collector.py` as a live price and symbol fallback alongside yfinance, NSE, Screener, BSE, SEBI, RBI, and World Bank sources.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item config.env.example config.env
```

## Deterministic Test Run

This uses local fixtures and does not depend on market hours or external APIs.

```powershell
python main.py --mode TEST --offline-fixture tests/fixtures/sample_companies.json --output-dir outputs/test_run
```

## Live Runs

Run a small live sample:

```powershell
python main.py --mode TEST --symbols RELIANCE,TCS,HDFCBANK --skip-screener --output-dir outputs/live_sample
```

Run the full universe:

```powershell
python main.py --mode FULL --output-dir outputs/full_run
```

Full runs fetch the live Nifty LargeMidcap 250 universe from NSE, fall back to the public Nifty Indices CSV, and then to the SQLite universe cache if live endpoints are unavailable.

## Outputs

The pipeline writes:

- `master_data_raw.csv`
- `master_scores.csv`
- `top50_opportunities.csv`
- `red_flags.csv`
- `technical_opportunities.csv`
- `dcf_valuations.csv`
- `peer_comparison.csv`
- `monitoring_dashboard.csv`
- `run_summary.txt`

SQLite state is created under `database/stocks.db` using `database/schema.sql`.

## Verification

```powershell
pytest -q
python main.py --mode TEST --offline-fixture tests/fixtures/sample_companies.json --output-dir outputs/test_run
```
