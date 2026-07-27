"""Snapshot-diffing engine.

Every source module appends new rows (see db/migrations/0001_init.sql --
nothing is ever UPDATEd in place). These functions are called right after a
new snapshot/filing is stored; each one compares the just-inserted batch
against the previous batch for the same entity and writes rows into
change_events. The dashboard only ever reads change_events for its activity
feed -- it never recomputes diffs itself.

"Batch" comparisons (fund holdings, executives) key off `observed_at`: each
scrape run stamps every row it inserts with the same timestamp, so grouping
by observed_at reconstructs "what the full snapshot looked like at time T".
"""
from __future__ import annotations

import json
from typing import Optional

VALUE_CHANGE_THRESHOLD_PCT = 10.0  # ignore noise smaller than this


def _insert_event(conn, company_id: int, entity_type: str, entity_ref: str, event_type: str,
                   old_value: Optional[str], new_value: Optional[str], detail: Optional[dict] = None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO change_events (company_id, entity_type, entity_ref, event_type, old_value, new_value, detail)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (company_id, entity_type, entity_ref, event_type, old_value, new_value, json.dumps(detail) if detail else None),
        )


def diff_sec13f_holdings(conn, company_id: int, new_filing_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT company_id, period_of_report FROM sec13f_filings WHERE id = %s", (new_filing_id,))
        _, period = cur.fetchone()

        cur.execute(
            """
            SELECT id FROM sec13f_filings
            WHERE company_id = %s AND period_of_report < %s
            ORDER BY period_of_report DESC LIMIT 1
            """,
            (company_id, period),
        )
        prev_row = cur.fetchone()

        cur.execute(
            "SELECT issuer_name, value_usd_thousands FROM sec13f_holdings WHERE filing_id = %s",
            (new_filing_id,),
        )
        new_holdings = {name: value for name, value in cur.fetchall()}

        if prev_row is None:
            # First filing we've ever ingested -- nothing to diff against, but
            # still worth recording that each position exists.
            for name in new_holdings:
                _insert_event(conn, company_id, "sec13f_holding", name, "new", None, "initial")
            return

        prev_filing_id = prev_row[0]
        cur.execute(
            "SELECT issuer_name, value_usd_thousands FROM sec13f_holdings WHERE filing_id = %s",
            (prev_filing_id,),
        )
        old_holdings = {name: value for name, value in cur.fetchall()}

    for name, new_value in new_holdings.items():
        if name not in old_holdings:
            _insert_event(conn, company_id, "sec13f_holding", name, "new", None, str(new_value))
            continue
        old_value = old_holdings[name]
        if old_value and new_value and old_value > 0:
            pct_change = (float(new_value) - float(old_value)) / float(old_value) * 100
            if pct_change >= VALUE_CHANGE_THRESHOLD_PCT:
                _insert_event(conn, company_id, "sec13f_holding", name, "increased", str(old_value), str(new_value),
                               {"pct_change": round(pct_change, 1)})
            elif pct_change <= -VALUE_CHANGE_THRESHOLD_PCT:
                _insert_event(conn, company_id, "sec13f_holding", name, "decreased", str(old_value), str(new_value),
                               {"pct_change": round(pct_change, 1)})

    for name, old_value in old_holdings.items():
        if name not in new_holdings:
            _insert_event(conn, company_id, "sec13f_holding", name, "removed", str(old_value), None)


def diff_fund_holdings(conn, company_id: int, fund_id: int, observed_at) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT stock_name, weight_pct FROM fund_holdings_snapshots WHERE fund_id = %s AND observed_at = %s",
            (fund_id, observed_at),
        )
        new_holdings = {name: weight for name, weight in cur.fetchall()}

        cur.execute(
            """
            SELECT DISTINCT observed_at FROM fund_holdings_snapshots
            WHERE fund_id = %s AND observed_at < %s
            ORDER BY observed_at DESC LIMIT 1
            """,
            (fund_id, observed_at),
        )
        prev_row = cur.fetchone()
        if prev_row is None:
            for name in new_holdings:
                _insert_event(conn, company_id, "fund_holding", name, "new", None, "initial")
            return

        cur.execute(
            "SELECT stock_name, weight_pct FROM fund_holdings_snapshots WHERE fund_id = %s AND observed_at = %s",
            (fund_id, prev_row[0]),
        )
        old_holdings = {name: weight for name, weight in cur.fetchall()}

    for name, new_weight in new_holdings.items():
        if name not in old_holdings:
            _insert_event(conn, company_id, "fund_holding", name, "new", None, str(new_weight))
        elif old_holdings[name] != new_weight:
            direction = "increased" if (new_weight or 0) > (old_holdings[name] or 0) else "decreased"
            _insert_event(conn, company_id, "fund_holding", name, direction, str(old_holdings[name]), str(new_weight))

    for name, old_weight in old_holdings.items():
        if name not in new_holdings:
            _insert_event(conn, company_id, "fund_holding", name, "removed", str(old_weight), None)


def diff_executives(conn, company_id: int, observed_at) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT person_name, title FROM executives_snapshots WHERE company_id = %s AND observed_at = %s",
            (company_id, observed_at),
        )
        new_people = {name: title for name, title in cur.fetchall()}

        cur.execute(
            """
            SELECT DISTINCT observed_at FROM executives_snapshots
            WHERE company_id = %s AND observed_at < %s
            ORDER BY observed_at DESC LIMIT 1
            """,
            (company_id, observed_at),
        )
        prev_row = cur.fetchone()
        if prev_row is None:
            for name in new_people:
                _insert_event(conn, company_id, "executive", name, "new", None, "initial")
            return

        cur.execute(
            "SELECT person_name, title FROM executives_snapshots WHERE company_id = %s AND observed_at = %s",
            (company_id, prev_row[0]),
        )
        old_people = {name: title for name, title in cur.fetchall()}

    for name, new_title in new_people.items():
        if name not in old_people:
            _insert_event(conn, company_id, "executive", name, "joined", None, new_title)
        elif old_people[name] != new_title:
            _insert_event(conn, company_id, "executive", name, "title_change", old_people[name], new_title)

    for name, old_title in old_people.items():
        if name not in new_people:
            _insert_event(conn, company_id, "executive", name, "left", old_title, None)


def diff_aum(conn, company_id: int, new_snapshot_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT aum_amount, aum_currency, observed_at FROM aum_snapshots WHERE id = %s",
            (new_snapshot_id,),
        )
        new_amount, currency, observed_at = cur.fetchone()

        cur.execute(
            """
            SELECT aum_amount FROM aum_snapshots
            WHERE company_id = %s AND observed_at < %s AND aum_currency = %s
            ORDER BY observed_at DESC LIMIT 1
            """,
            (company_id, observed_at, currency),
        )
        prev_row = cur.fetchone()

    if prev_row is None or new_amount is None:
        return
    old_amount = prev_row[0]
    if old_amount is None or old_amount == new_amount:
        return
    direction = "increased" if new_amount > old_amount else "decreased"
    _insert_event(conn, company_id, "aum", currency, direction, str(old_amount), str(new_amount))
