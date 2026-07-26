'use client';

import { useCallback, useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { api, type LiveStatus } from '@/lib/api';
import { cn } from '@/lib/utils';

function timeAgo(iso: string | null): string {
  if (!iso) return 'not yet';
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '—';
  const sec = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  return `${Math.floor(hr / 24)}d ago`;
}

/**
 * Subtle pill that shows when data was last refreshed and lets the user pull
 * live data on demand (calls POST /live/refresh). Fails soft when the API is
 * unreachable — it just shows "Refresh data".
 */
export function LiveRefresh({ className }: { className?: string }) {
  const [status, setStatus] = useState<LiveStatus | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api.liveStatus().then(setStatus).catch(() => {});
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function refresh() {
    if (busy) return;
    setBusy(true);
    try {
      await api.refresh();
      load();
    } catch {
      /* ignore — offline */
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      onClick={refresh}
      disabled={busy}
      title="Refresh live data now"
      className={cn(
        'group inline-flex items-center gap-1.5 px-3 py-1 bg-surface border border-border rounded-full text-xs text-ink-soft hover:text-ink hover:border-border-strong transition-colors disabled:opacity-60',
        className,
      )}
    >
      <RefreshCw
        className={cn(
          'w-3 h-3 text-ink-dim group-hover:text-accent transition-colors',
          busy && 'animate-spin',
        )}
      />
      <span>
        {busy ? 'Refreshing…' : status?.last_run ? `Updated ${timeAgo(status.last_run)}` : 'Refresh data'}
      </span>
    </button>
  );
}
