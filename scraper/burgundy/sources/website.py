"""burgundyasset.com source.

IMPORTANT: this module was written without being able to inspect the live
site (it returned HTTP 403 to every fetch attempt during development, likely
bot/WAF protection rather than a hard block -- Railway's outbound IPs and a
realistic browser User-Agent may fare better than the sandbox this was built
in). Because of that, the extraction functions below are deliberately
heuristic pattern-matching rather than fixed CSS selectors tied to a DOM
snapshot: they look for shapes of content ("a heading that looks like a
person's name followed by a short bio", "a number followed by 'billion' near
the word 'assets'") rather than exact class names.

Expect to tune these once the pipeline is actually running against the live
site: every fetch is archived to raw_snapshots (see 0003_raw_snapshots.sql),
so re-tuning means re-running a parser function against stored HTML/text,
not re-scraping.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-CA,en;q=0.9",
}

NAME_RE = re.compile(r"^[A-Z][a-zA-Z.'-]+(?: [A-Z][a-zA-Z.'-]+){1,3}$")
AUM_RE = re.compile(
    r"(?:CAD|C\$|US\$|\$)?\s?([0-9]{1,3}(?:[.,][0-9]+)?)\s?(billion|bn|million|mm)\b",
    re.IGNORECASE,
)


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=BROWSER_HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def fetch_pdf_bytes(url: str) -> bytes:
    resp = requests.get(url, headers=BROWSER_HEADERS, timeout=60)
    resp.raise_for_status()
    return resp.content


@dataclass
class PersonEntry:
    name: str
    title: Optional[str]
    bio_excerpt: Optional[str]


def parse_team_page(html: str) -> list[PersonEntry]:
    """Heuristic: scan heading tags (h2/h3/h4) for text shaped like a
    person's name ("First Last" or "First Middle Last"), then treat the very
    next sibling element with text as their title/bio."""
    soup = BeautifulSoup(html, "html.parser")
    people: list[PersonEntry] = []

    for heading in soup.find_all(["h2", "h3", "h4"]):
        name = heading.get_text(strip=True)
        if not name or not NAME_RE.match(name):
            continue

        title = None
        bio = None
        sib = heading.find_next_sibling()
        texts = []
        while sib and len(texts) < 2:
            t = sib.get_text(" ", strip=True)
            if t:
                texts.append(t)
            sib = sib.find_next_sibling()
        if texts:
            title = texts[0][:200]
        if len(texts) > 1:
            bio = texts[1][:500]

        people.append(PersonEntry(name=name, title=title, bio_excerpt=bio))

    return people


@dataclass
class FundEntry:
    name: str
    url: Optional[str]


def parse_funds_list(html: str, base_url: str) -> list[FundEntry]:
    """Heuristic: any link whose visible text or href mentions 'fund' and
    isn't obvious site chrome (nav/footer boilerplate)."""
    soup = BeautifulSoup(html, "html.parser")
    seen = set()
    funds: list[FundEntry] = []

    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"]
        if not text:
            continue
        if "fund" not in text.lower() and "fund" not in href.lower():
            continue
        if len(text) > 80:  # likely a sentence, not a fund name
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        url = href if href.startswith("http") else requests.compat.urljoin(base_url, href)
        funds.append(FundEntry(name=text, url=url))

    return funds


def find_aum_mentions(html_or_text: str) -> list[tuple[float, str, str]]:
    """Returns (amount, unit, matched_sentence) for every '$X billion'-shaped
    mention found near the word 'assets' -- narrows down candidate AUM
    figures without assuming a specific page layout. Caller should sanity
    check / pick the right one (a page can mention firm-wide AUM alongside
    a single fund's AUM)."""
    soup = BeautifulSoup(html_or_text, "html.parser")
    text = soup.get_text(" ", strip=True)

    results = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if "asset" not in sentence.lower() and "aum" not in sentence.lower():
            continue
        for match in AUM_RE.finditer(sentence):
            amount = float(match.group(1).replace(",", ""))
            unit = match.group(2).lower()
            results.append((amount, unit, sentence.strip()[:300]))
    return results


def parse_fact_sheet_pdf_text(text: str) -> list[dict]:
    """Heuristic extraction of a "top holdings" table from fund fact-sheet
    PDF text (already run through a PDF-to-text step, see pdf_to_text below).
    Looks for lines like "Samsung Electronics Co Ltd    South Korea    4.8%"
    -- i.e. a name, optionally a country, then a percentage. Column layout
    varies a lot between fact sheets, so this only fires on lines that
    unambiguously end in a percentage."""
    holdings = []
    line_re = re.compile(r"^(?P<name>[A-Za-z0-9&.,'\-\s]{3,60}?)\s{2,}(?:(?P<country>[A-Za-z ]{3,30})\s{2,})?(?P<pct>\d{1,2}\.\d)\s?%\s*$")
    for line in text.splitlines():
        m = line_re.match(line.strip())
        if not m:
            continue
        holdings.append(
            {
                "stock_name": m.group("name").strip(),
                "stock_country": (m.group("country") or "").strip() or None,
                "weight_pct": float(m.group("pct")),
            }
        )
    return holdings


def pdf_to_text(pdf_bytes: bytes) -> str:
    import io

    import pdfplumber

    text_parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)
