import { redirect } from "next/navigation";
import { getAllCompanies } from "@/lib/queries";

export const dynamic = "force-dynamic";

export default async function RootPage() {
  const companies = await getAllCompanies();
  const first = companies.find((c) => c.slug === "burgundy") ?? companies[0];

  if (!first?.slug) {
    return (
      <div className="mx-auto max-w-5xl px-6 py-8 text-sm" style={{ color: "var(--text-muted)" }}>
        No companies tracked yet. Run the scraper at least once to seed the database.
      </div>
    );
  }

  redirect(`/${first.slug}`);
}
