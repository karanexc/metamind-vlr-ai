'use client';

import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Users } from 'lucide-react';
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer,
} from 'recharts';
import { api, type PlayerListItem, type PlayerSummary } from '@/lib/api';
import { SAMPLE_PLAYER_LIST, SAMPLE_PLAYER_SUMMARIES } from '@/lib/sample-players';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

// Per-metric domain maxima used to normalise onto the 0–100 radar.
const AXES: { key: string; label: string; max: number; fmt: (s: PlayerSummary) => number }[] = [
  { key: 'rating', label: 'Rating', max: 1.4, fmt: (s) => s.avg_rating },
  { key: 'acs', label: 'ACS', max: 300, fmt: (s) => s.avg_acs },
  { key: 'kast', label: 'KAST', max: 100, fmt: (s) => s.avg_kast },
  { key: 'adr', label: 'ADR', max: 220, fmt: (s) => s.avg_adr },
  { key: 'hs', label: 'HS%', max: 50, fmt: (s) => s.avg_hs },
  { key: 'kd', label: 'K/D', max: 2, fmt: (s) => s.total_kills / Math.max(s.total_deaths, 1) },
];

const COLOR_A = '#FA4454';
const COLOR_B = '#22D3EE';

export default function ComparePage() {
  const [players, setPlayers] = useState<PlayerListItem[]>([]);
  const [idA, setIdA] = useState<number | null>(null);
  const [idB, setIdB] = useState<number | null>(null);
  const [sumA, setSumA] = useState<PlayerSummary | null>(null);
  const [sumB, setSumB] = useState<PlayerSummary | null>(null);
  const [loadingA, setLoadingA] = useState(false);
  const [loadingB, setLoadingB] = useState(false);
  const [demo, setDemo] = useState(false);

  useEffect(() => {
    api
      .players(20)
      .then((p) => {
        setPlayers(p);
        setDemo(false);
      })
      .catch(() => {
        // No backend reachable → fall back to the built-in sample set.
        setPlayers(SAMPLE_PLAYER_LIST);
        setDemo(true);
      });
  }, []);

  // Resolve a summary from the API, falling back to the sample set (also used
  // directly for the negative sample ids).
  async function loadSummary(
    id: number,
    setSum: (s: PlayerSummary | null) => void,
    setLoading: (b: boolean) => void,
  ) {
    setLoading(true);
    setSum(null);
    try {
      if (id < 0) throw new Error('sample');
      setSum(await api.player(id));
    } catch {
      const s = SAMPLE_PLAYER_SUMMARIES[id];
      if (s) {
        setSum(s);
        setDemo(true);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (idA !== null) loadSummary(idA, setSumA, setLoadingA);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idA]);

  useEffect(() => {
    if (idB !== null) loadSummary(idB, setSumB, setLoadingB);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idB]);

  const options = players.map((p) => ({ value: p.id, label: p.name, sub: `${p.n_maps} maps` }));

  const radarData = useMemo(() => {
    return AXES.map((ax) => ({
      metric: ax.label,
      A: sumA ? Math.min(100, (ax.fmt(sumA) / ax.max) * 100) : 0,
      B: sumB ? Math.min(100, (ax.fmt(sumB) / ax.max) * 100) : 0,
    }));
  }, [sumA, sumB]);

  const both = sumA && sumB;

  return (
    <div className="max-w-5xl mx-auto px-6 lg:px-8 py-16">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-2 text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
          <Users className="w-3.5 h-3.5 text-accent" />
          Compare
        </div>
        <h1 className="text-display font-semibold tracking-tight text-gradient">
          Player vs player.
        </h1>
        <p className="mt-4 text-base text-ink-soft max-w-2xl leading-relaxed">
          Put any two players head-to-head across their core performance metrics.
        </p>
        {demo && (
          <div className="mt-4 inline-flex items-center gap-2 px-3 py-1 bg-warning/10 border border-warning/30 rounded-full text-xs text-warning">
            Sample data — connect the backend to compare your full player pool.
          </div>
        )}
      </motion.div>

      {/* Pickers */}
      <div className="mt-10 grid md:grid-cols-2 gap-4">
        <div className="bg-surface border border-border rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: COLOR_A }} />
            <span className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim">Player A</span>
          </div>
          <Select options={options} value={idA} onChange={(v) => setIdA(Number(v))} placeholder="Pick a player..." />
          {sumA && <div className="mt-3 text-lg font-semibold text-ink">{sumA.name}</div>}
        </div>
        <div className="bg-surface border border-border rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: COLOR_B }} />
            <span className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim">Player B</span>
          </div>
          <Select options={options} value={idB} onChange={(v) => setIdB(Number(v))} placeholder="Pick a player..." />
          {sumB && <div className="mt-3 text-lg font-semibold text-ink">{sumB.name}</div>}
        </div>
      </div>

      {(loadingA || loadingB) && !both && (
        <div className="mt-8"><Skeleton className="h-[360px] rounded-2xl" /></div>
      )}

      {both && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mt-8 grid lg:grid-cols-[1fr_1fr] gap-6"
        >
          {/* Radar */}
          <div className="bg-surface border border-border rounded-2xl p-4">
            <ResponsiveContainer width="100%" height={360}>
              <RadarChart data={radarData} outerRadius="70%">
                <PolarGrid stroke="#1F1F24" />
                <PolarAngleAxis dataKey="metric" tick={{ fill: '#A1A1AA', fontSize: 12 }} />
                <Radar name={sumA.name} dataKey="A" stroke={COLOR_A} fill={COLOR_A} fillOpacity={0.28} strokeWidth={2} />
                <Radar name={sumB.name} dataKey="B" stroke={COLOR_B} fill={COLOR_B} fillOpacity={0.2} strokeWidth={2} />
              </RadarChart>
            </ResponsiveContainer>
            <div className="flex items-center justify-center gap-6 text-sm">
              <span className="flex items-center gap-2"><span className="w-3 h-3 rounded-sm" style={{ background: COLOR_A }} />{sumA.name}</span>
              <span className="flex items-center gap-2"><span className="w-3 h-3 rounded-sm" style={{ background: COLOR_B }} />{sumB.name}</span>
            </div>
          </div>

          {/* Raw stat table */}
          <div className="bg-surface border border-border rounded-2xl overflow-hidden">
            {AXES.map((ax) => {
              const a = ax.fmt(sumA);
              const b = ax.fmt(sumB);
              const aBetter = a >= b;
              const fmt = (n: number) => (ax.key === 'rating' || ax.key === 'kd' ? n.toFixed(2) : Math.round(n).toString());
              return (
                <div key={ax.key} className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 px-5 py-3 border-b border-border last:border-0">
                  <div className={cn('font-mono tabular text-right text-lg', aBetter ? 'text-ink font-semibold' : 'text-ink-dim')}>
                    {fmt(a)}
                  </div>
                  <div className="text-[0.65rem] uppercase tracking-widest text-ink-dim w-16 text-center">{ax.label}</div>
                  <div className={cn('font-mono tabular text-lg', !aBetter ? 'text-ink font-semibold' : 'text-ink-dim')}>
                    {fmt(b)}
                  </div>
                </div>
              );
            })}
            <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 px-5 py-3 bg-bg/40">
              <div className="font-mono tabular text-right text-sm text-ink-soft">{sumA.n_maps.toLocaleString()}</div>
              <div className="text-[0.65rem] uppercase tracking-widest text-ink-dim w-16 text-center">Maps</div>
              <div className="font-mono tabular text-sm text-ink-soft">{sumB.n_maps.toLocaleString()}</div>
            </div>
          </div>
        </motion.div>
      )}

      {!both && !loadingA && !loadingB && (
        <div className="mt-16 text-center text-sm text-ink-dim">
          Pick two players above to see the head-to-head.
        </div>
      )}
    </div>
  );
}
