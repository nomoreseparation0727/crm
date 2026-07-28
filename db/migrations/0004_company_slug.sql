-- Multi-company support: a short URL-safe identifier per company, used for
-- dashboard routing (/[company]/...) instead of hardcoding one company name
-- throughout the app.
ALTER TABLE companies ADD COLUMN IF NOT EXISTS slug TEXT UNIQUE;

UPDATE companies SET slug = 'burgundy'
WHERE name = 'Burgundy Asset Management' AND slug IS NULL;

-- Now that multiple companies share the same scrape jobs, tag each run with
-- which company it was for (nullable: a run can fail before resolving a
-- company, e.g. a bad CIK lookup).
ALTER TABLE scrape_runs ADD COLUMN IF NOT EXISTS company_id INTEGER REFERENCES companies(id);
CREATE INDEX IF NOT EXISTS idx_scrape_runs_company ON scrape_runs (company_id);
