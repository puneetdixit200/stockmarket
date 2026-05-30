# Indian Equity Research Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Python platform requested by the supplied Indian equity research document and publish it to `puneetdixit200/stockmarket`.

**Architecture:** Keep the requested module layout, implement free-source collectors with source tracking, calculate metrics and 12-section scores, and emit all required outputs. Use deterministic fixture mode for CI-style verification and live mode for the full universe.

**Tech Stack:** Python 3.13, pandas, numpy, requests, yfinance, BeautifulSoup/lxml, SQLite, pytest.

---

### Task 1: Project Skeleton

**Files:**
- Create: `requirements.txt`
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `.gitignore`
- Create: package `__init__.py` files

- [x] Add dependency and test configuration.
- [x] Document setup, test run, live sample, full run, and output names.

### Task 2: Data Collection

**Files:**
- Create: `universe/nifty_largmidcap250.py`
- Create: `universe/sector_classifier.py`
- Create: `data_collectors/*.py`

- [x] Implement NSE/Nifty universe fetch with cache fallback.
- [x] Integrate the hosted REST API from `0xramm/Indian-Stock-Market-API`.
- [x] Implement yfinance, NSE, Screener, BSE, SEBI, RBI, macro, sector median, and technical collector modules.

### Task 3: Calculators and Scoring

**Files:**
- Create: `calculators/*.py`
- Create: `confidence/data_confidence.py`
- Create: `scoring/*.py`

- [x] Implement DCF, valuation, quality, cash-flow, growth, governance, moat, risk, technical, peer, confidence, bank, insurance, sector adjustment, and composite scoring logic.

### Task 4: Pipeline and Outputs

**Files:**
- Create: `pipeline.py`
- Create: `reporting.py`
- Create: `main.py`
- Create: `database/schema.sql`
- Create: `database/db.py`

- [x] Orchestrate fixture and live runs.
- [x] Write all required output files.
- [x] Initialize SQLite schema.

### Task 5: Verification and Publish

**Files:**
- Create: `tests/*.py`
- Create: `tests/fixtures/sample_companies.json`

- [x] Add focused automated tests.
- [ ] Run `pytest -q`.
- [ ] Run deterministic pipeline output generation.
- [ ] Commit and push to `https://github.com/puneetdixit200/stockmarket.git`.
