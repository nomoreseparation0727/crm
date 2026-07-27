#!/usr/bin/env python3
"""Cron entrypoint that runs every source job. This is what Railway's cron
service actually invokes. Each job's failure is isolated so one broken
source doesn't block the other from running.
"""
import logging
import sys

from . import run_sec13f, run_website

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("run_all")


def main() -> int:
    failures = []

    for label, job in (("sec13f", run_sec13f), ("website", run_website)):
        try:
            job.main()
        except Exception as exc:  # noqa: BLE001
            log.error("%s job failed: %s", label, exc)
            failures.append(label)

    if failures:
        log.error("job(s) failed: %s", ", ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
