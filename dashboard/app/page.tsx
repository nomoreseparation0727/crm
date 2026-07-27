import AumChart from "@/components/AumChart";
import EventFeed from "@/components/EventFeed";
import { COMPANY_NAME } from "@/lib/constants";
import { getAumHistory, getCompany, getRecentChangeEvents } from "@/lib/queries";

// Data changes every scrape run -- never prerender/cache a stale snapshot.
export const dynamic = "force-dynamic";

export default async function OverviewPage() {
  const company = await getCompany(COMPANY_NAME);

  if (!company) {
    return (
      <div className="card p-6 text-sm" style={{ color: "var(--text-muted)" }}>
        No data yet for &quot;{COMPANY_NAME}&quot;. Run the scraper at least
        once (see the scraper/ README) to seed the database.
      </div>
    );
  }

  const [aumHistory, events] = await Promise.all([
    getAumHistory(company.id),
    getRecentChangeEvents(company.id),
  ]);

  const latestAum = aumHistory.at(-1);
  const points = aumHistory.map((p) => ({
    date: new Date(p.observed_at).toLocaleDateString("en-CA", { year: "2-digit", month: "short" }),
    amount: Number(p.aum_amount),
  }));

  return (
    <div className="flex flex-col gap-8">
      <section>
        <div className="flex items-baseline justify-between mb-3">
          <h1 className="text-xl font-semibold">AUM trend</h1>
          {latestAum && (
            <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
              latest: {latestAum.aum_currency} {(Number(latestAum.aum_amount) / 1_000_000_000).toFixed(1)}B
            </span>
          )}
        </div>
        <AumChart points={points} currency={latestAum?.aum_currency ?? "CAD"} />
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3">Recent activity</h2>
        <EventFeed events={events} />
      </section>
    </div>
  );
}
