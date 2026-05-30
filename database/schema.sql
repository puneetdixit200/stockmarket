CREATE TABLE IF NOT EXISTS universe (
    symbol          TEXT PRIMARY KEY,
    company_name    TEXT,
    isin            TEXT UNIQUE,
    industry        TEXT,
    series          TEXT,
    weightage       REAL,
    fetched_at      TEXT
);

CREATE TABLE IF NOT EXISTS nse_bse_mapping (
    nse_symbol      TEXT PRIMARY KEY,
    bse_code        TEXT,
    isin            TEXT,
    updated_at      TEXT
);

CREATE TABLE IF NOT EXISTS screener_cache (
    symbol          TEXT PRIMARY KEY,
    data            TEXT,
    fetched_at      TEXT
);

CREATE TABLE IF NOT EXISTS yfinance_cache (
    symbol          TEXT PRIMARY KEY,
    info_json       TEXT,
    financials_json TEXT,
    balance_sheet_json TEXT,
    cashflow_json   TEXT,
    quarterly_financials_json TEXT,
    quarterly_balance_sheet_json TEXT,
    quarterly_cashflow_json TEXT,
    dividends_json  TEXT,
    splits_json     TEXT,
    suffix_used     TEXT,
    fetched_at      TEXT
);

CREATE TABLE IF NOT EXISTS price_history (
    symbol          TEXT,
    date            TEXT,
    open            REAL,
    high            REAL,
    low             REAL,
    close           REAL,
    volume          INTEGER,
    PRIMARY KEY (symbol, date)
);

CREATE TABLE IF NOT EXISTS nse_cache (
    symbol          TEXT,
    endpoint        TEXT,
    data            TEXT,
    fetched_at      TEXT,
    PRIMARY KEY (symbol, endpoint)
);

CREATE TABLE IF NOT EXISTS bse_cache (
    bse_code        TEXT,
    endpoint        TEXT,
    data            TEXT,
    fetched_at      TEXT,
    PRIMARY KEY (bse_code, endpoint)
);

CREATE TABLE IF NOT EXISTS macro_cache (
    id              INTEGER PRIMARY KEY DEFAULT 1,
    data            TEXT,
    fetched_at      TEXT
);

CREATE TABLE IF NOT EXISTS calculated_metrics (
    symbol          TEXT PRIMARY KEY,
    company_type    TEXT,
    metrics_json    TEXT,
    calculated_at   TEXT
);

CREATE TABLE IF NOT EXISTS scores (
    symbol          TEXT PRIMARY KEY,
    company_type    TEXT,
    section_scores_json     TEXT,
    composite_score         REAL,
    confidence_score        REAL,
    confidence_grade        TEXT,
    verdict                 TEXT,
    penalty_flags           TEXT,
    scored_at               TEXT
);

CREATE TABLE IF NOT EXISTS sector_medians (
    sector          TEXT PRIMARY KEY,
    medians_json    TEXT,
    company_count   INTEGER,
    calculated_at   TEXT
);

CREATE TABLE IF NOT EXISTS run_log (
    run_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      TEXT,
    completed_at    TEXT,
    mode            TEXT,
    companies_attempted     INTEGER,
    companies_succeeded     INTEGER,
    companies_failed        INTEGER,
    yfinance_success_rate   REAL,
    screener_success_rate   REAL,
    nse_success_rate        REAL,
    bse_success_rate        REAL,
    gsec_yield_source       TEXT,
    screener_blocked        INTEGER DEFAULT 0,
    notes                   TEXT
);

CREATE INDEX IF NOT EXISTS idx_price_history_symbol ON price_history(symbol);
CREATE INDEX IF NOT EXISTS idx_scores_composite ON scores(composite_score DESC);
CREATE INDEX IF NOT EXISTS idx_scores_verdict ON scores(verdict);
