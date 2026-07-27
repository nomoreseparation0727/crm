import type { ChangeEvent } from "@/lib/queries";
import { formatDateTime } from "@/lib/format";

const EVENT_LABELS: Record<string, { label: string; color: string }> = {
  new: { label: "new", color: "var(--status-good)" },
  joined: { label: "joined", color: "var(--status-good)" },
  increased: { label: "increased", color: "var(--status-good)" },
  removed: { label: "removed", color: "var(--status-critical)" },
  left: { label: "left", color: "var(--status-critical)" },
  decreased: { label: "decreased", color: "var(--status-critical)" },
  title_change: { label: "title change", color: "var(--text-secondary)" },
};

const ENTITY_LABELS: Record<string, string> = {
  aum: "AUM",
  fund_holding: "Fund holding",
  sec13f_holding: "13F holding",
  executive: "Team",
};

export default function EventFeed({ events }: { events: ChangeEvent[] }) {
  if (events.length === 0) {
    return (
      <div className="card p-6 text-sm" style={{ color: "var(--text-muted)" }}>
        No changes detected yet. Change events appear here once at least two
        scrape runs have observed the same entity.
      </div>
    );
  }

  return (
    <ul className="card divide-y" style={{ borderColor: "var(--border)" }}>
      {events.map((event) => {
        const meta = EVENT_LABELS[event.event_type] ?? { label: event.event_type, color: "var(--text-secondary)" };
        return (
          <li key={event.id} className="flex items-start justify-between gap-4 px-4 py-3 text-sm">
            <div>
              <span className="text-xs uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
                {ENTITY_LABELS[event.entity_type] ?? event.entity_type}
              </span>
              <div style={{ color: "var(--text-primary)" }}>
                <span className="font-medium">{event.entity_ref ?? "—"}</span>{" "}
                <span style={{ color: meta.color }}>{meta.label}</span>
                {event.old_value && event.new_value && (
                  <span style={{ color: "var(--text-secondary)" }}>
                    {" "}({event.old_value} → {event.new_value})
                  </span>
                )}
              </div>
            </div>
            <time className="shrink-0 text-xs" style={{ color: "var(--text-muted)" }}>
              {formatDateTime(event.detected_at)}
            </time>
          </li>
        );
      })}
    </ul>
  );
}
