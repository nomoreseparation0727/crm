import { COMPANY_NAME } from "@/lib/constants";
import { formatDate, formatPct, formatUsdThousands } from "@/lib/format";
import {
  getCompany,
  getLatestFundHoldings,
  getLatestSec13FFiling,
  getSec13FHoldings,
  isKoreanHolding,
} from "@/lib/queries";

export const dynamic = "force-dynamic";

export default async function HoldingsPage() {
  const company = await getCompany(COMPANY_NAME);
  if (!company) {
    return (
      <div className="card p-6 text-sm" style={{ color: "var(--text-muted)" }}>
        No data yet for &quot;{COMPANY_NAME}&quot;.
      </div>
    );
  }

  const [filing, fundHoldings] = await Promise.all([
    getLatestSec13FFiling(company.id),
    getLatestFundHoldings(company.id),
  ]);
  const sec13fHoldings = filing ? await getSec13FHoldings(filing.id) : [];

  const koreanFundHoldings = fundHoldings.filter((h) => isKoreanHolding(h.stock_country));
  const otherFundHoldings = fundHoldings.filter((h) => !isKoreanHolding(h.stock_country));

  return (
    <div className="flex flex-col gap-10">
      <section>
        <h1 className="text-xl font-semibold mb-1">Korean holdings</h1>
        <p className="text-sm mb-3" style={{ color: "var(--text-muted)" }}>
          Fund fact-sheet holdings tagged as South Korea. This will only show
          Korean equities that Burgundy discloses in a fund&apos;s published
          top holdings -- it is not a full portfolio (SEC 13F below never
          covers Korean-listed shares directly).
        </p>
        <HoldingsTable holdings={koreanFundHoldings} highlight />
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3">Other fund holdings</h2>
        <HoldingsTable holdings={otherFundHoldings} />
      </section>

      <section>
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="text-lg font-semibold">SEC 13F holdings (US-listed / ADRs)</h2>
          {filing && (
            <span className="text-sm" style={{ color: "var(--text-muted)" }}>
              period {formatDate(filing.period_of_report)}
            </span>
          )}
        </div>
        {!filing ? (
          <div className="card p-6 text-sm" style={{ color: "var(--text-muted)" }}>
            No 13F filings ingested yet.
          </div>
        ) : (
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
                  <th className="px-4 py-2 font-medium">Issuer</th>
                  <th className="px-4 py-2 font-medium">Class</th>
                  <th className="px-4 py-2 font-medium text-right">Value</th>
                  <th className="px-4 py-2 font-medium text-right">Shares</th>
                </tr>
              </thead>
              <tbody>
                {sec13fHoldings.map((h, i) => (
                  <tr key={i} className="border-b last:border-0" style={{ borderColor: "var(--border)" }}>
                    <td className="px-4 py-2">{h.issuer_name}</td>
                    <td className="px-4 py-2" style={{ color: "var(--text-secondary)" }}>{h.class_title ?? "—"}</td>
                    <td className="px-4 py-2 text-right tabular-nums">{formatUsdThousands(h.value_usd_thousands)}</td>
                    <td className="px-4 py-2 text-right tabular-nums">{h.shares ? Number(h.shares).toLocaleString() : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function HoldingsTable({
  holdings,
  highlight = false,
}: {
  holdings: Awaited<ReturnType<typeof getLatestFundHoldings>>;
  highlight?: boolean;
}) {
  if (holdings.length === 0) {
    return (
      <div className="card p-6 text-sm" style={{ color: "var(--text-muted)" }}>
        None found yet.
      </div>
    );
  }
  return (
    <div className="card overflow-x-auto" style={highlight ? { borderColor: "var(--series-1)" } : undefined}>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left border-b" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
            <th className="px-4 py-2 font-medium">Fund</th>
            <th className="px-4 py-2 font-medium">Stock</th>
            <th className="px-4 py-2 font-medium">Country</th>
            <th className="px-4 py-2 font-medium text-right">Weight</th>
            <th className="px-4 py-2 font-medium text-right">As of</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h, i) => (
            <tr key={i} className="border-b last:border-0" style={{ borderColor: "var(--border)" }}>
              <td className="px-4 py-2">{h.fund_name}</td>
              <td className="px-4 py-2 font-medium">{h.stock_name}</td>
              <td className="px-4 py-2" style={{ color: "var(--text-secondary)" }}>{h.stock_country ?? "—"}</td>
              <td className="px-4 py-2 text-right tabular-nums">{formatPct(h.weight_pct)}</td>
              <td className="px-4 py-2 text-right" style={{ color: "var(--text-muted)" }}>{formatDate(h.observed_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
