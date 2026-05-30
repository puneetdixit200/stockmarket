# Architecture

This document explains how the Indian Equity Research Platform moves from a universe of symbols to scored research outputs.

## System Boundary

The platform is a batch research pipeline. It runs from the command line, collects data from free sources, calculates metrics, scores companies, and writes files. It does not expose a web server or keep a long-running process alive.

## Main Flow

```text
main.py
  -> build_arg_parser()
  -> config_from_args()
  -> ResearchPipeline.run()
       -> load fixture or fetch universe
       -> collect source data
       -> merge source records
       -> fetch macro data
       -> first calculation pass
       -> build sector medians
       -> second calculation pass with medians
       -> confidence scoring
       -> section scoring
       -> output writer
```

The two calculation passes matter. Some metrics need sector medians. The first pass creates enough normalized company metrics to build those medians. The second pass uses medians in relative valuation, moat, and confidence calculations.

## Entry Point

`main.py` owns CLI startup:

- Configures logging to `logs/platform.log` and console output.
- Parses arguments from `pipeline.build_arg_parser()`.
- Creates `ResearchPipeline` through `pipeline.config_from_args()`.
- Runs the pipeline and logs every file written.

## Runtime Configuration

`pipeline.RunConfig` holds runtime choices:

| Field | Purpose |
| --- | --- |
| `mode` | Run label: `FULL`, `TEST`, or `RESUME`. |
| `output_dir` | Directory where outputs are written. |
| `db_path` | SQLite file path. |
| `limit` | Optional company limit. |
| `symbols` | Optional explicit symbol list. |
| `offline_fixture` | Optional JSON fixture path. |
| `skip_screener` | Avoid Screener HTML requests. |
| `screener_max_per_run` | Maximum Screener requests in a run. |

`config.env.example` documents environment variables. The current code reads `INDIAN_STOCK_API_BASE_URL` in the 0xramm API collector.

## Universe Layer

`universe/nifty_largmidcap250.py` defines `NiftyLargeMidcap250Provider`.

Fetch order:

1. NSE index endpoint: `https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20LARGEMIDCAP%20250`
2. Nifty Indices CSV: `https://www.niftyindices.com/IndexConstituent/ind_niftylargemidcap250list.csv`
3. SQLite `universe` table

The provider normalizes source columns into:

- `symbol`
- `company_name`
- `isin`
- `industry`
- `series`
- `weightage`
- `fetched_at`

`universe/sector_classifier.py` maps a company to `BANK`, `NBFC`, `INSURANCE`, `SERVICES`, `MANUFACTURING`, `ASSET_HEAVY`, or `GENERAL`. The same file supplies monitoring metrics for `monitoring_dashboard.csv`.

## Collection Layer

Collectors live under `data_collectors/`. Each collector returns a dictionary with `_source` and `_fetched_at` when data is available. On failure, collectors return `_source: unavailable` plus `_error`, allowing the pipeline to continue.

| Module | Responsibility |
| --- | --- |
| `yfinance_collector.py` | Primary NSE/BSE structured data, financial statements, ratios, analyst fields, and OHLCV history. |
| `indian_stock_api_collector.py` | 0xramm hosted REST API client for `/search`, `/stock`, and `/stock/list`. |
| `nse_collector.py` | NSE quote and corporate action endpoints with session priming. |
| `screener_collector.py` | Screener HTML table extraction for promoter, pledge, ROE, ROCE, and table coverage. |
| `bse_collector.py` | BSE quote and filing API hooks. |
| `sebi_collector.py` | SEBI disclosure search hook. |
| `rbi_collector.py` | RBI 10-year G-Sec yield parser with an estimated fallback. |
| `macro_collector.py` | RBI plus World Bank macro inputs. |
| `sector_median_collector.py` | Sector medians for peer-relative scoring. |
| `technical_collector.py` | Wrapper for technical indicators from OHLCV records. |

## Source Merge

`ResearchPipeline._merge_sources()` combines universe, yfinance, 0xramm API, NSE, and Screener data.

For sourced scalar fields, the pipeline writes three values:

```text
field
field_source
field_fetched_at
```

Example:

```text
last_price
last_price_source
last_price_fetched_at
```

The merge order favors yfinance, then the 0xramm REST API, then NSE for quote-like fields. Screener supplies governance and supplementary metrics when enabled.

`source_status` records the collector result per source. `run_summary.txt` uses it for source success counts.

## Calculation Layer

Metric calculators live under `calculators/`.

| Module | Main output |
| --- | --- |
| `cashflow_calc.py` | FCF, owner earnings, CFO/PAT, capex intensity, dividend payout, buyback yield. |
| `quality_calc.py` | Margins, ROE, ROCE, ROIC, leverage, Altman Z, Piotroski, current ratio. |
| `dcf_engine.py` | Bear/base/bull DCF values, WACC, beta, margin of safety, DCF flags. |
| `valuation_calc.py` | PE, PB, EV/EBITDA, EV/Sales, FCF yield, P/FCF, PEG, Graham number, sector discounts. |
| `growth_calc.py` | Revenue, PAT, EBIT, EPS CAGR and latest growth. |
| `governance_calc.py` | Promoter holding, pledge, board independence, auditor score, governance flags. |
| `moat_calc.py` | Pricing power, asset efficiency, R&D intensity, market share proxy, moat proxy. |
| `risk_calc.py` | Leverage, beta, pledge, GNPA, concentration, commodity, currency, and regulatory risk flags. |
| `technical_calc.py` | SMA, RSI, MACD, ATR, volatility, 52-week levels, support, stop-loss, relative strength. |
| `peer_comparison.py` | Sector medians and closest-peer comparison rows. |

