import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Burgundy Asset Management Tracker",
  description: "AUM, fund holdings, key personnel, and Korean equity exposure tracking for Burgundy Asset Management.",
};

const NAV_ITEMS = [
  { href: "/", label: "Overview" },
  { href: "/holdings", label: "Holdings" },
  { href: "/team", label: "Team" },
];

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <header className="border-b" style={{ borderColor: "var(--border)" }}>
          <div className="mx-auto max-w-5xl px-6 py-4 flex items-center justify-between">
            <div>
              <span className="font-semibold">Burgundy Asset Management</span>
              <span className="ml-2 text-sm" style={{ color: "var(--text-muted)" }}>tracker</span>
            </div>
            <nav className="flex gap-5 text-sm" style={{ color: "var(--text-secondary)" }}>
              {NAV_ITEMS.map((item) => (
                <Link key={item.href} href={item.href} className="hover:opacity-80">
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="flex-1 mx-auto w-full max-w-5xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
