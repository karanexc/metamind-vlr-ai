'use client';

import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  BarChart, Bar, ScatterChart, Scatter, XAxis, YAxis, ZAxis, Tooltip,
  CartesianGrid, ResponsiveContainer, Cell, ReferenceLine, LabelList,
} from 'recharts';
import { Search, Zap, Target, Crosshair, Shield } from 'lucide-react';
import {
  api,
  type AbilitySummary, type AbilityAgent, type AbilityPlayer,
  type AbilityImpact, type MapImpact, type VctGameListItem, type VctGameRounds, type AbilityBreakdown,
  type VctRoundDetail, type VctTimelineEvent,
} from '@/lib/api';
import { cn } from '@/lib/utils';

const ROLE_HEX: Record<string, string> = {
  Duelist: '#fb7185',
  Initiator: '#fbbf24',
  Controller: '#a78bfa',
  Sentinel: '#34d399',
};
const AXIS = '#71717a';
const GRID = '#27272a';
const ACCENT = '#FA4454';
const TEAM_HEX = ['#FA4454', '#60a5fa']; // team A / team B

type Tab = 'impact' | 'agents' | 'players' | 'rounds';

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-surface border border-border rounded-2xl p-4">
      <div className="text-[0.65rem] uppercase tracking-widest text-ink-dim mb-1">{label}</div>
      <div className="font-mono text-2xl font-semibold text-ink tabular">{value}</div>
      {sub && <div className="text-[0.7rem] text-ink-dim mt-0.5">{sub}</div>}
    </div>
  );
}

function ChartCard({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div className="bg-surface border border-border rounded-2xl p-4">
      <div className="mb-2">
        <div className="text-sm font-semibold text-ink">{title}</div>
        {subtitle && <div className="text-[0.7rem] text-ink-dim">{subtitle}</div>}
      </div>
      <div className="h-64">{children}</div>
    </div>
  );
}

function EVENT_ICON(k: string): string {
  return k === 'kill' ? '✕' : k === 'ult' ? '⚡' : k === 'plant' ? '◆' : k === 'defuse' ? '✓' : '•';
}

