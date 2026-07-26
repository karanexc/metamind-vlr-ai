'use client';

import { cn } from '@/lib/utils';

/**
 * Loading placeholder. Renders a subtly pulsing block so sections keep their
 * shape while data is in flight instead of collapsing to nothing.
 */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-md bg-surface-hover/70 border border-border/40',
        className,
      )}
    />
  );
}
