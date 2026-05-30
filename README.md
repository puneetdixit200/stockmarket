# Indian Equity Research Platform

Python research pipeline for Indian equities, built around the Nifty LargeMidcap 250 universe. The platform collects free public data, calculates financial and technical metrics, scores each company across a 12-section research framework, and writes analysis-ready CSV outputs plus a run summary.

The repository implements `INDIAN EQUITY RESEARCH PLATFORM.docx` and integrates the hosted REST API documented at `https://github.com/0xramm/Indian-Stock-Market-API.git`.

## What It Does

- Fetches the Nifty LargeMidcap 250 universe from NSE with Nifty Indices CSV and SQLite cache fallbacks.
- Collects market, fundamental, governance, macro, and technical inputs from free sources.
- Uses yfinance as the primary structured data source for price history, financial statements, ratios, estimates, and analyst fields.
- Uses the 0xramm Indian Stock Market API as a no-key REST fallback for live quote and search data.
- Adds NSE, Screener, BSE, SEBI, RBI, and World Bank collectors for source-specific data.
- Calculates valuation, quality, growth, cash-flow, governance, moat, risk, DCF, peer comparison, and technical indicators.
- Scores companies across the 12-section weighted framework and applies red-flag penalties.
- Writes the nine requested output files under a chosen output directory.
- Tracks field sources and fetch timestamps so low-confidence data does not look complete.

## Repository Layout

```text
.
|-- main.py                         # CLI entry point
|-- pipeline.py                     # Orchestrates collection, calculation, scoring, output
|-- reporting.py                    # Writes the nine output files and run summary
|-- common.py                       # Numeric, JSON, symbol, scoring, and source helpers
|-- config.env.example              # Runtime configuration template
|-- requirements.txt                # Runtime and test dependencies
|-- pyproject.toml                  # Project metadata and pytest config
|-- universe/
|   |-- nifty_largmidcap250.py      # Nifty LargeMidcap 250 provider and cache fallback
|   `-- sector_classifier.py        # Company type and monitoring metric helpers
|-- data_collectors/
|   |-- yfinance_collector.py       # Primary statements, ratios, estimates, OHLCV
|   |-- indian_stock_api_collector.py # 0xramm hosted REST API client
|   |-- nse_collector.py            # NSE quote and corporate action endpoints
|   |-- screener_collector.py       # Screener HTML tables
|   |-- bse_collector.py            # BSE API hooks
|   |-- sebi_collector.py           # SEBI disclosure search hook
|   |-- rbi_collector.py            # RBI G-Sec yield
|   |-- macro_collector.py          # RBI plus World Bank macro data
|   |-- sector_median_collector.py  # Sector median builder
|   `-- technical_collector.py      # Price-history wrapper around technical indicators
|-- calculators/
|   |-- dcf_engine.py
|   |-- valuation_calc.py
|   |-- quality_calc.py
|   |-- cashflow_calc.py
|   |-- growth_calc.py
|   |-- governance_calc.py
|   |-- moat_calc.py
|   |-- risk_calc.py
|   |-- technical_calc.py
|   `-- peer_comparison.py
|-- scoring/
|   |-- scoring_engine.py
|   |-- bank_scorer.py
|   |-- insurance_scorer.py
|   `-- sector_adjustments.py
|-- confidence/
|   `-- data_confidence.py
|-- database/
|   |-- schema.sql
|   `-- db.py
|-- docs/
|   |-- ARCHITECTURE.md
|   `-- SOURCES.md
|-- tests/
|   |-- fixtures/sample_companies.json
|   |-- test_confidence.py
|   |-- test_dcf_engine.py
|   |-- test_indian_stock_api_collector.py
|   |-- test_pipeline_outputs.py
|   |-- test_scoring.py
|   `-- test_technical_calc.py
|-- outputs/.gitkeep
`-- logs/.gitkeep
```

## Setup

Use Python 3.11 or newer. The project was verified with Python 3.13 on Windows.

```powershell
cd C:\Users\mrpun\codex-work\stockmarket
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item config.env.example config.env
```

The checked-in code does not require paid market data credentials.

## Quick Verification

Run the deterministic fixture pipeline first. It does not call market APIs.

```powershell
pytest -q
python main.py --mode TEST --offline-fixture tests/fixtures/sample_companies.json --output-dir outputs/test_run
```

Expected result:

- `pytest` reports all tests passing.
- `outputs/test_run/` contains all nine output files.
- `outputs/test_run/run_summary.txt` records fixture-mode processing statistics.

## Live Sample Run

Use a small symbol list before a full universe run.

```powershell
python main.py --mode TEST --symbols RELIANCE,TCS,HDFCBANK --skip-screener --output-dir outputs/live_sample
```

`--skip-screener` keeps the smoke test fast and avoids unnecessary HTML scraping. Remove it when you want governance fields from Screener.

## Full Universe Run

```powershell
python main.py --mode FULL --output-dir outputs/full_run
```

Full mode uses the live Nifty LargeMidcap 250 universe provider. The provider tries NSE first, then the public Nifty Indices CSV, then the SQLite `universe` cache.

For a throttled full run with less Screener traffic:

```powershell
python main.py --mode FULL --screener-max-per-run 25 --output-dir outputs/full_run
```

## CLI Options

```text
--mode                 FULL, TEST, or RESUME. Default: TEST.
--output-dir           Directory for CSV and text outputs. Default: outputs.
--db-path              SQLite path. Default: database/stocks.db.
--limit                Limit the number of companies processed.
--symbols              Comma-separated NSE symbols. Overrides the live universe.
--offline-fixture      JSON fixture for deterministic local runs.
--skip-screener        Disable Screener HTML requests for the run.
--screener-max-per-run Maximum Screener requests in one run. Default: 25.
```

## Output Files

The pipeline writes these files for every run:

| File | Purpose |
| --- | --- |
| `master_data_raw.csv` | Raw merged company records with source and fetched-at columns where the pipeline collects sourced fields. |
| `master_scores.csv` | Ranking table with section scores, composite score, confidence score, verdict, penalties, and top/bottom sections. |
| `top50_opportunities.csv` | Companies with composite score above 65 and confidence above 50, sorted by score. |
| `red_flags.csv` | Companies that trigger pledge, Altman Z, Piotroski, leverage, FCF, audit, GNPA, insider, or confidence flags. |
| `technical_opportunities.csv` | Fundamental candidates that also match RSI, 52-week-low, confidence, and Piotroski filters. |
| `dcf_valuations.csv` | Bear, base, and bull DCF values, margin of safety, WACC, beta, assumptions, confidence, and DCF flags. |
| `peer_comparison.csv` | Company metrics compared with sector medians and three closest peers by market cap. |
| `monitoring_dashboard.csv` | Portfolio monitoring metrics, exit triggers, targets, and max position size guidance for top opportunities. |
| `run_summary.txt` | Processing counts, source success rates, confidence distribution, gaps, red flags, runtime, and next steps. |

Generated output files, logs, and SQLite databases are ignored by git.

## Data Sources

See [docs/SOURCES.md](docs/SOURCES.md) for the source matrix, endpoints, fields, fallbacks, and known network behavior.

Primary sources:

- yfinance for NSE/BSE tickers, statements, ratios, estimates, and OHLCV.
- 0xramm Indian Stock Market API for no-key REST quote/search fallback.
- NSE public APIs for universe, quote, and corporate action data.
- Screener HTML for promoter, pledge, ROE, ROCE, and supplementary Indian data.
- RBI and World Bank for macro inputs.
- BSE and SEBI collectors for filings and disclosure hooks.

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the pipeline flow, module ownership, SQLite schema, scoring flow, output writing, and extension points.

Short version:

```text
CLI args
  -> ResearchPipeline
  -> universe provider or fixture loader
  -> collectors
  -> source merge with field_source and field_fetched_at metadata
  -> calculators
  -> data confidence
  -> 12-section scoring and penalties
  -> reporting
  -> CSV/text outputs
