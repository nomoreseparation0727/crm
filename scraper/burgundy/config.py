import os


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


class Config:
    """Central place for env-driven settings that are actually secret/
    environment-specific. Per-company facts (name, website, URLs) live in
    companies.py instead -- they're public info, not config, so there's no
    reason to push them through env vars once you're tracking more than one
    company."""

    @property
    def database_url(self) -> str:
        return _require("DATABASE_URL")

    @property
    def sec_edgar_user_agent(self) -> str:
        # SEC requires every automated caller to identify itself with a real
        # contact (name/company + email). Requests without this get 403/429'd.
        # See https://www.sec.gov/os/webmaster-faq#developers
        return _require("SEC_EDGAR_USER_AGENT")


config = Config()
