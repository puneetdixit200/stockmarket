# Data Sources

This platform uses free public sources. It does not require Bloomberg, Refinitiv, paid broker feeds, or paid data vendor credentials.

## Source Priority

The pipeline merges data at field level. For live runs, quote-like fields prefer yfinance, then the 0xramm Indian Stock Market API, then NSE. Governance fields use Screener when enabled. Macro fields use RBI and World Bank, with explicit estimated fallbacks.

| Data area | Primary | Fallback | Local fallback |
| --- | --- | --- | --- |
| Universe | NSE index API | Nifty Indices CSV | SQLite `universe` table |
| Current quote | yfinance `.NS` | 0xramm API `/stock` or `/stock/list` | NSE quote endpoint |
| Financial statements | yfinance `.NS` or `.BO` | Screener HTML where available | Future `yfinance_cache` table |
| OHLCV history | yfinance history | Future NSE/BSE bhavcopy support | `price_history` table |
| Promoter and pledge | Screener HTML | NSE/BSE hooks | Unavailable with confidence penalty |
| Corporate actions | NSE corporate action API | BSE filing hook | Unavailable |
| BSE filings | BSE API hook | SEBI disclosure hook | Unavailable |
| G-Sec yield | RBI page parser | Estimated 7.0% | `macro_cache` table |
| GDP and CPI | World Bank API | Conservative defaults | `macro_cache` table |
| Sector medians | Calculated from run records | Overall run data | `sector_medians` table |
| Technical indicators | Calculated from OHLCV | Not applicable | Unavailable with confidence penalty |

## yfinance

Collector: `data_collectors/yfinance_collector.py`

Purpose:

- Primary structured source for NSE/BSE listed companies.
- Fetches metadata, ratios, analyst fields, financial statements, cash-flow data, balance-sheet data, and price history.

Symbol order:

1. `{SYMBOL}.NS`
2. `{SYMBOL}.BO`

Important fields:

- `company_name`
- `last_price`
- `previous_close`
- `year_high`
- `year_low`
- `volume`
- `market_cap`
- `enterprise_value`
- `pe_ratio`
- `pb_ratio`
- `dividend_yield`
- `book_value`
- `eps`
- `beta`
- `sector`
- `industry`
- `target_mean_price`
- `analyst_recommendation`
- `shares_outstanding`
- `revenue_history`
- `pat_history`
- `ebit_history`
- `total_assets_history`
- `equity_history`
- `total_debt_history`
- `cfo_history`
- `capex_history`
- `price_history`

Field-name stability:

`safe_get_yf_field()` maps logical fields to multiple yfinance keys because yfinance changes names across versions.

Failure behavior:

- If yfinance is not installed, the collector returns `_source: unavailable`.
- If `.NS` fails, the collector tries `.BO`.
- If both suffixes fail, the pipeline continues with other sources.

## 0xramm Indian Stock Market API

Collector: `data_collectors/indian_stock_api_collector.py`

Source repository: `https://github.com/0xramm/Indian-Stock-Market-API.git`

Default base URL:

```text
http://65.0.104.9/
```

Override:

```powershell
$env:INDIAN_STOCK_API_BASE_URL="http://65.0.104.9/"
```

Endpoints used:

| Endpoint | Method | Use |
| --- | --- | --- |
| `/search?q={query}` | GET | Symbol lookup and API compatibility. |
| `/stock?symbol={SYMBOL}&res=num` | GET | Single-symbol quote and metadata fallback. |
| `/stock/list?symbols={SYMBOL1,SYMBOL2}&res=num` | GET | Batch quote fallback. |

Fields used when present:

- `company_name`
- `last_price`
- `change`
- `percent_change`
- `previous_close`
- `open`
- `day_high`
- `day_low`
- `year_high`
- `year_low`
- `volume`
- `market_cap`
- `pe_ratio`
- `dividend_yield`
- `book_value`
- `earnings_per_share`
- `sector`
- `industry`
- `currency`

Failure behavior:

- Batch timeout creates unavailable records for that batch.
- Missing batch symbols get single-symbol fetch attempts.
- The collector marks failures with `_source: unavailable` and `_error`.

Observed network behavior:

- In the most recent local smoke run, the hosted API timed out from this network.
- yfinance still supplied live data, so the run completed.

## NSE

Collectors:

- `universe/nifty_largmidcap250.py`
- `data_collectors/nse_collector.py`

Endpoints:

```text
https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20LARGEMIDCAP%20250
https://www.nseindia.com/api/quote-equity
https://www.nseindia.com/api/corporates-corporateActions
```

Universe fallback:

```text
https://www.niftyindices.com/IndexConstituent/ind_niftylargemidcap250list.csv
```

Fields used:

- Universe constituents
- ISIN when present
- Sector and industry when present
- Last price
- Previous close
- 52-week high and low
- Corporate actions hook

Session behavior:

`NSESessionManager` primes the session by visiting `https://www.nseindia.com` before API calls.

