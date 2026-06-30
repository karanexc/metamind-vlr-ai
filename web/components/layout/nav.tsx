'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';

const navItems = [
  { href: '/', label: 'Home' },
  { href: '/predict', label: 'Predict' },
  { href: '/match-analysis', label: 'Match Analysis' },
  { href: '/fantasy', label: 'Fantasy' },
  { href: '/teams', label: 'Teams' },
  { href: '/players', label: 'Players' },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 backdrop-blur-md bg-bg/70 border-b border-border/50">
      <div className="max-w-7xl mx-auto px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="relative w-2.5 h-2.5">
            <div className="absolute inset-0 bg-accent rounded-full" />
            <div className="absolute inset-0 bg-accent rounded-full blur-md opacity-50 group-hover:opacity-80 transition-opacity" />
          </div>
          <span className="font-semibold tracking-tight text-ink">
            VLR<span className="text-ink-soft font-normal">Analytics</span>
          </span>
        </Link>

        {/* Nav items */}
        <nav className="hidden md:flex items-center gap-1">
          {navItems.map((item) => {
            const isActive =
              item.href === '/'
                ? pathname === '/'
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'px-3 py-1.5 text-sm font-medium rounded-md transition-colors',
                  isActive
                    ? 'text-ink bg-surface'
                    : 'text-ink-soft hover:text-ink hover:bg-surface/50',
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
