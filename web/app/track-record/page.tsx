'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, ReferenceLine, Cell,
} from 'recharts';
import { Check, X, Clock, TrendingUp } from 'lucide-react';
import { api, type PredictionItem, type PredictionAccuracy } from '@/lib/api';
import { TeamLogo } from '@/components/ui/avatar';
import { cn } from '@/lib/utils';

const AXIS = '#71717a';
const GRID = '#27272a';
const ACCENT = '#FA4454';

type Tab = 'upcoming' | 'results';

function pct(item: PredictionItem): number {
  return Math.round(Math.max(item.prob_a, item.prob_b) * 100);
}

function when(iso: string | null): string {
  if (!iso) return 'TBD';
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return 'TBD';
  const diff = t - Date.now();
  const h = Math.round(Math.abs(diff) / 3.6e6);
  if (h < 1) return diff >= 0 ? 'soon' : 'just now';
  if (h < 24) return diff >= 0 ? `in ${h}h` : `${h}h ago`;
  const d = Math.round(h / 24);
  return diff >= 0 ? `in ${d}d` : `${d}d ago`;
}

function AccCard({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent?: boolean }) {
  return (
    <div className={cn('rounded-2xl p-4 border', accent ? 'bg-accent/5 border-accent/30' : 'bg-surface border-border')}>
      <div className="text-[0.65rem] uppercase tracking-widest text-ink-dim mb-1">{label}</div>
      <div className={cn('font-mono text-2xl font-semibold tabular', accent ? 'text-accent' : 'text-ink')}>{value}</div>
      {sub && <div className="text-[0.7rem] text-ink-dim mt-0.5">{sub}</div>}
    </div>
  );
}