Observed network behavior:

- In the most recent local smoke run, NSE quote returned `403` from this network.
- The pipeline marked NSE unavailable and continued.

## Screener

Collector: `data_collectors/screener_collector.py`

URLs:

```text
https://www.screener.in/company/{SYMBOL}/consolidated/
https://www.screener.in/company/{SYMBOL}/
```

Fields extracted when present:

- `promoter_pct`
- `pledge_pct`
- `roe_pct`
- `roce_pct`
- `screener_tables_count`

Controls:

```powershell
python main.py --skip-screener
python main.py --screener-max-per-run 25
```

Failure behavior:

- HTML parsing or blocking returns `_source: unavailable`.
- Governance confidence loses points when promoter, pledge, or board data is missing.

Operational note:

Screener can block repeated scraping. Use a small `--screener-max-per-run` and rerun later when you need broad governance coverage.

## BSE

Collector: `data_collectors/bse_collector.py`

Endpoints:

```text
https://api.bseindia.com/BseIndiaAPI/api/StockReachGraph/w
https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w
```

Current use:

- Quote hook by BSE code.
- Corporate filing hook by BSE code.

This collector is in place for BSE-specific enrichment. The current pipeline does not yet require a BSE code for the default fixture path.

## SEBI

Collector: `data_collectors/sebi_collector.py`

Endpoint:

```text
https://www.sebi.gov.in/sebiweb/ajax/home/getnewslistinfo.jsp
```

Current use:

- Disclosure search hook by symbol.
- Stores a bounded raw text response for downstream parsing.

The collector returns unavailable records on network or parsing failure.

## RBI

Collector: `data_collectors/rbi_collector.py`

Endpoint:

```text
https://www.rbi.org.in/Scripts/BS_NSDPDisplay.aspx
```

Fields:

- `gsec_10yr_yield`
- `gsec_10yr_yield_source`

Fallback:

- If parsing fails or the value falls outside a reasonable range, the collector returns `7.0` with source `estimated`.
- DCF output flags estimated G-Sec usage with `USING_ESTIMATED_GSEC`.

## World Bank

Collector: `data_collectors/macro_collector.py`

Endpoint pattern:

```text
https://api.worldbank.org/v2/country/IN/indicator/{indicator}?format=json&per_page=5
```

Indicators:

| Indicator | Field |
| --- | --- |
| `NY.GDP.MKTP.KD.ZG` | `india_gdp_growth` |
| `FP.CPI.TOTL.ZG` | `india_cpi` |

Fallbacks:

- GDP growth: `6.5`
- CPI: `5.0`

Static macro defaults:

- USD/INR: `83.0`
- Brent crude: `80.0`

These defaults are explicit fields in the macro result and appear in the run's merged data.

## Calculated Sources

Some output fields do not come from a raw provider:

| Field group | Source |
| --- | --- |
| DCF values | `calculators/dcf_engine.py` |
| Valuation ratios and discounts | `calculators/valuation_calc.py` |
| Quality and balance-sheet ratios | `calculators/quality_calc.py` |
| Cash-flow metrics | `calculators/cashflow_calc.py` |
| Growth metrics | `calculators/growth_calc.py` |
| Governance flags | `calculators/governance_calc.py` |
| Moat proxies | `calculators/moat_calc.py` |
| Risk flags | `calculators/risk_calc.py` |
| Technical indicators | `calculators/technical_calc.py` |
| Peer comparison | `calculators/peer_comparison.py` |
| Data confidence | `confidence/data_confidence.py` |
| Composite scores | `scoring/scoring_engine.py` |

These fields should use source value `calculated` when added as sourced fields in future output expansion.

## Source Metadata

The merge layer writes source metadata for scalar source fields:

```text
{field}
{field}_source
{field}_fetched_at
```

Examples:

```text
last_price
last_price_source
last_price_fetched_at
market_cap
market_cap_source
market_cap_fetched_at
```

For list-like histories, the pipeline stores:

```text
{history_field}
{history_field}_source
{history_field}_fetched_at
```

The run summary also includes source success counts.

## Network and Market-Hour Notes

Public market endpoints can behave differently by time, IP, headers, and provider-side rate limits. Runs may see:

- HTTP 403 from NSE.
- Timeouts from the hosted 0xramm API.
- Screener blocking after repeated HTML requests.
- yfinance missing fields for a specific ticker or suffix.

The pipeline treats these as data quality issues, records them, and continues when another source can supply enough information.

## Adding a Source

Follow the existing collector contract:

1. Put the collector under `data_collectors/`.
2. Return a dictionary with `_source` and `_fetched_at` on success.
3. Return `_source: unavailable` and `_error` on failure.
4. Wire the collector into `ResearchPipeline._collect_live_records()`.
5. Merge fields with `add_sourced_field()`.
6. Add source success accounting in `_run_stats()` when needed.
7. Add a test with a fake session for timeout and error paths.