function RoundTimeline({ round, teamA, teamB }: { round: VctRoundDetail; teamA: string; teamB: string }) {
  const events = (round.timeline ?? []).filter((e) => e.t != null);
  const dur = Math.max(1, ...events.map((e) => e.t ?? 0));
  return (
    <div className="mt-3">
      <div className="flex items-center gap-4 text-[0.7rem] text-ink-dim mb-2">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{ background: TEAM_HEX[0] }} /> {teamA}</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{ background: TEAM_HEX[1] }} /> {teamB}</span>
        <span className="ml-auto">{Math.round(dur)}s round</span>
      </div>
      <div className="relative h-16 bg-bg/40 border border-border rounded-lg">
        {/* center line */}
        <div className="absolute left-0 right-0 top-1/2 h-px bg-border" />
        {events.map((e, i) => {
          const left = `${((e.t ?? 0) / dur) * 100}%`;
          const isA = e.team === 0;
          const top = e.k === 'kill' ? (isA ? '18%' : '62%') : isA ? '30%' : '52%';
          return (
            <div
              key={i}
              className="absolute -translate-x-1/2 text-[0.7rem] font-bold leading-none"
              style={{ left, top, color: e.team == null ? AXIS : TEAM_HEX[e.team] }}
              title={`${(e.t ?? 0).toFixed(1)}s · ${e.k}${e.slot ? ` (${e.slot})` : ''}`}
            >
              {EVENT_ICON(e.k)}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function AbilitiesPage() {
  const [summary, setSummary] = useState<AbilitySummary | null>(null);
  const [impact, setImpact] = useState<AbilityImpact | null>(null);
  const [breakdown, setBreakdown] = useState<AbilityBreakdown | null>(null);
  const [mapImpact, setMapImpact] = useState<MapImpact[]>([]);
  const [agents, setAgents] = useState<AbilityAgent[]>([]);
  const [players, setPlayers] = useState<AbilityPlayer[]>([]);
  const [selectedMap, setSelectedMap] = useState('');
  const [tab, setTab] = useState<Tab>('impact');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  // rounds tab
  const [games, setGames] = useState<VctGameListItem[]>([]);
  const [gameSearch, setGameSearch] = useState('');
  const [gameRounds, setGameRounds] = useState<VctGameRounds | null>(null);
  const [selectedRound, setSelectedRound] = useState<number | null>(null);

  useEffect(() => {
    Promise.all([
      api.abilitiesSummary().catch(() => null),
      api.abilitiesImpactMaps().catch(() => [] as MapImpact[]),
      api.abilitiesImpactBreakdown().catch(() => null),
    ])
      .then(([s, m, b]) => {
        setSummary(s);
        setMapImpact(m);
        setBreakdown(b);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    api.abilitiesImpact(selectedMap).then(setImpact).catch(() => setImpact(null));
    api.abilitiesAgents(5, selectedMap).then(setAgents).catch(() => setAgents([]));
  }, [selectedMap]);

  useEffect(() => {
    if (tab !== 'players') return;
    api.abilitiesPlayers(search, 60).then(setPlayers).catch(() => setPlayers([]));
  }, [tab, search]);

  useEffect(() => {
    if (tab !== 'rounds') return;
    api.abilitiesGames({ search: gameSearch, limit: 60 }).then(setGames).catch(() => setGames([]));
  }, [tab, gameSearch]);

  const hasData = !!summary && summary.games > 0;

  const scatterData = useMemo(
    () =>
      agents.map((a) => ({
        x: a.ability_casts_per_round,
        y: a.win_rate,
        z: a.games,
        agent: a.agent,
        role: a.role ?? '',
      })),
    [agents],
  );

  function loadGame(id: string) {
    setSelectedRound(null);
    setGameRounds(null);
    api.abilitiesGameRounds(id).then((g) => {
      setGameRounds(g);
      const important = g.rounds?.find((r) => r.is_map_point || r.is_clutch);
      setSelectedRound(important?.round_number ?? g.rounds?.[0]?.round_number ?? null);
    }).catch(() => setGameRounds(null));
  }

  const activeRound = gameRounds?.rounds?.find((r) => r.round_number === selectedRound) ?? null;

  return (
    <div className="max-w-7xl mx-auto px-6 lg:px-8 py-16">
      {/* Hero */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-2 text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
          <Zap className="w-3.5 h-3.5 text-accent" />
          Ability impact · VCT esports telemetry
        </div>
        <h1 className="text-display font-semibold tracking-tight text-gradient">
          Does the utility win the round?
        </h1>
        <p className="mt-4 text-base text-ink-soft max-w-2xl">
          Measured ability + ultimate usage from real VCT matches, tied to round
          outcomes — who used what, when, and whether it won. Historical corpus,
          separate from the live vlr data.
        </p>
      </motion.div>

      {/* Empty state */}
      {!loading && !hasData && (
        <div className="mt-8 bg-surface border border-border rounded-2xl p-8 text-center">
          <Target className="w-6 h-6 text-ink-dim mx-auto mb-3" />
          <div className="text-ink font-medium mb-1">No VCT ability data imported yet</div>
          <p className="text-sm text-ink-soft">Populate it once from Riot&apos;s public dataset:</p>
          <code className="mt-3 inline-block bg-bg border border-border rounded-lg px-3 py-2 text-xs text-ink-soft font-mono">
            python -m src.vlr.cli import-vct-abilities --tier vct-international --year 2024
          </code>
        </div>
      )}

      {hasData && (
        <>
          {/* Headline impact cards */}
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.12 }}
            className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-3"
          >
            <StatCard
              label="First blood → round win"
              value={impact ? `${impact.first_blood_win_rate}%` : '—'}
              sub="win the opening duel, win the round"
            />
            <StatCard
              label="Higher-utility team wins"
              value={impact ? `${impact.utility_edge_win_rate}%` : '—'}
              sub="of rounds where one side out-utilities the other"
            />
            <StatCard
              label="Ult beats no-ult"
              value={impact ? `${impact.ult_win_rate}%` : '—'}
              sub="when one team ults and the other doesn't"
            />
            <StatCard label="Rounds analysed" value={impact ? impact.rounds.toLocaleString() : '—'} />
          </motion.div>

          {/* Map filter + tabs */}
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}
            className="mt-8 flex flex-wrap items-center justify-between gap-4"
          >
            <div className="flex gap-1 p-1 bg-surface border border-border rounded-xl">
              {(['impact', 'agents', 'players', 'rounds'] as Tab[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={cn(
                    'px-4 py-1.5 text-sm font-medium rounded-lg transition-all capitalize',
                    tab === t ? 'bg-accent text-white shadow-lg shadow-accent/20'
                      : 'text-ink-soft hover:text-ink hover:bg-surface-hover',
                  )}
                >
                  {t}
                </button>
              ))}
            </div>
            {(tab === 'impact' || tab === 'agents') && mapImpact.length > 0 && (
              <select
                value={selectedMap}
                onChange={(e) => setSelectedMap(e.target.value)}
                className="px-3 py-2 bg-surface border border-border rounded-lg text-sm text-ink focus:outline-none focus:border-border-strong"
              >
                <option value="">All maps</option>
                {mapImpact.map((m) => (
                  <option key={m.map} value={m.map}>{m.map}</option>
                ))}
              </select>
            )}
          </motion.div>

          {/* IMPACT TAB */}
          {tab === 'impact' && (
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mt-6 space-y-4">
              {/* High-signal per-agent impact */}
              <div className="grid md:grid-cols-2 gap-4">
                <div className="bg-surface border border-border rounded-2xl p-4">
                  <div className="text-sm font-semibold text-ink">Opening duel — who wins the entry</div>
                  <div className="text-[0.7rem] text-ink-dim mb-3">round win% when this agent draws first blood · ranked by volume</div>
                  <div className="space-y-1.5">
                    {(breakdown?.first_blood ?? []).slice(0, 8).map((a) => (
                      <RankBar key={a.agent} label={a.agent} pct={a.win_pct} sub={`${a.first_bloods} FBs`} />
                    ))}
                    {(!breakdown || breakdown.first_blood.length === 0) && <EmptyRow />}
                  </div>
                </div>
                <div className="bg-surface border border-border rounded-2xl p-4">
                  <div className="text-sm font-semibold text-ink">Ult conversion — which ults swing rounds</div>
                  <div className="text-[0.7rem] text-ink-dim mb-3">round win% when this agent spends their ultimate</div>
                  <div className="space-y-1.5">
                    {(breakdown?.ult_conversion ?? []).slice(0, 8).map((a) => (
                      <RankBar key={a.agent} label={a.agent} pct={a.win_pct} sub={`${a.ult_rounds} ults`} />
                    ))}
                    {(!breakdown || breakdown.ult_conversion.length === 0) && <EmptyRow />}
                  </div>
                </div>
              </div>

              {/* Composition meta */}
              <div className="bg-surface border border-border rounded-2xl p-4">
                <div className="text-sm font-semibold text-ink">Composition — win% by role make-up</div>
                <div className="text-[0.7rem] text-ink-dim mb-3">the comp meta: how a team&apos;s role split affects winning</div>
                <div className="space-y-1.5">
                  {(breakdown?.role_comps ?? []).slice(0, 6).map((c) => (
                    <RankBar key={c.label} label={c.label} pct={c.win_pct} sub={`${c.games} games`} wide />
                  ))}
                  {(!breakdown || breakdown.role_comps.length === 0) && <EmptyRow />}
                </div>
              </div>

              <ChartCard
                title="The meta map"
                subtitle="utility per round × win rate · bubble = games · colour = role"
              >
                <ResponsiveContainer>
                  <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 0 }}>
                    <CartesianGrid stroke={GRID} />
                    <XAxis type="number" dataKey="x" name="Utility/round" stroke={AXIS} tick={{ fontSize: 11, fill: AXIS }}
                      label={{ value: 'utility / round', position: 'insideBottom', offset: -8, fill: AXIS, fontSize: 11 }} />
                    <YAxis type="number" dataKey="y" name="Win %" stroke={AXIS} tick={{ fontSize: 11, fill: AXIS }} unit="%" />
                    <ZAxis type="number" dataKey="z" range={[40, 400]} />
                    <ReferenceLine y={50} stroke={AXIS} strokeDasharray="3 3" />
                    <Tooltip
                      cursor={{ strokeDasharray: '3 3' }}
                      contentStyle={{ background: '#18181b', border: `1px solid ${GRID}`, borderRadius: 8, fontSize: 12 }}
                      formatter={(v: any, n: any) => [v, n]}
                      labelFormatter={() => ''}
                      content={({ payload }: any) => {
                        const p = payload?.[0]?.payload;
                        if (!p) return null;
                        return (
                          <div className="bg-bg border border-border rounded-lg px-3 py-2 text-xs">
                            <div className="font-semibold text-ink">{p.agent}</div>
                            <div className="text-ink-dim">{p.role}</div>
                            <div className="text-ink-soft mt-1">{p.x} util/rd · {p.y}% win · {p.z} games</div>
                          </div>
                        );
                      }}
                    />
                    <Scatter data={scatterData}>
                      {scatterData.map((d, i) => (
                        <Cell key={i} fill={ROLE_HEX[d.role] ?? ACCENT} fillOpacity={0.8} />
                      ))}
                    </Scatter>
                  </ScatterChart>
                </ResponsiveContainer>
              </ChartCard>

              <div className="grid md:grid-cols-2 gap-4">
                <ChartCard title="Utility edge → round win" subtitle="win rate by how much a team out-utilities the enemy that round">
                  <ResponsiveContainer>
                    <BarChart data={impact?.util_diff_buckets ?? []} margin={{ top: 10, right: 10, bottom: 0, left: -10 }}>
                      <CartesianGrid stroke={GRID} vertical={false} />
                      <XAxis dataKey="bucket" stroke={AXIS} tick={{ fontSize: 10, fill: AXIS }} />
                      <YAxis stroke={AXIS} tick={{ fontSize: 11, fill: AXIS }} unit="%" domain={[0, 100]} />
                      <ReferenceLine y={50} stroke={AXIS} strokeDasharray="3 3" />
                      <Tooltip contentStyle={{ background: '#18181b', border: `1px solid ${GRID}`, borderRadius: 8, fontSize: 12 }} />
                      <Bar dataKey="win_rate" radius={[3, 3, 0, 0]}>
                        {(impact?.util_diff_buckets ?? []).map((b, i) => (
                          <Cell key={i} fill={b.win_rate >= 50 ? ACCENT : '#52525b'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </ChartCard>

                <ChartCard title="Ultimates fired → round win" subtitle="win rate by number of ults a team spends in the round">
                  <ResponsiveContainer>
                    <BarChart data={impact?.ult_buckets ?? []} margin={{ top: 10, right: 10, bottom: 0, left: -10 }}>
                      <CartesianGrid stroke={GRID} vertical={false} />
                      <XAxis dataKey="ults" stroke={AXIS} tick={{ fontSize: 11, fill: AXIS }} />
                      <YAxis stroke={AXIS} tick={{ fontSize: 11, fill: AXIS }} unit="%" domain={[0, 100]} />
                      <ReferenceLine y={50} stroke={AXIS} strokeDasharray="3 3" />
                      <Tooltip contentStyle={{ background: '#18181b', border: `1px solid ${GRID}`, borderRadius: 8, fontSize: 12 }} />
                      <Bar dataKey="win_rate" fill={ACCENT} radius={[3, 3, 0, 0]}>
                        <LabelList dataKey="win_rate" position="top" fill={AXIS} fontSize={10} formatter={(v: any) => `${v}%`} />
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </ChartCard>
              </div>

              {/* by-condition + map impact */}
              <div className="grid md:grid-cols-2 gap-4">
                <div className="bg-surface border border-border rounded-2xl p-4">
                  <div className="text-sm font-semibold text-ink mb-3">How rounds are won — and the utility behind them</div>
                  <div className="space-y-2">
                    {(impact?.by_condition ?? []).map((c) => (
                      <div key={c.condition} className="flex items-center justify-between text-sm">
                        <span className="text-ink-soft">{c.condition}</span>
                        <span className="font-mono text-ink-dim tabular">
                          {c.rounds} rds · {c.avg_util} util · {c.avg_ults} ults
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="bg-surface border border-border rounded-2xl p-4 overflow-x-auto">
                  <div className="text-sm font-semibold text-ink mb-3">Impact by map</div>
                  <table className="w-full text-sm min-w-[420px]">
                    <thead>
                      <tr className="text-[0.65rem] uppercase tracking-widest text-ink-dim">
                        <th className="text-left font-medium pb-2">Map</th>
                        <th className="text-right font-medium pb-2">Util edge win%</th>
                        <th className="text-right font-medium pb-2">Ult win%</th>
                        <th className="text-right font-medium pb-2">Games</th>
                      </tr>
                    </thead>
                    <tbody>
                      {mapImpact.map((m) => (
                        <tr key={m.map} className="border-t border-border">
                          <td className="py-1.5 text-ink">{m.map}</td>
                          <td className="py-1.5 text-right font-mono text-accent tabular">{m.utility_edge_win_rate}%</td>
                          <td className="py-1.5 text-right font-mono text-ink-soft tabular">{m.ult_win_rate}%</td>
                          <td className="py-1.5 text-right font-mono text-ink-dim tabular">{m.games}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </motion.div>
          )}

          {/* AGENTS TAB */}
          {tab === 'agents' && (
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
              className="mt-6 bg-surface border border-border rounded-2xl overflow-x-auto">
              <table className="w-full min-w-[720px] text-sm">
                <thead>
                  <tr className="border-b border-border text-[0.65rem] uppercase tracking-widest text-ink-dim">
                    <th className="text-left font-medium px-5 py-3">Agent</th>
                    <th className="text-left font-medium px-5 py-3">Role</th>
                    <th className="text-right font-medium px-5 py-3">Games</th>
                    <th className="text-right font-medium px-5 py-3">Utility / round</th>
                    <th className="text-right font-medium px-5 py-3">Ults / game</th>
                    <th className="text-right font-medium px-5 py-3">K/D</th>
                    <th className="text-right font-medium px-5 py-3">Win %</th>
                  </tr>
                </thead>
                <tbody>
                  {agents.map((a) => (
                    <tr key={a.agent} className="border-b border-border last:border-0 hover:bg-bg/20">
                      <td className="px-5 py-3 font-semibold text-ink">{a.agent}</td>
                      <td className="px-5 py-3">
                        <span className="text-[0.7rem] font-medium" style={{ color: ROLE_HEX[a.role ?? ''] ?? AXIS }}>
                          {a.role ?? '—'}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-right font-mono tabular text-ink-soft">{a.games}</td>
                      <td className="px-5 py-3 text-right font-mono tabular text-accent font-semibold">{a.ability_casts_per_round}</td>
                      <td className="px-5 py-3 text-right font-mono tabular text-ink-soft">{a.ults_per_game}</td>
                      <td className="px-5 py-3 text-right font-mono tabular text-ink-soft">{a.kd}</td>
                      <td className="px-5 py-3 text-right font-mono tabular text-ink-soft">{a.win_rate}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </motion.div>
          )}

          {/* PLAYERS TAB */}
          {tab === 'players' && (
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mt-6 space-y-4">
              <div className="relative w-72">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-dim" />
                <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search players…"
                  className="pl-9 pr-4 py-2 w-full bg-surface border border-border rounded-lg text-sm text-ink placeholder:text-ink-dim focus:outline-none focus:border-border-strong" />
              </div>
              <div className="bg-surface border border-border rounded-2xl overflow-x-auto">
                <table className="w-full min-w-[680px] text-sm">
                  <thead>
                    <tr className="border-b border-border text-[0.65rem] uppercase tracking-widest text-ink-dim">
                      <th className="text-left font-medium px-5 py-3">Player</th>
                      <th className="text-left font-medium px-5 py-3">Team</th>
                      <th className="text-right font-medium px-5 py-3">Games</th>
                      <th className="text-right font-medium px-5 py-3">Utility / round</th>
                      <th className="text-right font-medium px-5 py-3">Ults / game</th>
                      <th className="text-right font-medium px-5 py-3">K/D</th>
                      <th className="text-right font-medium px-5 py-3">Win %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {players.length === 0 && (
                      <tr><td colSpan={7} className="px-5 py-10 text-center text-ink-dim">No players match.</td></tr>
                    )}
                    {players.map((p) => (
                      <tr key={p.player_name} className="border-b border-border last:border-0 hover:bg-bg/20">
                        <td className="px-5 py-3 font-semibold text-ink">{p.player_name}</td>
                        <td className="px-5 py-3 text-ink-dim">{p.team_tag ?? '—'}</td>
                        <td className="px-5 py-3 text-right font-mono tabular text-ink-soft">{p.games}</td>
                        <td className="px-5 py-3 text-right font-mono tabular text-accent font-semibold">{p.ability_casts_per_round}</td>
                        <td className="px-5 py-3 text-right font-mono tabular text-ink-soft">{p.ults_per_game}</td>
                        <td className="px-5 py-3 text-right font-mono tabular text-ink-soft">{p.kd}</td>
                        <td className="px-5 py-3 text-right font-mono tabular text-ink-soft">{p.win_rate}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </motion.div>
          )}

          {/* ROUNDS TAB */}
          {tab === 'rounds' && (
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mt-6 grid lg:grid-cols-[300px_1fr] gap-4">
              {/* game list */}
              <div className="bg-surface border border-border rounded-2xl p-3">
                <div className="relative mb-3">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-dim" />
                  <input value={gameSearch} onChange={(e) => setGameSearch(e.target.value)} placeholder="Search team…"
                    className="pl-9 pr-3 py-2 w-full bg-bg border border-border rounded-lg text-sm text-ink placeholder:text-ink-dim focus:outline-none" />
                </div>
                <div className="max-h-[520px] overflow-y-auto space-y-1">
                  {games.map((g) => (
                    <button key={g.game_id} onClick={() => loadGame(g.game_id)}
                      className={cn('w-full text-left px-3 py-2 rounded-lg transition-colors',
                        gameRounds?.game?.game_id === g.game_id ? 'bg-accent/10 border border-accent/30' : 'hover:bg-bg/40 border border-transparent')}>
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium text-ink truncate">{g.team_a_tag ?? '?'} <span className="text-ink-dim">v</span> {g.team_b_tag ?? '?'}</span>
                        <span className="font-mono text-xs text-ink-soft tabular">{g.score_a}-{g.score_b}</span>
                      </div>
                      <div className="text-[0.7rem] text-ink-dim">{g.map ?? '—'} · {g.year}</div>
                    </button>
                  ))}
                  {games.length === 0 && <div className="text-center text-sm text-ink-dim py-8">No games.</div>}
                </div>
              </div>

              {/* round detail */}
              <div className="bg-surface border border-border rounded-2xl p-4 min-h-[300px]">
                {!gameRounds?.found && <div className="text-center text-ink-dim py-16">Pick a game to inspect its rounds.</div>}
                {gameRounds?.found && gameRounds.rounds && (() => {
                  const teamA = gameRounds.game?.team_a_tag ?? 'A';
                  const teamB = gameRounds.game?.team_b_tag ?? 'B';
                  const rnds = gameRounds.rounds ?? [];
                  const scoreA = rnds.filter((r) => r.winner_tag === teamA).length;
                  const scoreB = rnds.filter((r) => r.winner_tag === teamB).length;
                  const tt = (tag: string) => gameRounds.teams?.find((t) => t.team_tag === tag);
                  const roster = (tag: string) =>
                    (gameRounds.players ?? []).filter((p) => p.team_tag === tag).sort((a, b) => b.kills - a.kills);
                  const h = gameRounds.highlights;
                  const utilA = tt(teamA)?.util ?? 0;
                  const utilB = tt(teamB)?.util ?? 0;
                  const utilTotal = Math.max(1, utilA + utilB);
                  return (
                  <>
                    {/* score header */}
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3 text-sm">
                        <span className={cn('font-semibold', gameRounds.game?.winner_tag === teamA ? 'text-accent' : 'text-ink')}>{teamA}</span>
                        <span className="font-mono text-lg tabular text-ink">{scoreA}<span className="text-ink-dim mx-0.5">–</span>{scoreB}</span>
                        <span className={cn('font-semibold', gameRounds.game?.winner_tag === teamB ? 'text-accent' : 'text-ink')}>{teamB}</span>
                      </div>
                      <span className="text-xs text-ink-dim">{gameRounds.game?.map} · {gameRounds.game?.year}</span>
                    </div>

                    {/* impact highlights */}
                    {h && (
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
                        <Highlight label="Most utility" name={h.most_utility?.player_name}
                          sub={h.most_utility ? `${h.most_utility.agent} · ${h.most_utility.value}` : undefined} />
                        <Highlight label="Most ults" name={h.most_ults?.player_name}
                          sub={h.most_ults ? `${h.most_ults.agent} · ${h.most_ults.value}` : undefined} />
                        <Highlight label="Top fragger" name={h.top_fragger?.player_name}
                          sub={h.top_fragger ? `${h.top_fragger.agent} · ${h.top_fragger.value}k` : undefined} />
                        <Highlight label="Utility-edge rounds" name={`${h.utility_edge_rounds}/${h.total_rounds}`} sub="won by more util" />
                      </div>
                    )}

                    {/* team utility comparison */}
                    <div className="mb-4">
                      <div className="flex justify-between text-[0.7rem] text-ink-dim mb-1">
                        <span style={{ color: TEAM_HEX[0] }}>{teamA} · {utilA} util · {tt(teamA)?.ults ?? 0} ult</span>
                        <span style={{ color: TEAM_HEX[1] }}>{utilB} util · {tt(teamB)?.ults ?? 0} ult · {teamB}</span>
                      </div>
                      <div className="h-2 rounded-full overflow-hidden flex bg-bg">
                        <div style={{ width: `${(utilA / utilTotal) * 100}%`, background: TEAM_HEX[0] }} />
                        <div style={{ width: `${(utilB / utilTotal) * 100}%`, background: TEAM_HEX[1] }} />
                      </div>
                    </div>

                    {/* scoreboard: team / player / agent combined */}
                    <div className="grid md:grid-cols-2 gap-3 mb-5">
                      {[teamA, teamB].map((tag, ti) => (
                        <div key={tag} className="border border-border rounded-xl overflow-hidden">
                          <div className="px-3 py-1.5 text-xs font-semibold flex items-center justify-between border-b border-border" style={{ color: TEAM_HEX[ti] }}>
                            <span>{tag}{gameRounds.game?.winner_tag === tag ? ' ✓' : ''}</span>
                            <span className="text-ink-dim font-normal">util · ult · K/D</span>
                          </div>
                          <table className="w-full text-xs">
                            <tbody>
                              {roster(tag).map((p) => (
                                <tr key={p.handle} className="border-t border-border first:border-0">
                                  <td className="px-3 py-1.5 text-ink font-medium truncate max-w-[90px]">{p.player_name}</td>
                                  <td className="px-1 py-1.5 text-ink-dim truncate" style={{ color: ROLE_HEX[p.role ?? ''] ?? undefined }}>{p.agent ?? '—'}</td>
                                  <td className="px-2 py-1.5 text-right font-mono tabular text-accent font-semibold">{p.ability_casts}</td>
                                  <td className="px-2 py-1.5 text-right font-mono tabular text-ink-soft">{p.ult_casts}</td>
                                  <td className="px-3 py-1.5 text-right font-mono tabular text-ink-soft">{p.kills}/{p.deaths}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ))}
                    </div>

                    {/* round-by-round */}
                    <div className="text-[0.65rem] font-semibold uppercase tracking-widest text-ink-dim mb-2">
                      Round by round {h?.decisive_round ? `· decisive: R${h.decisive_round}` : ''}
                    </div>
                    <div className="flex flex-wrap gap-1.5 mb-4">
                      {rnds.map((r) => (
                        <button key={r.round_number} onClick={() => setSelectedRound(r.round_number)}
                          title={[r.is_pistol && 'pistol', r.is_map_point && 'map point', r.is_clutch && 'clutch'].filter(Boolean).join(' · ') || undefined}
                          className={cn('w-8 h-8 rounded-md text-xs font-mono tabular border transition-colors',
                            selectedRound === r.round_number ? 'bg-accent text-white border-accent'
                              : r.is_map_point ? 'border-amber-400/50 text-amber-400 hover:bg-amber-400/10'
                                : r.is_clutch ? 'border-violet-400/50 text-violet-300 hover:bg-violet-400/10'
                                  : 'border-border text-ink-soft hover:bg-bg/40')}>
                          {r.round_number}
                        </button>
                      ))}
                    </div>
                    {activeRound && (
                      <div className="border-t border-border pt-4">
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
                          <span className="font-semibold text-ink">Round {activeRound.round_number}</span>
                          <span className="text-accent font-medium">{activeRound.winner_tag} won</span>
                          <span className="text-ink-dim">{(activeRound.win_condition ?? '').replace('_', ' ').toLowerCase()}</span>
                          {activeRound.is_pistol && <Badge icon={<Crosshair className="w-3 h-3" />} label="pistol" />}
                          {activeRound.is_map_point && <Badge icon={<Target className="w-3 h-3" />} label="map point" />}
                          {activeRound.is_clutch && <Badge icon={<Shield className="w-3 h-3" />} label="clutch" />}
                        </div>
                        <div className="mt-2 flex gap-6 text-xs text-ink-soft font-mono">
                          <span>utility {activeRound.winner_util} <span className="text-ink-dim">vs</span> {activeRound.loser_util}</span>
                          <span>ults {activeRound.winner_ults} <span className="text-ink-dim">vs</span> {activeRound.loser_ults}</span>
                          <span>first blood: {activeRound.opening_kill_tag ?? '—'}</span>
                        </div>
                        <RoundTimeline round={activeRound}
                          teamA={gameRounds.game?.team_a_tag ?? 'A'} teamB={gameRounds.game?.team_b_tag ?? 'B'} />
                        <div className="mt-2 text-[0.7rem] text-ink-dim">
                          • ability &nbsp; ⚡ ult &nbsp; ✕ kill &nbsp; ◆ plant &nbsp; ✓ defuse — position = seconds into the round
                        </div>
                      </div>
                    )}
                  </>
                  );
                })()}
              </div>
            </motion.div>
          )}
        </>
      )}

      {/* Methodology */}
      <div className="mt-8 text-xs text-ink-dim max-w-3xl leading-relaxed">
        <span className="font-medium text-ink-soft">Methodology:</span> ability
        usage is derived from Riot&apos;s per-tick state telemetry (a cast = a
        charge drop within a round; an ult = a ready ult spent). Round outcomes,
        spike events and kills come from the event stream. Impact is measured as
        correlation/timing — the utility that <em>shaped</em> the round-winning
        play, not proven causation. Data: Riot VCT esports dataset, 2022–2024,
        historical. &quot;Important&quot; rounds = pistol / map-point / clutch (1vX).
      </div>
    </div>
  );
}

function Badge({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[0.7rem] font-medium bg-bg border border-border text-ink-soft">
      {icon}{label}
    </span>
  );
}

function Highlight({ label, name, sub }: { label: string; name?: string | null; sub?: string }) {
  return (
    <div className="bg-bg/40 border border-border rounded-lg px-3 py-2">
      <div className="text-[0.6rem] uppercase tracking-widest text-ink-dim">{label}</div>
      <div className="text-sm font-semibold text-ink truncate">{name ?? '—'}</div>
      {sub && <div className="text-[0.65rem] text-ink-dim truncate">{sub}</div>}
    </div>
  );
}

function RankBar({ label, pct, sub, wide }: { label: string; pct: number; sub?: string; wide?: boolean }) {
  return (
    <div className="flex items-center gap-3 text-xs">
      <div className={cn('text-ink truncate', wide ? 'w-40 md:w-56' : 'w-20')} title={label}>{label}</div>
      <div className="flex-1 h-4 bg-bg rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${Math.min(100, Math.max(0, pct))}%`, background: pct >= 50 ? ACCENT : '#52525b' }} />
      </div>
      <div className="w-10 text-right font-mono tabular text-ink font-semibold">{pct}%</div>
      {sub && <div className="w-16 text-right text-ink-dim tabular">{sub}</div>}
    </div>
  );
}

function EmptyRow() {
  return <div className="text-xs text-ink-dim py-3 text-center">Not enough data yet — import more games.</div>;
}