export default function TrackRecordPage() {
  const [acc, setAcc] = useState<PredictionAccuracy | null>(null);
  const [upcoming, setUpcoming] = useState<PredictionItem[]>([]);
  const [results, setResults] = useState<PredictionItem[]>([]);
  const [tab, setTab] = useState<Tab>('upcoming');
  const [source, setSource] = useState<'' | 'live' | 'backtest'>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.predictionsAccuracy().catch(() => null),
      api.predictionsUpcoming(50).catch(() => [] as PredictionItem[]),
    ])
      .then(([a, u]) => {
        setAcc(a);
        setUpcoming(u);
        if (u.length === 0) setTab('results');
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (tab !== 'results') return;
    api.predictionsResults(source, 100).then(setResults).catch(() => setResults([]));
  }, [tab, source]);

  const hasData = !!acc && (acc.overall.n > 0 || upcoming.length > 0);

  return (
    <div className="max-w-6xl mx-auto px-6 lg:px-8 py-16">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-2 text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
          <TrendingUp className="w-3.5 h-3.5 text-accent" />
          Track record
        </div>
        <h1 className="text-display font-semibold tracking-tight text-gradient">Our calls vs reality.</h1>
        <p className="mt-4 text-base text-ink-soft max-w-2xl">
          The model&apos;s prediction on real vlr matches, scored against what actually happened.
        </p>
      </motion.div>

      {!loading && !hasData && (
        <div className="mt-8 bg-surface border border-border rounded-2xl p-8 text-center">
          <div className="text-ink font-medium mb-1">No predictions yet</div>
          <code className="mt-2 inline-block bg-bg border border-border rounded-lg px-3 py-2 text-xs text-ink-soft font-mono">
            python -m src.vlr.cli backtest-predictions --limit 200
          </code>
        </div>
      )}

      {hasData && acc && (
        <>
          {/* Accuracy headline */}
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}
            className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-3">
            <AccCard label="Live hit-rate" accent value={acc.live.n ? `${acc.live.hit_rate}%` : '—'}
              sub={acc.live.n ? `${acc.live.correct} / ${acc.live.n} correct` : 'fills as matches finish'} />
            <AccCard label="Backtest hit-rate" value={acc.backtest.n ? `${acc.backtest.hit_rate}%` : '—'}
              sub={acc.backtest.n ? `${acc.backtest.correct} / ${acc.backtest.n} correct` : '—'} />
            <AccCard label="Overall" value={acc.overall.n ? `${acc.overall.hit_rate}%` : '—'} sub={`${acc.overall.n} calls scored`} />
            <AccCard label="Pending" value={`${upcoming.length}`} sub="awaiting results" />
          </motion.div>

          {/* Tabs */}
          <div className="mt-8 flex flex-wrap items-center justify-between gap-4">
            <div className="flex gap-1 p-1 bg-surface border border-border rounded-xl">
              {(['upcoming', 'results'] as Tab[]).map((t) => (
                <button key={t} onClick={() => setTab(t)}
                  className={cn('px-4 py-1.5 text-sm font-medium rounded-lg transition-all capitalize',
                    tab === t ? 'bg-accent text-white shadow-lg shadow-accent/20' : 'text-ink-soft hover:text-ink hover:bg-surface-hover')}>
                  {t}
                </button>
              ))}
            </div>
            {tab === 'results' && (
              <div className="flex gap-1 p-1 bg-surface border border-border rounded-xl text-xs">
                {([['', 'All'], ['live', 'Live'], ['backtest', 'Backtest']] as const).map(([v, label]) => (
                  <button key={v} onClick={() => setSource(v)}
                    className={cn('px-3 py-1 rounded-md transition-colors', source === v ? 'bg-surface-hover text-ink' : 'text-ink-dim hover:text-ink')}>
                    {label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Upcoming */}
          {tab === 'upcoming' && (
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="mt-4 grid md:grid-cols-2 gap-3">
              {upcoming.length === 0 && (
                <div className="md:col-span-2 text-center text-sm text-ink-dim py-12 bg-surface border border-border rounded-2xl">
                  No upcoming calls yet — they appear as the scheduler pulls vlr&apos;s schedule.
                </div>
              )}
              {upcoming.map((p) => {
                const aFav = p.prob_a >= p.prob_b;
                return (
                  <div key={p.match_id} className="bg-surface border border-border rounded-2xl p-4">
                    <div className="flex items-center justify-between text-[0.7rem] text-ink-dim mb-3">
                      <span className="truncate">{p.event ?? 'Match'}</span>
                      <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {when(p.scheduled_at)}</span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <div className={cn('flex items-center gap-2 min-w-0', aFav ? 'text-ink' : 'text-ink-dim')}>
                        <TeamLogo name={p.team_a} logoUrl={p.team_a_logo} size="sm" />
                        <span className="font-semibold truncate">{p.team_a}</span>
                      </div>
                      <span className="text-ink-dim text-xs">vs</span>
                      <div className={cn('flex items-center gap-2 min-w-0 justify-end', !aFav ? 'text-ink' : 'text-ink-dim')}>
                        <span className="font-semibold truncate">{p.team_b}</span>
                        <TeamLogo name={p.team_b} logoUrl={p.team_b_logo} size="sm" />
                      </div>
                    </div>
                    <div className="mt-3 h-1.5 rounded-full overflow-hidden flex bg-bg">
                      <div style={{ width: `${p.prob_a * 100}%`, background: ACCENT }} />
                      <div style={{ width: `${p.prob_b * 100}%`, background: '#3f3f46' }} />
                    </div>
                    <div className="mt-2 text-xs text-ink-soft">
                      Pick: <span className="text-ink font-semibold">{p.predicted_winner}</span>{' '}
                      <span className="font-mono">{pct(p)}%</span>
                      <span className="text-ink-dim"> · {p.confidence}</span>
                    </div>
                  </div>
                );
              })}
            </motion.div>
          )}

          {/* Results — scoreboard cards */}
          {tab === 'results' && (
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="mt-4 space-y-2.5">
              {results.length === 0 && (
                <div className="text-center text-sm text-ink-dim py-12 bg-surface border border-border rounded-2xl">No scored predictions yet.</div>
              )}
              {results.map((p) => {
                const aWon = (p.actual_score_a ?? 0) > (p.actual_score_b ?? 0);
                return (
                  <div key={p.match_id}
                    className={cn('bg-surface border rounded-2xl p-4 border-l-[3px]',
                      p.correct ? 'border-border border-l-emerald-400/70' : 'border-border border-l-rose-400/70')}>
                    <div className="flex items-center gap-4">
                      {/* Matchup */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-4">
                          <div className={cn('flex items-center gap-2 min-w-0', aWon ? 'text-ink font-semibold' : 'text-ink-dim')}>
                            <TeamLogo name={p.team_a} logoUrl={p.team_a_logo} size="sm" />
                            <span className="truncate">{p.team_a}</span>
                          </div>
                          <span className="font-mono tabular text-lg text-ink shrink-0">
                            {p.actual_score_a}<span className="text-ink-dim mx-0.5">–</span>{p.actual_score_b}
                          </span>
                          <div className={cn('flex items-center gap-2 min-w-0', !aWon ? 'text-ink font-semibold' : 'text-ink-dim')}>
                            <TeamLogo name={p.team_b} logoUrl={p.team_b_logo} size="sm" />
                            <span className="truncate">{p.team_b}</span>
                          </div>
                        </div>
                        <div className="mt-1.5 text-xs text-ink-dim">
                          predicted <span className="text-ink-soft font-medium">{p.predicted_winner}</span>{' '}
                          <span className="font-mono">{pct(p)}%</span>
                          {p.event ? <span> · {p.event}</span> : null}
                          {p.source === 'backtest' ? <span className="text-ink-dim"> · backtest</span> : null}
                        </div>
                      </div>
                      {/* Verdict */}
                      <div className="shrink-0">
                        {p.correct ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-400/10 text-emerald-400 border border-emerald-400/30">
                            <Check className="w-3.5 h-3.5" /> correct
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-400/10 text-rose-400 border border-rose-400/30">
                            <X className="w-3.5 h-3.5" /> missed
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </motion.div>
          )}

          {/* Calibration */}
          {acc.calibration.some((c) => c.n > 0) && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}
              className="mt-6 bg-surface border border-border rounded-2xl p-4">
              <div className="text-sm font-semibold text-ink mb-3">Calibration — confidence vs actual win rate</div>
              <div className="h-48">
                <ResponsiveContainer>
                  <BarChart data={acc.calibration} margin={{ top: 8, right: 10, bottom: 0, left: -10 }}>
                    <CartesianGrid stroke={GRID} vertical={false} />
                    <XAxis dataKey="band" stroke={AXIS} tick={{ fontSize: 11, fill: AXIS }} unit="%" />
                    <YAxis stroke={AXIS} tick={{ fontSize: 11, fill: AXIS }} unit="%" domain={[0, 100]} />
                    <ReferenceLine y={50} stroke={AXIS} strokeDasharray="3 3" />
                    <Tooltip contentStyle={{ background: '#18181b', border: `1px solid ${GRID}`, borderRadius: 8, fontSize: 12 }} />
                    <Bar dataKey="actual_win_rate" name="actual win %" radius={[3, 3, 0, 0]}>
                      {acc.calibration.map((_, i) => <Cell key={i} fill={ACCENT} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </motion.div>
          )}
        </>
      )}
    </div>
  );
}
