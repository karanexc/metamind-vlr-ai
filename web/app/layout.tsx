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
  // vlr's image CDN (owcdn.net) returns 403 for any request carrying a foreign
  // Referer header. Team logos and player photos are served from there, so in
  // production the browser's Referer (the Vercel origin) got them blocked.
  // Emitting <meta name="referrer" content="no-referrer"> site-wide strips the
  // Referer from every subresource request, so the CDN serves the images (200).
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
