import type { Metadata } from 'next';
import './globals.css';
import { Nav } from '@/components/layout/nav';
import { Footer } from '@/components/layout/footer';

export const metadata: Metadata = {
  title: 'VLR Analytics — Valorant match intelligence',
  description:
    'Match prediction, performance analysis, and roster intelligence for competitive Valorant. Built on every Tier 1 and Challengers match since 2024.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen flex flex-col">
        <Nav />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
