import Link from "next/link";
import { notFound } from "next/navigation";
import CompanySwitcher from "@/components/CompanySwitcher";
import { getAllCompanies } from "@/lib/queries";

export const dynamic = "force-dynamic";

export default async function CompanyLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ company: string }>;
}) {
  const { company: slug } = await params;
  const companies = await getAllCompanies();
  const current = companies.find((c) => c.slug === slug);
  if (!current) {
    notFound();
  }

  const navItems = [
    { href: `/${slug}`, label: "Overview" },
    { href: `/${slug}/holdings`, label: "Holdings" },
    { href: `/${slug}/team`, label: "Team" },
  ];

  return (
    <>
      <header className="border-b" style={{ borderColor: "var(--border)" }}>
        <div className="mx-auto max-w-5xl px-6 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="font-semibold">{current.name}</span>
            <span className="text-sm" style={{ color: "var(--text-muted)" }}>tracker</span>
          </div>
          <div className="flex items-center gap-5">
            <nav className="flex gap-5 text-sm" style={{ color: "var(--text-secondary)" }}>
              {navItems.map((item) => (
                <Link key={item.href} href={item.href} className="hover:opacity-80">
                  {item.label}
                </Link>
              ))}
            </nav>
            <CompanySwitcher companies={companies} currentSlug={slug} />
          </div>
        </div>
      </header>
      <main className="flex-1 mx-auto w-full max-w-5xl px-6 py-8">{children}</main>
    </>
  );
}
