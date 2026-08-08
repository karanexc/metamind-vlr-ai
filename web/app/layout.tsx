import type { Metadata } from 'next';
import './globals.css';
import { Nav } from '@/components/layout/nav';
import { Footer } from '@/components/layout/footer';
import { AmbientBackground } from '@/components/layout/ambient-background';
import { HudRails } from '@/components/layout/hud-rails';
import { SampleBadge } from '@/components/ui/sample-badge';

export const metadata: Metadata = {
  title: 'VLR Analytics — Valorant match intelligence',
  description:
    'Match prediction, performance analysis, and roster intelligence for competitive Valorant. Built on every Tier 1 and Challengers match since 2024.',
  // Privacy default — don't leak the current URL to third parties as a Referer.
  // NB: this does NOT unblock vlr's image CDN (owcdn.net). That CloudFront guard
  // keys on the browser's Sec-Fetch-Dest/Site headers (which a page can't
  // override), not on Referer — so team logos and player photos are loaded
  // through the same-origin /api/img proxy instead. See lib/utils.ts#proxyImage.
  referrer: 'no-referrer',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen flex flex-col">
        <AmbientBackground />
        <HudRails />
        <div className="relative z-10 flex flex-1 flex-col">
          <Nav />
          <main className="flex-1">{children}</main>
          <Footer />
        </div>
        <SampleBadge />
      </body>
    </html>
  );
}
