'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Menu, X } from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
  { href: '/', label: 'Home' },
  { href: '/predict', label: 'Predict' },
  { href: '/match-analysis', label: 'Match Analysis' },
  { href: '/fantasy', label: 'Fantasy' },
  { href: '/pickem', label: "Pick'em" },
  { href: '/teams', label: 'Teams' },
  { href: '/players', label: 'Players' },
];

export function Nav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const isActive = (href: string) =>
    href === '/' ? pathname === '/' : pathname.startsWith(href);

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

        {/* Desktop nav — sliding active pill */}
        <nav className="hidden md:flex items-center gap-1">
          {navItems.map((item) => {
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'relative px-3 py-1.5 text-sm font-medium rounded-md transition-colors',
                  active ? 'text-ink' : 'text-ink-soft hover:text-ink',
                )}
              >
                {active && (
                  <motion.span
                    layoutId="nav-pill"
                    className="absolute inset-0 bg-surface border border-border/60 rounded-md"
                    transition={{ type: 'spring', stiffness: 400, damping: 32 }}
                  />
                )}
                <span className="relative z-10">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Mobile toggle */}
        <button
          className="md:hidden text-ink-soft hover:text-ink transition-colors"
          onClick={() => setOpen((o) => !o)}
          aria-label="Toggle menu"
        >
          {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile menu */}
      <AnimatePresence>
        {open && (
          <motion.nav
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
            className="md:hidden overflow-hidden border-t border-border/50 bg-bg/95 backdrop-blur-md"
          >
            <div className="px-6 py-3 flex flex-col gap-1">
              {navItems.map((item) => {
                const active = isActive(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setOpen(false)}
                    className={cn(
                      'px-3 py-2 text-sm font-medium rounded-md transition-colors',
                      active
                        ? 'text-ink bg-surface'
                        : 'text-ink-soft hover:text-ink hover:bg-surface/50',
                    )}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </motion.nav>
        )}
      </AnimatePresence>
    </header>
  );
}
