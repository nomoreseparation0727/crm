-- Raw fetched content (HTML pages, extracted PDF text) kept alongside each
-- scrape run. The website/PDF parsers are heuristic (the site's real DOM/PDF
-- layout couldn't be inspected while this was built -- see README), so this
-- table lets selectors be tuned later by re-running the parser against
-- already-fetched content instead of re-scraping the live site.
CREATE TABLE IF NOT EXISTS raw_snapshots (
    id              SERIAL PRIMARY KEY,
    scrape_run_id   INTEGER REFERENCES scrape_runs(id),
    url             TEXT NOT NULL,
    content_type    TEXT,              -- 'html' | 'pdf_text'
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    content         TEXT
);
CREATE INDEX IF NOT EXISTS idx_raw_snapshots_url ON raw_snapshots (url, fetched_at DESC);