Calculators accept dictionaries and return dictionaries. This keeps each calculator isolated from collectors and reporting.

## DCF Engine

`calculators/dcf_engine.py` defines three scenarios:

| Scenario | Growth assumption | Margin assumption | Terminal growth |
| --- | --- | --- | ---: |
| Bear | 60% of base growth | 90% of base margin | 3.5% |
| Base | 100% of base growth | 100% of base margin | 4.5% |
| Bull | 125% of base growth | 108% of base margin | 5.5% |

The DCF engine estimates WACC from G-Sec yield, beta, market risk premium, debt/equity, and tax rate. It flags negative EBIT, estimated G-Sec usage, and high terminal value share.

## Confidence Layer

`confidence/data_confidence.py` scores data coverage on a 100-point scale:

| Area | Points |
| --- | ---: |
| Core financial history | 40 |
| Governance | 20 |
| Technical price history | 15 |
| Sector-specific fields | 15 |
| Macro and sector median inputs | 10 |
| Analyst and sentiment fields | 5 |

The result includes:

- `confidence_score`
- `confidence_grade`
- `field_completeness`
- `missing_critical_fields`
- `data_sources_used`

Low-confidence companies stay in the outputs, but the verdict carries an asterisk when confidence is below 50.

## Scoring Layer

`scoring/scoring_engine.py` defines the standard 12-section framework:

| Section | Weight |
| --- | ---: |
| `absolute_valuation` | 0.12 |
| `relative_valuation` | 0.05 |
| `profitability` | 0.12 |
| `balance_sheet` | 0.10 |
| `cash_flow` | 0.10 |
| `growth` | 0.10 |
| `governance` | 0.10 |
| `moat` | 0.10 |
| `macro_tailwinds` | 0.05 |
| `technical` | 0.05 |
| `risk_matrix` | 0.08 |
| `sentiment` | 0.03 |

`score_company_sections()` creates parameter-level scores from metrics. `calculate_composite_score()` averages each section, reweights available sections, converts the score to a 100-point scale, and applies penalties.

Penalty flags include:

- High pledge
- Altman Z below 1.8
- Piotroski below 3
- Qualified audit opinion
- Insider sell cluster
- Net debt/EBITDA above 5x
- GNPA above 7%
- Negative FCF for three consecutive years

Special frameworks:

- `bank_scorer.py` adds NIM, ROA, GNPA, capital adequacy, and CASA.
- `insurance_scorer.py` adds combined ratio, solvency, premium growth, and persistency.
- `sector_adjustments.py` adds focused signals for asset-heavy and services companies.

## Reporting Layer

`reporting.write_all_outputs()` writes every required output file:

```text
master_data_raw.csv
master_scores.csv
top50_opportunities.csv
red_flags.csv
technical_opportunities.csv
dcf_valuations.csv
peer_comparison.csv
monitoring_dashboard.csv
run_summary.txt
```

The writer keeps generated outputs outside git through `.gitignore`.

## SQLite Schema

`database/schema.sql` creates the project tables:

| Table | Purpose |
| --- | --- |
| `universe` | Cached Nifty LargeMidcap 250 constituents. |
| `nse_bse_mapping` | NSE to BSE mapping hook. |
| `screener_cache` | Screener scrape cache. |
| `yfinance_cache` | yfinance statement and metadata cache. |
| `price_history` | OHLCV history by symbol/date. |
| `nse_cache` | NSE endpoint cache. |
| `bse_cache` | BSE endpoint cache. |
| `macro_cache` | Macro data cache. |
| `calculated_metrics` | Serialized calculated metrics. |
| `scores` | Serialized section and composite scores. |
| `sector_medians` | Sector median snapshots. |
| `run_log` | Run-level status and source performance. |

`database/db.py` initializes the schema and provides JSON cache helpers.

## Error Handling

Collectors catch network, parsing, and provider errors at the source boundary. The pipeline receives an unavailable record and continues. This keeps one blocked endpoint from stopping the whole run.

The run summary records:

- Companies attempted
- Companies failed
- Source success counts
- Macro status
- G-Sec yield source
- Confidence distribution
- Critical data gaps
- Red flag counts
- Runtime

## Tests

The tests use local fixtures for deterministic verification:

| Test file | Coverage |
| --- | --- |
| `test_confidence.py` | General and bank confidence scoring. |
| `test_dcf_engine.py` | DCF scenarios and estimated G-Sec flag. |
| `test_indian_stock_api_collector.py` | API batch timeout behavior. |
| `test_pipeline_outputs.py` | End-to-end fixture run and output files. |
| `test_scoring.py` | Section weights, penalties, low-confidence verdict marker. |
| `test_technical_calc.py` | Technical indicators and levels. |

Run:

```powershell
pytest -q
```

## Extension Points

Add a new data source:

1. Create a collector in `data_collectors/`.
2. Return `_source`, `_fetched_at`, and `_error` on failure.
3. Wire the collector into `ResearchPipeline._collect_live_records()`.
4. Add fields to `_merge_sources()` with `add_sourced_field()`.
5. Add tests with a fake session or fixture.

Add a metric:

1. Implement the calculation in the relevant `calculators/` module.
2. Add a scoring rule in `scoring/scoring_engine.py` or the sector scorer.
3. Add output columns in `reporting.py` if analysts need the field.
4. Add a fixture assertion.

Add a new output:

1. Add the filename to `reporting.OUTPUT_FILENAMES`.
2. Add a writer call in `write_all_outputs()`.
3. Update `README.md` and tests.
