#!/usr/bin/env python3
"""Cron entrypoint: scrape burgundyasset.com for team/people, fund list +
fact-sheet holdings, and AUM mentions. See sources/website.py for the caveat
that these extractors are heuristic and likely need tuning against the real
DOM after first deploy -- every fetch is archived to raw_snapshots precisely
so that tuning doesn't require re-scraping.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import requests

from ..config import config
from ..db import finish_scrape_run, get_conn, get_or_create_company, start_scrape_run
from ..diff import diff_aum, diff_executives, diff_fund_holdings
from ..sources import website

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("run_website")


def _save_raw(conn, run_id: int, url: str, content_type: str, content: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO raw_snapshots (scrape_run_id, url, content_type, content) VALUES (%s, %s, %s, %s)",
            (run_id, url, content_type, content),
        )


def scrape_team(conn, run_id: int, company_id: int) -> int:
    html = website.fetch_html(config.team_page_url)
    _save_raw(conn, run_id, config.team_page_url, "html", html)

    people = website.parse_team_page(html)
    observed_at = datetime.now(timezone.utc)
    log.info("parsed %d person entries from team page", len(people))

    with conn.cursor() as cur:
        for p in people:
            cur.execute(
                """
                INSERT INTO executives_snapshots (company_id, observed_at, person_name, title, bio_excerpt, source)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (company_id, observed_at, p.name, p.title, p.bio_excerpt, config.team_page_url),
            )

    if people:
        diff_executives(conn, company_id, observed_at)

    for amount, unit, sentence in website.find_aum_mentions(html):
        _store_aum(conn, company_id, amount, unit, config.team_page_url, sentence)

    return len(people)


def _store_aum(conn, company_id: int, amount: float, unit: str, source: str, raw_text: str) -> None:
    multiplier = 1_000_000_000 if unit.startswith(("b", "bn")) else 1_000_000
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO aum_snapshots (company_id, aum_amount, aum_currency, source, raw_text)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (company_id, amount * multiplier, "CAD", source, raw_text),
        )
        snapshot_id = cur.fetchone()[0]
    diff_aum(conn, company_id, snapshot_id)


def scrape_funds(conn, run_id: int, company_id: int) -> int:
    html = website.fetch_html(config.funds_index_url)
    _save_raw(conn, run_id, config.funds_index_url, "html", html)

    funds = website.parse_funds_list(html, config.funds_index_url)
    log.info("found %d candidate fund links", len(funds))

    items_seen = 0
    for f in funds:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO funds (company_id, name, source_url) VALUES (%s, %s, %s) "
                "ON CONFLICT (company_id, name) DO UPDATE SET source_url = EXCLUDED.source_url "
                "RETURNING id",
                (company_id, f.name, f.url),
            )
            fund_id = cur.fetchone()[0]

        if not f.url:
            continue
        try:
            fund_html = website.fetch_html(f.url)
        except requests.RequestException:
            log.warning("could not fetch fund page %s", f.url)
            continue
        _save_raw(conn, run_id, f.url, "html", fund_html)

        for amount, unit, sentence in website.find_aum_mentions(fund_html):
            _store_aum(conn, company_id, amount, unit, f.url, sentence)

        pdf_links = _extract_pdf_links(fund_html, f.url)
        for pdf_url in pdf_links:
            try:
                pdf_bytes = website.fetch_pdf_bytes(pdf_url)
                text = website.pdf_to_text(pdf_bytes)
            except Exception:  # noqa: BLE001
                log.warning("could not fetch/parse fact sheet %s", pdf_url)
                continue
            _save_raw(conn, run_id, pdf_url, "pdf_text", text)

            holdings = website.parse_fact_sheet_pdf_text(text)
            if not holdings:
                continue
            observed_at = datetime.now(timezone.utc)
            with conn.cursor() as cur:
                for h in holdings:
                    cur.execute(
                        """
                        INSERT INTO fund_holdings_snapshots
                            (fund_id, observed_at, stock_name, stock_country, weight_pct, source)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (fund_id, observed_at, h["stock_name"], h["stock_country"], h["weight_pct"], pdf_url),
                    )
            items_seen += len(holdings)
            diff_fund_holdings(conn, company_id, fund_id, observed_at)

    return items_seen


def _extract_pdf_links(html: str, base_url: str) -> list[str]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(" ", strip=True).lower()
        if href.lower().endswith(".pdf") and ("fact" in text or "holding" in text or "commentary" in text or "factsheet" in href.lower()):
            links.append(href if href.startswith("http") else requests.compat.urljoin(base_url, href))
    return links


def main() -> None:
    with get_conn() as conn:
        run_id = start_scrape_run(conn, "website")
        items_seen = 0
        try:
            company_id = get_or_create_company(conn, config.company_name, config.website_base_url)
            items_seen += scrape_team(conn, run_id, company_id)
            items_seen += scrape_funds(conn, run_id, company_id)
            finish_scrape_run(conn, run_id, "success", items_seen=items_seen)
        except Exception as exc:  # noqa: BLE001
            log.exception("website job failed")
            finish_scrape_run(conn, run_id, "error", items_seen=items_seen, error_message=str(exc))
            raise


if __name__ == "__main__":
    main()
