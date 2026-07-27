"use client";

import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface Props {
  points: { date: string; amount: number }[];
  currency: string;
}

function formatAmount(amount: number, currency: string): string {
  const billions = amount / 1_000_000_000;
  return `${currency} $${billions.toFixed(1)}B`;
}

export default function AumChart({ points, currency }: Props) {
  if (points.length === 0) {
    return (
      <div className="card p-6 text-sm" style={{ color: "var(--text-muted)" }}>
        No AUM observations yet. Once the website scraper runs and finds an
        AUM figure, this chart will populate.
      </div>
    );
  }

  return (
    <div className="card p-4" style={{ height: 320 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
          <XAxis
            dataKey="date"
            stroke="var(--baseline)"
            tick={{ fill: "var(--text-muted)", fontSize: 12 }}
            tickLine={false}
          />
          <YAxis
            stroke="var(--baseline)"
            tick={{ fill: "var(--text-muted)", fontSize: 12 }}
            tickLine={false}
            tickFormatter={(v) => formatAmount(v, currency)}
            width={90}
          />
          <Tooltip
            formatter={(value) => [formatAmount(Number(value), currency), "AUM"]}
            contentStyle={{
              background: "var(--surface-1)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              color: "var(--text-primary)",
              fontSize: 13,
            }}
          />
          <Line
            type="monotone"
            dataKey="amount"
            stroke="var(--series-1)"
            strokeWidth={2}
            dot={{ r: 3, fill: "var(--series-1)" }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
