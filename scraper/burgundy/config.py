import os


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


class Config:
    """Central place for env-driven settings. Import `config` (the singleton
    below), don't read os.environ elsewhere."""

    @property
    def database_url(self) -> str:
        return _require("DATABASE_URL")

    @property
    def company_name(self) -> str:
        return os.environ.get("BURGUNDY_COMPANY_NAME", "Burgundy Asset Management")

    @property
    def website_base_url(self) -> str:
        return os.environ.get("BURGUNDY_WEBSITE_URL", "https://www.burgundyasset.com")

    @property
    def sec_edgar_user_agent(self) -> str:
        # SEC requires every automated caller to identify itself with a real
        # contact (name/company + email). Requests without this get 403/429'd.
        # See https://www.sec.gov/os/webmaster-faq#developers
        return _require("SEC_EDGAR_USER_AGENT")

    @property
    def team_page_url(self) -> str:
        return os.environ.get("BURGUNDY_TEAM_URL", f"{self.website_base_url}/our-team/")

    @property
    def funds_index_url(self) -> str:
        return os.environ.get("BURGUNDY_FUNDS_URL", f"{self.website_base_url}/equity/")

    @property
    def sec_cik(self) -> str | None:
        """10-digit, zero-padded CIK for the company's 13F filer entity, if
        known. Set this explicitly once you've looked it up on EDGAR --
        auto-resolution by name is best-effort and can match the wrong
        entity, so a manual override always wins."""
        cik = os.environ.get("BURGUNDY_SEC_CIK")
        if cik:
            return cik.strip().zfill(10)
        return None


config = Config()
