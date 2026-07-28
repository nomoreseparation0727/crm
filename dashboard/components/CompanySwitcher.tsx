"use client";

import { useRouter } from "next/navigation";

interface Props {
  companies: { slug: string | null; name: string }[];
  currentSlug: string;
}

export default function CompanySwitcher({ companies, currentSlug }: Props) {
  const router = useRouter();

  return (
    <select
      value={currentSlug}
      onChange={(e) => router.push(`/${e.target.value}`)}
      className="text-sm rounded-md px-2 py-1 border bg-transparent"
      style={{ borderColor: "var(--border)", color: "var(--text-primary)" }}
      aria-label="Switch company"
    >
      {companies.map((c) => (
        <option key={c.slug} value={c.slug ?? undefined}>
          {c.name}
        </option>
      ))}
    </select>
  );
}
