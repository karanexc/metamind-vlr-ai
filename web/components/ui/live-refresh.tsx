'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
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
 * Subtle pill that shows when data was last refreshed and triggers a full
 * vlr refresh on demand (matches + rankings + new-player/team profiles + tiers).
 * The refresh runs in the background; the pill polls status while it's running.
 * Fails soft when the API is unreachable.
 */
export function LiveRefresh({ className }: { className?: string }) {
  const [status, setStatus] = useState<LiveStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async (): Promise<LiveStatus | null> => {
    try {
      const s = await api.liveStatus();
      setStatus(s);
      return s;
    } catch {
      return null;
    }
  }, []);

  useEffect(() => {
    load();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [load]);

  function startPolling() {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      const s = await load();
      if (!s || !s.running) {
        if (pollRef.current) clearInterval(pollRef.current);
        pollRef.current = null;
        setBusy(false);
      }
    }, 5000);
  }

  async function refresh() {
    if (busy || status?.running) return;
    setBusy(true);
    try {
      await api.refresh();
      await load();
      startPolling();
    } catch {
      setBusy(false);
    }
  }

  const running = busy || !!status?.running;

  return (
    <button
      onClick={refresh}
      disabled={running}
      title="Refresh all data from vlr.gg now"
      className={cn(
        'group inline-flex items-center gap-1.5 px-3 py-1 bg-surface border border-border rounded-full text-xs text-ink-soft hover:text-ink hover:border-border-strong transition-colors disabled:opacity-70',
        className,
      )}
    >
      <RefreshCw
        className={cn(
          'w-3 h-3 text-ink-dim group-hover:text-accent transition-colors',
          running && 'animate-spin',
        )}
      />
      <span>
        {running ? 'Refreshing…' : status?.last_run ? `Updated ${timeAgo(status.last_run)}` : 'Refresh data'}
      </span>
    </button>
  );
}
