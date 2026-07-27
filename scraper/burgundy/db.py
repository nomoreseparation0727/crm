import contextlib
from typing import Any, Iterator

import psycopg2
import psycopg2.extras

from .config import config


@contextlib.contextmanager
def get_conn() -> Iterator[Any]:
    conn = psycopg2.connect(config.database_url)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_or_create_company(conn, name: str, website: str | None = None) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM companies WHERE name = %s", (name,))
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(
            "INSERT INTO companies (name, website) VALUES (%s, %s) RETURNING id",
            (name, website),
        )
        return cur.fetchone()[0]


def start_scrape_run(conn, source: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO scrape_runs (source, status) VALUES (%s, 'running') RETURNING id",
            (source,),
        )
        return cur.fetchone()[0]


def finish_scrape_run(conn, run_id: int, status: str, items_seen: int = 0, error_message: str | None = None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE scrape_runs
            SET finished_at = now(), status = %s, items_seen = %s, error_message = %s
            WHERE id = %s
            """,
            (status, items_seen, error_message, run_id),
        )


def dict_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
