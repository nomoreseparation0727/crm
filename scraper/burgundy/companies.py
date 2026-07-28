"""Registry of asset managers this service tracks.

Adding a company is a 3-line addition here, not a config/env change --
these are public facts (name, website, page paths), not secrets. team_url
and funds_url are best-guess defaults the same way Burgundy's were: they
get corrected once a real deploy's logs show a 404 against the live site
(see README "Adding a new company").
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CompanyConfig:
    slug: str
    name: str
    website: str
    team_url: str
    funds_url: str
    # Currency the firm reports its own AUM in (what gets scraped off their
    # site) -- not the currency of any individual holding.
    aum_currency: str = "USD"
    # 10-digit zero-padded SEC CIK, if confirmed. Leave None to fall back to
    # best-effort name resolution at runtime (see sources/sec_edgar.resolve_cik) --
    # that fallback can match the wrong entity, so fill this in once confirmed.
    sec_cik: Optional[str] = None


COMPANIES = [
    CompanyConfig(
        slug="burgundy",
        name="Burgundy Asset Management",
        website="https://www.burgundyasset.com",
        team_url="https://www.burgundyasset.com/our-team/",
        funds_url="https://www.burgundyasset.com/equity/",
        aum_currency="CAD",
    ),
    CompanyConfig(
        slug="kopernik",
        name="Kopernik Global Investors",
        website="https://www.kopernikglobal.com",
        team_url="https://www.kopernikglobal.com/our-team/",
        funds_url="https://www.kopernikglobal.com/strategies/",
    ),
    CompanyConfig(
        # Name/paths unverified -- the site couldn't be inspected while
        # adding this (see README). Confirm the real company name (likely
        # shown in the site's title tag) once raw_snapshots has a fetch.
        slug="drz",
        name="DRZ",
        website="https://drz-inc.com",
        team_url="https://drz-inc.com/our-team/",
        funds_url="https://drz-inc.com/strategies/",
    ),
]
