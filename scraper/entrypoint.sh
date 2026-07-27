#!/bin/sh
set -e

echo "Applying DB migrations..."
python3 db/migrate.py

echo "Running scrape jobs..."
python3 -m burgundy.jobs.run_all
