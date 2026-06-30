'use client';

import { motion } from 'framer-motion';

interface ProbBarProps {
  probA: number;
  delay?: number;
}

export function ProbBar({ probA, delay = 0.2 }: ProbBarProps) {
  const pct = Math.round(probA * 100);
  return (
    <div className="relative h-2 bg-bg rounded-full overflow-hidden border border-border">
      <motion.div
        className="absolute inset-y-0 left-0 bg-accent rounded-full"
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.9, delay, ease: [0.16, 1, 0.3, 1] }}
      />
      <motion.div
        className="absolute inset-y-0 left-0 bg-gradient-to-r from-accent/60 to-accent blur-sm rounded-full"
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.9, delay, ease: [0.16, 1, 0.3, 1] }}
      />
    </div>
  );
}
