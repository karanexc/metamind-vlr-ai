'use client';

import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Layers } from 'lucide-react';
import { api, type AgentMetaItem } from '@/lib/api';
import { getAgents, type ValAgent } from '@/lib/valorant';
import { Skeleton } from '@/components/ui/skeleton';
import { cn, avatarColor, initials } from '@/lib/utils';

type SortKey = 'pick' | 'win' | 'rating';
const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, '');

export default function MetaPage() {
  const [maps, setMaps] = useState<string[]>([]);
  const [selectedMap, setSelectedMap] = useState<string>('all');
  const [agents, setAgents] = useState<AgentMetaItem[]>([]);
  const [art, setArt] = useState<Record<string, ValAgent>>({});
  const [sort, setSort] = useState<SortKey>('pick');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.metaMaps().then(setMaps).catch(console.error);
    getAgents()
      .then((list) => {
        const m: Record<string, ValAgent> = {};
        for (const a of list) m[norm(a.name)] = a;
        setArt(m);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    api
      .metaAgents(selectedMap === 'all' ? undefined : selectedMap, 20)
      .then(setAgents)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [selectedMap]);

  const sorted = useMemo(() => {
    const arr = [...agents];
    arr.sort((a, b) =>
      sort === 'win' ? b.win_rate - a.win_rate : sort === 'rating' ? b.avg_rating - a.avg_rating : b.pick_rate - a.pick_rate,
    );
    return arr;
  }, [agents, sort]);

  const maxPick = Math.max(1, ...agents.map((a) => a.pick_rate));

  return (
    <div className="max-w-5xl mx-auto px-6 lg:px-8 py-16">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-2 text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
          <Layers className="w-3.5 h-3.5 text-accent" />
          Agent meta
        </div>
        <h1 className="text-display font-semibold tracking-tight text-gradient">
          The meta, by the numbers.
        </h1>
        <p className="mt-4 text-base text-ink-soft max-w-2xl leading-relaxed">
          Pick share, win rate and average performance for every agent across the dataset —
          filter by map to see how the meta shifts.
        </p>
      </motion.div>

      {/* Map filter */}
      <div className="mt-8 flex flex-wrap gap-2">
        {['all', ...maps].map((m) => (
          <button
            key={m}
            onClick={() => setSelectedMap(m)}
            className={cn(
              'px-3.5 py-1.5 text-sm font-medium rounded-lg transition-all capitalize',
              selectedMap === m
                ? 'bg-accent text-white shadow-lg shadow-accent/20'
                : 'bg-surface border border-border text-ink-soft hover:text-ink hover:border-border-strong',
            )}
          >
            {m === 'all' ? 'All maps' : m}
          </button>
        ))}
      </div>

      {/* Sort toggle */}
      <div className="mt-4 flex items-center gap-2">
        <span className="text-[0.7rem] uppercase tracking-widest text-ink-dim">Sort by</span>
        <div className="inline-flex gap-1 p-1 bg-surface border border-border rounded-lg">
          {([
            ['pick', 'Pick rate'],
            ['win', 'Win rate'],
            ['rating', 'Rating'],
          ] as [SortKey, string][]).map(([k, label]) => (
            <button
              key={k}
              onClick={() => setSort(k)}
              className={cn(
                'px-3 py-1 text-xs font-medium rounded-md transition-colors',
                sort === k ? 'bg-accent text-white' : 'text-ink-soft hover:text-ink',
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="mt-6 bg-surface border border-border rounded-2xl overflow-hidden">
        <div className="hidden md:grid grid-cols-[40px_1fr_140px_120px_90px_90px] gap-4 px-5 py-3 border-b border-border bg-bg/40 text-[0.65rem] font-medium uppercase tracking-widest text-ink-dim">
          <div>#</div>
          <div>Agent</div>
          <div>Pick share</div>
          <div>Win rate</div>
          <div className="text-right">Rating</div>
          <div className="text-right">ACS</div>
        </div>

        {loading ? (
          Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className="px-5 py-3 border-b border-border last:border-0">
              <Skeleton className="h-9 w-full rounded" />
            </div>
          ))
        ) : sorted.length === 0 ? (
          <div className="px-5 py-12 text-center text-sm text-ink-dim">
            No agent data for this filter.
          </div>
        ) : (
          sorted.map((a, i) => {
            const info = art[norm(a.agent)];
            const win = a.win_rate;
            return (
              <motion.div
                key={a.agent}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: Math.min(i * 0.02, 0.4) }}
                className="grid grid-cols-[40px_1fr] md:grid-cols-[40px_1fr_140px_120px_90px_90px] gap-4 px-5 py-3 border-b border-border last:border-0 items-center hover:bg-surface-hover transition-colors"
              >
                <div className="text-sm font-mono text-ink-dim tabular">{i + 1}</div>

                <div className="flex items-center gap-3 min-w-0">
                  {info?.icon ? (
                    <img
                      src={info.icon}
                      alt={a.agent}
                      loading="lazy"
                      className="w-8 h-8 rounded-md object-contain bg-bg border border-border p-0.5"
                    />
                  ) : (
                    <div
                      className="w-8 h-8 rounded-md flex items-center justify-center text-[10px] font-bold text-white"
                      style={{ background: avatarColor(a.agent) }}
                    >
                      {initials(a.agent)}
                    </div>
                  )}
                  <div className="min-w-0">
                    <div className="text-sm font-semibold text-ink capitalize truncate">{a.agent}</div>
                    <div className="text-[0.65rem] text-ink-dim">
                      {info?.role || '—'} · {a.picks.toLocaleString()} picks
                    </div>
                  </div>
                </div>

                {/* Pick share bar */}
                <div className="hidden md:block">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-bg rounded-full overflow-hidden">
                      <div
                        className="h-full bg-accent rounded-full"
                        style={{ width: `${(a.pick_rate / maxPick) * 100}%` }}
                      />
                    </div>
                    <span className="text-xs font-mono text-ink-soft tabular w-10 text-right">
                      {a.pick_rate}%
                    </span>
                  </div>
                </div>

                {/* Win rate */}
                <div className="hidden md:block">
                  <span
                    className={cn(
                      'font-mono font-semibold tabular text-sm',
                      win >= 52 ? 'text-success' : win <= 48 ? 'text-accent' : 'text-ink-soft',
                    )}
                  >
                    {win}%
                  </span>
                </div>

                <div className="hidden md:block text-right font-mono tabular text-sm text-ink">
                  {a.avg_rating.toFixed(2)}
                </div>
                <div className="hidden md:block text-right font-mono tabular text-sm text-ink-soft">
                  {a.avg_acs}
                </div>
              </motion.div>
            );
          })
        )}
      </div>
    </div>
  );
}
