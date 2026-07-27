import { query } from "./db";

export interface Company {
  id: number;
  name: string;
  website: string | null;
  sec_cik: string | null;
}

export async function getCompany(name: string): Promise<Company | null> {
  const rows = await query<Company>(
    "SELECT id, name, website, sec_cik FROM companies WHERE name = $1",
    [name]
  );
  return rows[0] ?? null;
}

export interface AumPoint {
  observed_at: string;
  aum_amount: string;
  aum_currency: string;
}

export async function getAumHistory(companyId: number): Promise<AumPoint[]> {
  return query<AumPoint>(
    `SELECT observed_at, aum_amount, aum_currency
     FROM aum_snapshots
     WHERE company_id = $1 AND aum_amount IS NOT NULL
     ORDER BY observed_at ASC`,
    [companyId]
  );
}

export interface ChangeEvent {
  id: number;
  entity_type: string;
  entity_ref: string | null;
  event_type: string;
  detected_at: string;
  old_value: string | null;
  new_value: string | null;
  detail: Record<string, unknown> | null;
}

export async function getRecentChangeEvents(companyId: number, limit = 30): Promise<ChangeEvent[]> {
  return query<ChangeEvent>(
    `SELECT id, entity_type, entity_ref, event_type, detected_at, old_value, new_value, detail
     FROM change_events
     WHERE company_id = $1
     ORDER BY detected_at DESC
     LIMIT $2`,
    [companyId, limit]
  );
}

export interface Sec13FHolding {
  issuer_name: string;
  class_title: string | null;
  value_usd_thousands: string | null;
  shares: string | null;
}

export interface Sec13FFilingSummary {
  id: number;
  period_of_report: string;
  filed_at: string;
}

export async function getLatestSec13FFiling(companyId: number): Promise<Sec13FFilingSummary | null> {
  const rows = await query<Sec13FFilingSummary>(
    `SELECT id, period_of_report, filed_at
     FROM sec13f_filings
     WHERE company_id = $1
     ORDER BY period_of_report DESC
     LIMIT 1`,
    [companyId]
  );
  return rows[0] ?? null;
}

export async function getSec13FHoldings(filingId: number): Promise<Sec13FHolding[]> {
  return query<Sec13FHolding>(
    `SELECT issuer_name, class_title, value_usd_thousands, shares
     FROM sec13f_holdings
     WHERE filing_id = $1
     ORDER BY value_usd_thousands DESC NULLS LAST`,
    [filingId]
  );
}

export interface FundHolding {
  fund_name: string;
  stock_name: string;
  stock_country: string | null;
  ticker: string | null;
  weight_pct: string | null;
  observed_at: string;
}

// Anything not explicitly a well-known non-Korean market is treated as
// "unknown" rather than silently excluded -- better to over-show than to
// hide a Korean holding because of a country-string mismatch.
const KOREA_COUNTRY_STRINGS = ["korea", "south korea", "kr"];

export async function getLatestFundHoldings(companyId: number): Promise<FundHolding[]> {
  return query<FundHolding>(
    `SELECT DISTINCT ON (f.id, fhs.stock_name)
            f.name AS fund_name, fhs.stock_name, fhs.stock_country, fhs.ticker,
            fhs.weight_pct, fhs.observed_at
     FROM fund_holdings_snapshots fhs
     JOIN funds f ON f.id = fhs.fund_id
     WHERE f.company_id = $1
     ORDER BY f.id, fhs.stock_name, fhs.observed_at DESC`,
    [companyId]
  );
}

export function isKoreanHolding(stockCountry: string | null): boolean {
  if (!stockCountry) return false;
  return KOREA_COUNTRY_STRINGS.includes(stockCountry.trim().toLowerCase());
}

export interface Executive {
  person_name: string;
  title: string | null;
  bio_excerpt: string | null;
  observed_at: string;
}

export async function getCurrentTeam(companyId: number): Promise<Executive[]> {
  return query<Executive>(
    `WITH latest AS (
       SELECT MAX(observed_at) AS observed_at FROM executives_snapshots WHERE company_id = $1
     )
     SELECT es.person_name, es.title, es.bio_excerpt, es.observed_at
     FROM executives_snapshots es, latest
     WHERE es.company_id = $1 AND es.observed_at = latest.observed_at
     ORDER BY es.person_name`,
    [companyId]
  );
}