```

## Scoring Model

`scoring/scoring_engine.py` defines the 12-section weights:

| Section | Weight |
| --- | ---: |
| Absolute valuation | 12% |
| Relative valuation | 5% |
| Profitability | 12% |
| Balance sheet | 10% |
| Cash flow | 10% |
| Growth | 10% |
| Governance | 10% |
| Moat | 10% |
| Macro tailwinds | 5% |
| Technical | 5% |
| Risk matrix | 8% |
| Sentiment | 3% |

Missing sections are reweighted across available sections. Hard red flags apply penalties after the weighted score.

## Data Confidence

`confidence/data_confidence.py` scores each company on a 100-point scale:

- 40 points for five-year core financial history.
- 20 points for governance data.
- 15 points for technical price history.
- 15 points for bank, NBFC, insurance, or non-applicable sector-specific coverage.
- 10 points for macro and sector median inputs.
- 5 points for analyst sentiment fields.

Companies below 50 confidence receive an asterisk on the verdict.

## SQLite State

`database/schema.sql` creates these tables:

- `universe`
- `nse_bse_mapping`
- `screener_cache`
- `yfinance_cache`
- `price_history`
- `nse_cache`
- `bse_cache`
- `macro_cache`
- `calculated_metrics`
- `scores`
- `sector_medians`
- `run_log`

The schema supports caching and repeatable runs. Generated DB files stay local.

## Known Operational Behavior

- Public endpoints may throttle, block, or time out depending on network, market hours, and provider rules.
- The pipeline logs collector failures and continues with available sources.
- RBI G-Sec fetch falls back to an estimated 7.0% value if parsing fails.
- `run_summary.txt` records source success rates and data gaps for the run.
- yfinance field names can change by library version, so `safe_get_yf_field()` maps multiple known keys to one logical field.

## Development Workflow

Run tests before pushing:

```powershell
pytest -q
python main.py --mode TEST --offline-fixture tests/fixtures/sample_companies.json --output-dir outputs/test_run
```

Check generated files:

```powershell
Get-ChildItem outputs\test_run
Get-Content outputs\test_run\run_summary.txt
```

## Financial Use

This repository produces research data and scoring outputs. It does not place trades, manage risk for a real portfolio, or provide personal investment advice.
