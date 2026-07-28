"""SEC EDGAR 13F source.

Covers only US-exchange-listed equities and ADRs that a filer reports on
Form 13F (required for US institutional managers with >$100M in 13(f)
securities). This will NOT show Korean ordinary shares held directly --
those come from the website/fact-sheet source instead. It's the one fully
structured, machine-readable, no-auth-required source in this pipeline, so
treat it as ground truth for whatever it does cover.

SEC requires every automated request to send a descriptive User-Agent with
real contact info (see config.sec_edgar_user_agent) or it will 403/429 you.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

import requests

from ..config import config

SEC_BASE = "https://www.sec.gov"
DATA_BASE = "https://data.sec.gov"


def _headers() -> dict:
    return {"User-Agent": config.sec_edgar_user_agent, "Accept-Encoding": "gzip, deflate"}


def resolve_cik(company_name: str) -> Optional[str]:
    """Best-effort CIK lookup by company name via the classic EDGAR company
    search. Prefer setting CompanyConfig.sec_cik explicitly in companies.py --
    this is a fallback for convenience only and can match the wrong entity
    if there are similarly-named filers."""
    resp = requests.get(
        f"{SEC_BASE}/cgi-bin/browse-edgar",
        params={
            "action": "getcompany",
            "company": company_name,
            "type": "13F",
            "dateb": "",
            "owner": "include",
            "count": "40",
            "output": "atom",
        },
        headers=_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    match = re.search(r"CIK=(\d{10})", resp.text)
    if match:
        return match.group(1)
    match = re.search(r"<cik>(\d+)</cik>", resp.text, re.IGNORECASE)
    if match:
        return match.group(1).zfill(10)
    return None


@dataclass
class FilingRef:
    accession_number: str
    form: str
    filing_date: date
    report_date: date
    primary_document: str


def list_13f_filings(cik: str) -> list[FilingRef]:
    """Recent filings for a CIK via the submissions JSON API. Only returns
    what's in the 'recent' window SEC keeps inline; older filings are
    paginated into separate files under filings.files, which we don't
    bother following since this service cares about staying current, not
    backfilling full history on day one."""
    resp = requests.get(f"{DATA_BASE}/submissions/CIK{cik}.json", headers=_headers(), timeout=30)
    resp.raise_for_status()
    data = resp.json()
    recent = data["filings"]["recent"]

    filings = []
    for i, form in enumerate(recent["form"]):
        if form not in ("13F-HR", "13F-HR/A"):
            continue
        filings.append(
            FilingRef(
                accession_number=recent["accessionNumber"][i],
                form=form,
                filing_date=datetime.strptime(recent["filingDate"][i], "%Y-%m-%d").date(),
                report_date=datetime.strptime(recent["reportDate"][i], "%Y-%m-%d").date(),
                primary_document=recent["primaryDocument"][i],
            )
        )
    return filings


@dataclass
class HoldingRow:
    issuer_name: str
    cusip: Optional[str]
    class_title: Optional[str]
    value_usd_thousands: Optional[float]
    shares: Optional[float]
    share_type: Optional[str]
    put_call: Optional[str]


def _local(tag: str) -> str:
    """Strip the XML namespace off a tag name (e.g. '{...}nameOfIssuer' -> 'nameOfIssuer')."""
    return tag.split("}", 1)[-1]


def fetch_information_table(cik: str, accession_number: str) -> list[HoldingRow]:
    """Locate and parse the Form 13F "information table" XML for a filing.

    Every filing folder on EDGAR has a machine-readable directory listing at
    .../index.json; we use that to find whichever file is the info table
    rather than guessing a fixed filename, since filers name it inconsistently.
    """
    acc_no_dashes = accession_number.replace("-", "")
    cik_int = str(int(cik))  # archive paths use the CIK without leading zeros
    folder_url = f"{SEC_BASE}/Archives/edgar/data/{cik_int}/{acc_no_dashes}"

    resp = requests.get(f"{folder_url}/index.json", headers=_headers(), timeout=30)
    resp.raise_for_status()
    items = resp.json()["directory"]["item"]

    info_table_name = None
    for item in items:
        name = item["name"]
        if "infotable" in name.lower() or "information" in name.lower():
            info_table_name = name
            break
    if info_table_name is None:
        # Fall back: some filers ship a single combined XML for the whole
        # submission that includes the info table inline.
        for item in items:
            if item["name"].lower().endswith(".xml"):
                info_table_name = item["name"]
                break
    if info_table_name is None:
        raise ValueError(f"could not locate information table in {folder_url}")

    xml_resp = requests.get(f"{folder_url}/{info_table_name}", headers=_headers(), timeout=30)
    xml_resp.raise_for_status()

    root = ET.fromstring(xml_resp.content)
    holdings: list[HoldingRow] = []
    for info_table in root.iter():
        if _local(info_table.tag) != "infoTable":
            continue

        fields = {}
        for child in info_table:
            fields[_local(child.tag)] = child

        def text(el, path):
            if el is None:
                return None
            found = None
            for sub in el.iter():
                if _local(sub.tag) == path:
                    found = sub.text
                    break
            return found.strip() if found else None

        shares_el = fields.get("shrsOrPrnAmt")
        value_text = fields.get("value").text if fields.get("value") is not None else None

        holdings.append(
            HoldingRow(
                issuer_name=(fields.get("nameOfIssuer").text or "").strip() if fields.get("nameOfIssuer") is not None else "",
                cusip=fields.get("cusip").text.strip() if fields.get("cusip") is not None else None,
                class_title=fields.get("titleOfClass").text.strip() if fields.get("titleOfClass") is not None else None,
                value_usd_thousands=float(value_text) if value_text else None,
                shares=float(text(shares_el, "sshPrnamt")) if text(shares_el, "sshPrnamt") else None,
                share_type=text(shares_el, "sshPrnamtType"),
                put_call=fields.get("putCall").text.strip() if fields.get("putCall") is not None else None,
            )
        )
    return holdings
