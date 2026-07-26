import Link from 'next/link';

const COLUMNS: { title: string; links: { label: string; href: string }[] }[] = [
  {
    title: 'Tools',
    links: [
      { label: 'Match prediction', href: '/predict' },
      { label: 'AI match analysis', href: '/match-analysis' },
      { label: 'Fantasy mode', href: '/fantasy' },
    ],
  },
  {
    title: 'Explore',
    links: [
      { label: 'Teams', href: '/teams' },
      { label: 'Players', href: '/players' },
    ],
  },
];

export function Footer() {
  return (
    <footer className="border-t border-border/40 mt-32">
      <div className="max-w-7xl mx-auto px-6 lg:px-8 py-12">
        <div className="grid gap-10 md:grid-cols-[1.4fr_1fr_1fr]">
          {/* Brand + blurb */}
          <div>
            <Link href="/" className="flex items-center gap-2.5 group w-fit">
              <div className="relative w-2.5 h-2.5">
                <div className="absolute inset-0 bg-accent rounded-full" />
                <div className="absolute inset-0 bg-accent rounded-full blur-md opacity-50 group-hover:opacity-80 transition-opacity" />
              </div>
              <span className="font-semibold tracking-tight text-ink">
                VLR<span className="text-ink-soft font-normal">Analytics</span>
              </span>
            </Link>
            <p className="mt-4 text-sm text-ink-soft leading-relaxed max-w-xs">
              Match prediction, performance analysis, and roster intelligence for
              competitive Valorant — powered by a custom ML model.
            </p>
            <div className="mt-5 inline-flex items-center gap-1.5 px-3 py-1 bg-surface border border-border rounded-full text-xs text-ink-soft">
              <span className="relative flex w-1.5 h-1.5">
                <span className="absolute inline-flex w-full h-full rounded-full bg-success opacity-75 animate-ping" />
                <span className="relative inline-flex w-1.5 h-1.5 rounded-full bg-success" />
              </span>
              <span className="font-medium">All systems operational</span>
            </div>
          </div>

          {/* Link columns */}
          {COLUMNS.map((col) => (
            <div key={col.title}>
              <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-4">
                {col.title}
              </div>
              <ul className="space-y-2.5">
                {col.links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-sm text-ink-soft hover:text-ink transition-colors"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="mt-12 pt-6 border-t border-border/40 flex flex-col md:flex-row items-center justify-between gap-3">
          <p className="text-xs text-ink-dim">
            Data sourced from vlr.gg · Predictions via custom XGBoost model, grounded by GPT-4o
          </p>
          <p className="text-xs text-ink-dim">
            Built as MSc dissertation research · 2026
          </p>
        </div>
      </div>
    </footer>
  );
}
