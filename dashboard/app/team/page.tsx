import { COMPANY_NAME } from "@/lib/constants";
import { formatDate } from "@/lib/format";
import { getCompany, getCurrentTeam, getRecentChangeEvents } from "@/lib/queries";
import EventFeed from "@/components/EventFeed";

export const dynamic = "force-dynamic";

export default async function TeamPage() {
  const company = await getCompany(COMPANY_NAME);
  if (!company) {
    return (
      <div className="card p-6 text-sm" style={{ color: "var(--text-muted)" }}>
        No data yet for &quot;{COMPANY_NAME}&quot;.
      </div>
    );
  }

  const [team, allEvents] = await Promise.all([
    getCurrentTeam(company.id),
    getRecentChangeEvents(company.id, 200),
  ]);
  const teamEvents = allEvents.filter((e) => e.entity_type === "executive").slice(0, 30);

  return (
    <div className="flex flex-col gap-10">
      <section>
        <div className="flex items-baseline justify-between mb-3">
          <h1 className="text-xl font-semibold">Current team</h1>
          {team[0] && (
            <span className="text-sm" style={{ color: "var(--text-muted)" }}>
              as of {formatDate(team[0].observed_at)}
            </span>
          )}
        </div>
        {team.length === 0 ? (
          <div className="card p-6 text-sm" style={{ color: "var(--text-muted)" }}>
            No team data scraped yet.
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {team.map((p, i) => (
              <div key={i} className="card p-4">
                <div className="font-medium">{p.person_name}</div>
                {p.title && (
                  <div className="text-sm" style={{ color: "var(--text-secondary)" }}>{p.title}</div>
                )}
                {p.bio_excerpt && (
                  <div className="text-xs mt-2" style={{ color: "var(--text-muted)" }}>{p.bio_excerpt}</div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3">Personnel changes</h2>
        <EventFeed events={teamEvents} />
      </section>
    </div>
  );
}
