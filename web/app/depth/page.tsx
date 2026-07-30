'use client';

import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { LineChartIcon } from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer,
  Tooltip, ReferenceLine,
} from 'recharts';
import {
  api,
  type EventPlayer,
  type PlayerEventAnalysis,
} from '@/lib/api';
import { getAgents, type ValAgent } from '@/lib/valorant';
import { SAMPLE_EVENTS, SAMPLE_EVENT_PLAYERS, buildSampleAnalysis } from '@/lib/sample-depth';
import { Select } from '@/components/ui/select';
import { StatTile } from '@/components/ui/stat-tile';
import { Skeleton } from '@/components/ui/skeleton';
import { cn, avatarColor, initials } from '@/lib/utils';

const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, '');

type MetricKey = 'rating' | 'acs' | 'adr';
const METRICS: { key: MetricKey; label: string; domain: [number | string, number | string] }[] = [
  { key: 'rating', label: 'Rating', domain: [0.5, 'auto'] },
  { key: 'acs', label: 'ACS', domain: [0, 'auto'] },
  { key: 'adr', label: 'ADR', domain: [0, 'auto'] },
];
const ACCENT = '#FA4454';

export default function DepthPage() {
  const [events, setEvents] = useState<{ id: number; name: string }[]>([]);
  const [eventId, setEventId] = useState<number | null>(null);
  const [eventPlayers, setEventPlayers] = useState<EventPlayer[]>([]);
  const [playerId, setPlayerId] = useState<number | null>(null);
  const [analysis, setAnalysis] = useState<PlayerEventAnalysis | null>(null);
  const [loadingPlayers, setLoadingPlayers] = useState(false);
  const [loading, setLoading] = useState(false);
  const [metric, setMetric] = useState<MetricKey>('rating');
  const [art, setArt] = useState<Record<string, ValAgent>>({});
  const [demo, setDemo] = useState(false);

  useEffect(() => {
    api
      .events()
      .then((e) => {
        setEvents(e);
        setDemo(false);
      })
      .catch(() => {
        // No backend → offline sample tournaments.
        setEvents(SAMPLE_EVENTS);
        setDemo(true);
      });
    getAgents()
      .then((list) => setArt(Object.fromEntries(list.map((a) => [norm(a.name), a]))))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (eventId === null) return;
    setPlayerId(null);
    setAnalysis(null);
    // Sample event → use the built-in player list directly.
    if (eventId < 0) {
      setEventPlayers(SAMPLE_EVENT_PLAYERS);
      return;
    }
    setLoadingPlayers(true);
    setEventPlayers([]);
    api
      .eventPlayers(eventId)
      .then(setEventPlayers)
      .catch(() => {
        setEventPlayers(SAMPLE_EVENT_PLAYERS);
        setDemo(true);
      })
      .finally(() => setLoadingPlayers(false));
  }, [eventId]);

  useEffect(() => {
    if (eventId === null || playerId === null) return;
    // Sample selection → generate a sample analysis locally.
    if (eventId < 0 || playerId < 0) {
      setAnalysis(buildSampleAnalysis(eventId, playerId));
      return;
    }
    setLoading(true);
    setAnalysis(null);
    api
      .playerEventAnalysis(eventId, playerId)
      .then(setAnalysis)
      .catch(() => {
        const s = buildSampleAnalysis(eventId, playerId);
        if (s) {
          setAnalysis(s);
          setDemo(true);
        }
      })
      .finally(() => setLoading(false));
  }, [eventId, playerId]);

  const kd = analysis ? (analysis.total_kills / Math.max(analysis.total_deaths, 1)).toFixed(2) : '—';
  const avgLine = analysis
    ? metric === 'rating' ? 1.0 : metric === 'acs' ? analysis.avg_acs : analysis.avg_adr
    : 0;

  const metricLabel = METRICS.find((m) => m.key === metric)!.label;

  return (
    <div className="max-w-5xl mx-auto px-6 lg:px-8 py-16">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-2 text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
          <LineChartIcon className="w-3.5 h-3.5 text-accent" />
          Depth analysis
        </div>
        <h1 className="text-display font-semibold tracking-tight text-gradient">
          A player, one tournament, map by map.
        </h1>
        <p className="mt-4 text-base text-ink-soft max-w-2xl leading-relaxed">
          Pick a tournament and a player to see their performance trend across every map
          they played — form, consistency, and agent pool for that event.
        </p>
        {demo && (
          <div className="mt-4 inline-flex items-center gap-2 px-3 py-1 bg-warning/10 border border-warning/30 rounded-full text-xs text-warning">
            Sample data — connect the backend for real tournament analysis.
          </div>
        )}
      </motion.div>

      {/* Selectors */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mt-10 bg-surface border border-border rounded-2xl p-6 grid md:grid-cols-2 gap-4"
      >
        <Select
          label="Tournament"
          options={events.map((e) => ({ value: e.id, label: e.name }))}
          value={eventId}
          onChange={(v) => setEventId(Number(v))}
          placeholder={events.length === 0 ? 'Loading events...' : 'Pick a tournament...'}
          disabled={events.length === 0}
        />
        <Select
          label="Player"
          options={eventPlayers.map((p) => ({ value: p.id, label: p.name, sub: `${p.n_maps} maps` }))}
          value={playerId}
          onChange={(v) => setPlayerId(Number(v))}
          placeholder={
            eventId === null ? 'Pick a tournament first' : loadingPlayers ? 'Loading players...' : 'Pick a player...'
          }
          disabled={eventId === null || eventPlayers.length === 0}
        />
      </motion.div>

      {loading && <div className="mt-8"><Skeleton className="h-[420px] rounded-2xl" /></div>}

      {analysis && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="mt-8">
          <h2 className="text-2xl font-semibold text-ink">
            {analysis.player_name} <span className="text-ink-dim font-normal">· {analysis.event_name}</span>
          </h2>

          {/* Stat tiles */}
          <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatTile label="Rating" value={analysis.avg_rating.toFixed(2)} sub={`${analysis.n_maps} maps`} index={0} />
            <StatTile label="ACS" value={Math.round(analysis.avg_acs)} index={1} />
            <StatTile label="K/D" value={kd} sub={`${analysis.total_kills}/${analysis.total_deaths}`} index={2} />
            <StatTile label="Map W%" value={`${Math.round(analysis.map_win_rate)}%`} sub={`${analysis.map_wins}W`} index={3} />
            <StatTile label="KAST" value={`${Math.round(analysis.avg_kast)}%`} index={4} />
            <StatTile label="ADR" value={analysis.avg_adr.toFixed(1)} index={5} />
            <StatTile label="HS%" value={`${Math.round(analysis.avg_hs)}%`} index={6} />
            <StatTile label="Agents" value={analysis.per_agent.length} index={7} />
          </div>

          {/* Trend chart */}
          <div className="mt-8">
            <div className="flex items-center justify-between mb-3">
              <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim">
                Performance trend · {analysis.n_maps} maps
              </div>
              <div className="inline-flex gap-1 p-1 bg-surface border border-border rounded-lg">
                {METRICS.map((m) => (
                  <button
                    key={m.key}
                    onClick={() => setMetric(m.key)}
                    className={cn(
                      'px-3 py-1 text-xs font-medium rounded-md transition-colors',
                      metric === m.key ? 'bg-accent text-white' : 'text-ink-soft hover:text-ink',
                    )}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="bg-surface border border-border rounded-2xl p-4">
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={analysis.series} margin={{ top: 10, right: 12, bottom: 0, left: -12 }}>
                  <CartesianGrid stroke="#1F1F24" vertical={false} />
                  <XAxis dataKey="index" stroke="#6B6B72" tick={{ fill: '#6B6B72', fontSize: 11 }} />
                  <YAxis
                    stroke="#6B6B72"
                    tick={{ fill: '#6B6B72', fontSize: 11 }}
                    domain={METRICS.find((m) => m.key === metric)!.domain as [number | string, number | string]}
                  />
                  <ReferenceLine y={avgLine} stroke="#3A3A40" strokeDasharray="4 4" />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null;
                      const d: any = payload[0].payload;
                      const val = metric === 'rating' ? d.rating.toFixed(2) : Math.round(d[metric]);
                      return (
                        <div className="bg-surface border border-border-strong rounded-lg px-3 py-2 text-xs shadow-lg">
                          <div className="font-semibold text-ink">Map {d.index} · {d.map_name || '—'}</div>
                          <div className="text-ink-dim">vs {d.opponent || '—'} · {d.agent || '—'}</div>
                          <div className="mt-1 text-ink">
                            {metricLabel}: <span className="font-mono font-semibold">{val}</span>
                            <span className={cn('ml-2 font-semibold', d.won ? 'text-success' : 'text-accent')}>
                              {d.won ? 'W' : 'L'}
                            </span>
                          </div>
                        </div>
                      );
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey={metric}
                    stroke={ACCENT}
                    strokeWidth={2}
                    dot={{ fill: ACCENT, r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Per-agent + map results */}
          <div className="mt-8 grid lg:grid-cols-2 gap-6">
            <div>
              <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
                Agents this event
              </div>
              <div className="bg-surface border border-border rounded-2xl overflow-hidden">
                {analysis.per_agent.map((a) => {
                  const info = art[norm(a.agent)];
                  return (
                    <div key={a.agent} className="flex items-center gap-3 px-4 py-2.5 border-b border-border last:border-0">
                      {info?.icon ? (
                        <img src={info.icon} alt={a.agent} loading="lazy" className="w-7 h-7 rounded-md object-contain bg-bg border border-border p-0.5" />
                      ) : (
                        <div className="w-7 h-7 rounded-md flex items-center justify-center text-[10px] font-bold text-white" style={{ background: avatarColor(a.agent) }}>
                          {initials(a.agent)}
                        </div>
                      )}
                      <div className="flex-1 text-sm font-medium text-ink capitalize">{a.agent}</div>
                      <div className="text-xs font-mono text-ink-dim tabular">{a.maps} maps</div>
                      <div className="text-sm font-mono font-semibold text-ink tabular w-12 text-right">{a.avg_rating.toFixed(2)}</div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div>
              <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
                Map log
              </div>
              <div className="bg-surface border border-border rounded-2xl overflow-hidden max-h-[360px] overflow-y-auto">
                {analysis.series.map((m) => (
                  <div key={m.index} className="flex items-center gap-3 px-4 py-2.5 border-b border-border last:border-0">
                    <div className="w-5 text-xs font-mono text-ink-dim tabular">{m.index}</div>
                    <div className={cn('w-5 text-xs font-bold', m.won ? 'text-success' : 'text-accent')}>{m.won ? 'W' : 'L'}</div>
                    <div className="min-w-0 flex-1">
                      <div className="text-sm text-ink truncate">{m.map_name} <span className="text-ink-dim">vs {m.opponent || '—'}</span></div>
                      <div className="text-[0.65rem] text-ink-dim capitalize">{m.agent || '—'}</div>
                    </div>
                    <div className="text-sm font-mono font-semibold text-ink tabular">{m.rating.toFixed(2)}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {!analysis && !loading && (
        <div className="mt-16 text-center text-sm text-ink-dim">
          Pick a tournament and a player to see their depth analysis.
        </div>
      )}
    </div>
  );
}
