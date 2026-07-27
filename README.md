# Burgundy Asset Management tracker

Tracks [Burgundy Asset Management](https://www.burgundyasset.com) (a Toronto
value-equity manager) over time: AUM trend, fund holdings (with a focus on
Korean equity exposure), key personnel, and quarterly SEC 13F filings. Every
observation is stored as a new row rather than overwritten, so the full
history is queryable, and a diffing engine turns consecutive snapshots into
a change-log ("new holding", "AUM up 5%", "person X left").

## Why this design

Burgundy is a **foreign (Canadian) private manager**, so Korean regulatory
disclosure (DART) doesn't apply to it -- there's no single API that gives
"AUM + full portfolio + personnel" for a firm like this. The two sources
used instead:

1. **SEC EDGAR 13F** (`scraper/burgundy/sources/sec_edgar.py`) -- structured,
   free, no auth beyond a compliant User-Agent header. Quarterly. Only
   covers US-exchange-listed equities and ADRs Burgundy reports as a US
   institutional investment manager -- it will **never** show Korean
   ordinary shares held directly.
2. **burgundyasset.com** (`scraper/burgundy/sources/website.py`) -- the
   firm's own team page and fund fact sheets/commentary PDFs, which is
   where Korean holdings, AUM figures, and personnel actually come from.

Everything is appended (SCD Type 2 style, see `db/migrations/0001_init.sql`)
so trends and diffs are just SQL over history, not something computed ad hoc.

## Known limitation: the website scraper is unverified against the live site

`burgundyasset.com` returned HTTP 403 to every fetch attempt made while
building this (looked like bot/WAF protection, not a hard block -- a
realistic browser User-Agent from Railway's IPs may well get through where
this sandbox's network didn't). Because of that, `sources/website.py` uses
**heuristic pattern matching** (a heading that looks like a person's name, a
number followed by "billion" near the word "assets", a table row ending in a
percentage) rather than fixed CSS selectors tied to an inspected DOM.

Every fetch is archived into the `raw_snapshots` table specifically so that
tuning the parser later means re-running it against already-fetched
HTML/PDF text, not re-scraping the live site. After first deploy:

1. Check `raw_snapshots` for what actually got fetched.
2. Check `scrape_runs` for errors (`SELECT * FROM scrape_runs ORDER BY id DESC`).
3. Adjust `config.team_page_url` / `config.funds_index_url` (env vars
   `BURGUNDY_TEAM_URL`, `BURGUNDY_FUNDS_URL`) if the guessed paths are wrong.
4. Adjust the parsing heuristics in `sources/website.py` against real content.

The SEC 13F pipeline has no such caveat -- `data.sec.gov`'s JSON APIs and the
13F information-table XML schema are stable, documented formats.

## Repo layout

```
db/migrations/    Plain SQL migrations (schema_migrations tracks what's applied)
db/migrate.py     Idempotent migration runner
scraper/          Python: fetches data, writes snapshots + diffs, run by Railway cron
dashboard/        Next.js: reads the same Postgres, renders AUM/holdings/team
```

## Local setup

Requires Postgres, Python 3.12+, Node 20+.

```bash
createdb burgundy
export DATABASE_URL=postgresql://localhost/burgundy
python3 db/migrate.py

cd scraper
pip install -r requirements.txt
cp ../.env.example ../.env   # fill in SEC_EDGAR_USER_AGENT at minimum
python3 -m burgundy.jobs.run_all

cd ../dashboard
npm install
cp .env.local.example .env.local   # same DATABASE_URL
npm run dev   # http://localhost:3000
```

## Deploying to Railway

Create one Railway project with three services:

1. **Postgres** -- Railway's managed Postgres plugin.
2. **scraper** (cron) -- new service from this GitHub repo.
   - Root Directory: repo root (the Dockerfile needs `db/` as build context,
     see `scraper/railway.toml`'s `dockerfilePath`).
   - Set `DATABASE_URL` to the Postgres plugin's connection variable,
     `SEC_EDGAR_USER_AGENT` to a real contact string, and (recommended)
     `BURGUNDY_SEC_CIK` once you've looked it up on EDGAR.
   - Cron schedule is set in `scraper/railway.toml` (daily 06:00 UTC);
     change it in the dashboard's Settings -> Cron Schedule, or edit the file.
   - Every run applies pending migrations first (`entrypoint.sh`), so schema
     changes ship automatically with a deploy.
3. **dashboard** (web) -- another service from the same repo.
   - Root Directory: `dashboard/`.
   - Set `DATABASE_URL` to the same Postgres variable.
   - Uses Nixpacks (no Dockerfile needed for Next.js); `next start` reads
     Railway's `PORT` automatically.

Trigger the scraper's first run manually (Railway lets you run a cron
service on demand) so the dashboard has data to show immediately rather than
waiting for the first scheduled fire.

## Data model

See `db/migrations/0001_init.sql` for the full schema. Summary:

| Table | What it holds |
|---|---|
| `aum_snapshots` | AUM figure history, one row per observation |
| `funds` | Funds Burgundy manages (as discovered on the website) |
| `fund_holdings_snapshots` | Top holdings per fund per observation (not a full portfolio -- whatever subset is publicly disclosed) |
| `sec13f_filings` / `sec13f_holdings` | Quarterly 13F filings and their line items |
| `executives_snapshots` | Team/leadership roster per observation |
| `change_events` | Diffs computed right after each scrape -- the dashboard's activity feed reads only this table |
| `raw_snapshots` | Archived raw HTML/PDF-text per fetch, for re-tuning parsers without re-scraping |
| `scrape_runs` | Run log (status, error, item counts) per job invocation |

## Compliance notes

- SEC EDGAR requires a descriptive User-Agent identifying the caller; the
  scraper enforces this via `SEC_EDGAR_USER_AGENT` and refuses to run without it.
- The website scraper only reads publicly published pages (team bios, fund
  fact sheets) -- no authentication bypass, no scraping of gated content.
- No DART/Korean regulatory API is used, since Burgundy is a foreign private
  manager and DART disclosure obligations don't apply to it the way they
  would to a Korean-domiciled manager.
