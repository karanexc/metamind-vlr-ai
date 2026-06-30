'use client';

import { motion } from 'framer-motion';
import { Counter } from './counter';
import { cn } from '@/lib/utils';

interface StatTileProps {
  label: string;
  value: number | string;
  sub?: string;
  mono?: boolean;
  index?: number; // for stagger animation
}

export function StatTile({ label, value, sub, mono = true, index = 0 }: StatTileProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: index * 0.08, ease: [0.16, 1, 0.3, 1] }}
      className="group relative bg-surface border border-border rounded-2xl p-5 hover:border-border-strong transition-colors duration-300"
    >
      <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-2.5">
        {label}
      </div>
      <div
        className={cn(
          'text-3xl font-semibold tracking-tight text-ink tabular leading-none',
          mono && 'font-mono',
        )}
      >
        {typeof value === 'number' ? <Counter value={value} /> : value}
      </div>
      {sub && (
        <div className="text-xs text-ink-soft mt-2.5 leading-relaxed">{sub}</div>
      )}
    </motion.div>
  );
}
