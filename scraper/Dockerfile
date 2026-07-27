FROM python:3.12-slim

WORKDIR /app

COPY scraper/requirements.txt ./scraper/requirements.txt
RUN pip install --no-cache-dir -r scraper/requirements.txt

COPY db ./db
COPY scraper ./scraper

ENV PYTHONPATH=/app/scraper

RUN chmod +x scraper/entrypoint.sh

ENTRYPOINT ["scraper/entrypoint.sh"]
