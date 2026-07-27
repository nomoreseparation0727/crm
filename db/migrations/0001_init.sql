-- Initial schema for Burgundy Asset Management tracking service.
--
-- Design: every observation is appended as a new row (SCD Type 2 style) rather
-- than updated in place, so the full history is always queryable. A separate
-- `change_events` table stores only the diffs between consecutive snapshots,
-- which is what the dashboard's "recent activity" feed reads from.

CREATE TABLE IF NOT EXISTS companies (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    website         TEXT,
    sec_cik         TEXT,              -- 10-digit zero-padded CIK, resolved lazily
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS scrape_runs (
    id              SERIAL PRIMARY KEY,
    source          TEXT NOT NULL,     -- 'sec_edgar_13f' | 'website_team' | 'website_funds' | 'fund_factsheet'
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    status          TEXT NOT NULL DEFAULT 'running', -- 'running' | 'success' | 'error'
    error_message   TEXT,
    items_seen      INTEGER NOT NULL DEFAULT 0
);

-- AUM history (company-wide, as disclosed on the website / fact sheets / 13F cover pages).
CREATE TABLE IF NOT EXISTS aum_snapshots (
    id              SERIAL PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    observed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    as_of_date      DATE,              -- date the figure itself is reported "as of", if known
    aum_amount      NUMERIC,
    aum_currency    TEXT NOT NULL DEFAULT 'CAD',
    source          TEXT NOT NULL,     -- URL or filing reference
    raw_text        TEXT,              -- verbatim sentence/label the figure was extracted from
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_aum_snapshots_company_time ON aum_snapshots (company_id, observed_at);

-- Funds managed by the company (e.g. "Burgundy Asian Equity Fund").
CREATE TABLE IF NOT EXISTS funds (
    id              SERIAL PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    name            TEXT NOT NULL,
    slug            TEXT,
    fund_type       TEXT,              -- e.g. 'equity', 'balanced', 'asian equity'
    source_url      TEXT,
    UNIQUE (company_id, name)
);

-- Top holdings per fund, parsed from fact sheets / commentary PDFs published on the website.
-- Not a full portfolio (funds rarely disclose 100% of holdings) -- this tracks whatever
-- subset (e.g. "top 10/25 holdings") is publicly disclosed at each observation.
CREATE TABLE IF NOT EXISTS fund_holdings_snapshots (
    id              SERIAL PRIMARY KEY,
    fund_id         INTEGER NOT NULL REFERENCES funds(id),
    observed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    as_of_date      DATE,
    stock_name      TEXT NOT NULL,
    stock_country   TEXT,              -- e.g. 'South Korea', 'Canada', 'United States'
    ticker          TEXT,
    weight_pct      NUMERIC,
    source          TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_fund_holdings_fund_time ON fund_holdings_snapshots (fund_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_fund_holdings_country ON fund_holdings_snapshots (stock_country);

-- SEC 13F holdings (quarterly, US-listed equities & ADRs only -- Korean ordinary shares
-- held directly will NOT appear here; see fund_holdings_snapshots for those).
CREATE TABLE IF NOT EXISTS sec13f_filings (
    id                  SERIAL PRIMARY KEY,
    company_id          INTEGER NOT NULL REFERENCES companies(id),
    accession_number    TEXT NOT NULL UNIQUE,
    period_of_report    DATE NOT NULL,
    filed_at            DATE NOT NULL,
    source_url          TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sec13f_holdings (
    id              SERIAL PRIMARY KEY,
    filing_id       INTEGER NOT NULL REFERENCES sec13f_filings(id) ON DELETE CASCADE,
    issuer_name     TEXT NOT NULL,
    cusip           TEXT,
    class_title     TEXT,
    value_usd_thousands NUMERIC,
    shares          NUMERIC,
    share_type      TEXT,              -- 'SH' | 'PRN'
    put_call        TEXT
);
CREATE INDEX IF NOT EXISTS idx_sec13f_holdings_filing ON sec13f_holdings (filing_id);
CREATE INDEX IF NOT EXISTS idx_sec13f_holdings_issuer ON sec13f_holdings (issuer_name);

-- Key personnel, scraped from the "our team" / leadership pages.
CREATE TABLE IF NOT EXISTS executives_snapshots (
    id              SERIAL PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    observed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    person_name     TEXT NOT NULL,
    title           TEXT,
    bio_excerpt     TEXT,
    source          TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_executives_company_time ON executives_snapshots (company_id, observed_at);

-- Derived diff events, computed by the snapshot-diffing engine right after each scrape.
-- This is what the dashboard's activity feed reads from -- it never needs to compute
-- diffs itself.
CREATE TABLE IF NOT EXISTS change_events (
    id              SERIAL PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    entity_type     TEXT NOT NULL,     -- 'aum' | 'fund_holding' | 'sec13f_holding' | 'executive'
    entity_ref      TEXT,              -- e.g. fund name + stock name, or person name
    event_type      TEXT NOT NULL,     -- 'new' | 'removed' | 'increased' | 'decreased' | 'joined' | 'left' | 'title_change'
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    old_value       TEXT,
    new_value       TEXT,
    detail          JSONB
);
CREATE INDEX IF NOT EXISTS idx_change_events_company_time ON change_events (company_id, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_change_events_entity_type ON change_events (entity_type);
