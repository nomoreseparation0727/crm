#!/usr/bin/env python3
"""Cron entrypoint: fetch any new 13F-HR filings for every tracked company
and store their holdings. Safe to run daily -- SEC only publishes new 13F
filings quarterly (within 45 days of quarter end), so most runs will see
nothing new. Not every tracked company necessarily files 13F (it only
applies to US institutional managers with >$100M in 13(f) securities) --
a company with no CIK resolvable simply contributes nothing here.
"""
from __future__ import annotations

import logging
from datetime import date

from ..companies import COMPANIES, CompanyConfig
from ..db import finish_scrape_run, get_conn, get_or_create_company, start_scrape_run
from ..diff import diff_sec13f_holdings
from ..sources import sec_edgar

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("run_sec13f")

# This tracker cares about recent/ongoing trends, not a full historical
# backfill -- and older filings predate the XML information-table mandate,
# so they aren't reliably parseable anyway (see the skip below).
MIN_REPORT_DATE = date(2018, 1, 1)


def _run_for_company(conn, company: CompanyConfig) -> None:
    run_id = start_scrape_run(conn, "sec_edgar_13f")
    items_seen = 0
    try:
        company_id = get_or_create_company(conn, company.name, company.website, company.slug)
        with conn.cursor() as cur:
            cur.execute("UPDATE scrape_runs SET company_id = %s WHERE id = %s", (company_id, run_id))

        cik = company.sec_cik
        if not cik:
            log.warning("no confirmed sec_cik for %s, attempting best-effort name resolution", company.name)
            cik = sec_edgar.resolve_cik(company.name)
            if not cik:
                raise RuntimeError(
                    f"could not resolve SEC CIK for {company.name}; confirm and set "
                    "CompanyConfig.sec_cik explicitly in companies.py "
                    "(look it up at https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany)"
                )
            log.info("resolved CIK=%s for %s", cik, company.name)

        with conn.cursor() as cur:
            cur.execute("UPDATE companies SET sec_cik = %s WHERE id = %s", (cik, company_id))

        filings = sec_edgar.list_13f_filings(cik)
        log.info("found %d 13F-HR filing(s) in recent window for %s", len(filings), company.name)

        for filing in filings:
            if filing.report_date < MIN_REPORT_DATE:
                continue

            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM sec13f_filings WHERE accession_number = %s",
                    (filing.accession_number,),
                )
                if cur.fetchone():
                    continue  # already ingested

            log.info("fetching information table for %s (report date %s)", filing.accession_number, filing.report_date)
            try:
                holdings = sec_edgar.fetch_information_table(cik, filing.accession_number)
            except Exception:  # noqa: BLE001
                # Very old filings (pre-2013 XML mandate) or one-off format
                # quirks can make a specific filing unparseable. Skip it
                # rather than aborting every later (parseable) filing too.
                log.warning("skipping unparseable filing %s", filing.accession_number, exc_info=True)
                continue

            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sec13f_filings (company_id, accession_number, period_of_report, filed_at, source_url)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        company_id,
                        filing.accession_number,
                        filing.report_date,
                        filing.filing_date,
                        f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}",
                    ),
                )
                filing_id = cur.fetchone()[0]

                for h in holdings:
                    cur.execute(
                        """
                        INSERT INTO sec13f_holdings
                            (filing_id, issuer_name, cusip, class_title, value_usd_thousands, shares, share_type, put_call)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (filing_id, h.issuer_name, h.cusip, h.class_title, h.value_usd_thousands, h.shares, h.share_type, h.put_call),
                    )
            items_seen += len(holdings)

            diff_sec13f_holdings(conn, company_id, filing_id)

        finish_scrape_run(conn, run_id, "success", items_seen=items_seen)
    except Exception as exc:  # noqa: BLE001
        log.exception("sec13f job failed for %s", company.name)
        conn.rollback()
        finish_scrape_run(conn, run_id, "error", items_seen=items_seen, error_message=str(exc))


def main() -> None:
    # Each company gets its own connection/transaction so one company's
    # failure can't leave a later company's queries stuck in an aborted
    # transaction.
    for company in COMPANIES:
        with get_conn() as conn:
            _run_for_company(conn, company)


if __name__ == "__main__":
    main()
