'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip,
  CartesianGrid,
} from 'recharts';
import {
  api,
  type PlayerListItem,
  type PlayerSummary,
  type RegionalTeam,
  type TeamRosterPlayer,
} from '@/lib/api';
import { Select } from '@/components/ui/select';
import { StatTile } from '@/components/ui/stat-tile';
import { PlayerAvatar, TeamLogo } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
import { cn, countryFlag, proxyImage } from '@/lib/utils';
import { VLR_REGIONS } from '@/lib/regions';

const REGIONS = VLR_REGIONS.map((r) => ({ value: r.slug, label: r.label }));

export default function PlayersPage() {
  const [region, setRegion] = useState<string>('north-america');
  const [topTeams, setTopTeams] = useState<RegionalTeam[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<RegionalTeam | null>(null);
  const [roster, setRoster] = useState<TeamRosterPlayer[]>([]);
  const [allPlayers, setAllPlayers] = useState<PlayerListItem[]>([]);
  const [playerId, setPlayerId] = useState<number | null>(null);
  const [summary, setSummary] = useState<PlayerSummary | null>(null);

  // Load top teams whenever the region tab changes
  useEffect(() => {
    setTopTeams([]);
    setSelectedTeam(null);
    setRoster([]);
    api.regionalTopTeams(region, 5).then(setTopTeams).catch(console.error);
  }, [region]);

  // Load roster when a team is selected
  useEffect(() => {
    if (!selectedTeam) {
      setRoster([]);
      return;
    }
    api
      .teamRoster(selectedTeam.id)
      .then(setRoster)
      .catch(console.error);
  }, [selectedTeam]);

  // Load all players for the fallback dropdown
  useEffect(() => {
    api.players(20).then(setAllPlayers).catch(console.error);
  }, []);

  // Load player detail when one is selected
  useEffect(() => {
    if (playerId !== null) {
      setSummary(null);
      api.player(playerId).then(setSummary).catch(console.error);
      // Scroll to detail
      setTimeout(() => {
        document
          .getElementById('player-detail')
          ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    }
  }, [playerId]);

  const playerOptions = allPlayers.map((p) => ({
    value: p.id,
    label: p.name,
    sub: `${p.n_maps} maps`,
  }));

  const kd = summary
    ? (summary.total_kills / Math.max(summary.total_deaths, 1)).toFixed(2)
    : '—';

  const recentFormChartData = summary
    ? [...summary.recent_form].reverse().map((r: any, i: number) => ({
        i,
        rating: r.rating || 0,
      }))
    : [];

  return (
    <div className="max-w-7xl mx-auto px-6 lg:px-8 py-16">
      {/* Hero */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
          Players
        </div>
        <h1 className="text-display font-semibold tracking-tight text-gradient">
          Browse rosters by region.
        </h1>
        <p className="mt-4 text-base text-ink-soft max-w-2xl">
          Top 5 teams in each vlr.gg region by official rating. Click a team to
          see its current roster. Click a player to dive into their stats.
        </p>
      </motion.div>

      {/* Region tabs */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.15 }}
        className="mt-10 flex flex-wrap gap-1 p-1 bg-surface border border-border rounded-xl"
      >
        {REGIONS.map((r) => (
          <button
            key={r.value}
            onClick={() => setRegion(r.value)}
            className={cn(
              'px-5 py-2 text-sm font-medium rounded-lg transition-all',
              region === r.value
                ? 'bg-accent text-white shadow-lg shadow-accent/20'
                : 'text-ink-soft hover:text-ink hover:bg-surface-hover',
            )}
          >
            {r.label}
          </button>
        ))}
      </motion.div>

      {/* Top teams grid */}
      <div className="mt-6">
        <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
          Top 5 in {REGIONS.find((r) => r.value === region)?.label} · by vlr.gg rating
        </div>
        {topTeams.length === 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-[132px] rounded-2xl" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <AnimatePresence mode="popLayout">
              {topTeams.map((t, i) => {
                const isSelected = selectedTeam?.id === t.id;
                return (
                  <motion.button
                    key={t.id}
                    layout
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.3, delay: i * 0.06 }}
                    onClick={() => setSelectedTeam(t)}
                    className={cn(
                      'relative bg-surface border rounded-2xl p-5 text-left transition-all overflow-hidden group',
                      isSelected
                        ? 'border-accent shadow-lg shadow-accent/10 bg-accent/5'
                        : 'border-border hover:border-border-strong hover:-translate-y-0.5',
                    )}
                  >
                    {isSelected && (
                      <div className="absolute -top-20 -right-20 w-40 h-40 bg-accent/15 rounded-full blur-3xl" />
                    )}
                    <div className="relative">
                      <div className="flex items-center justify-between mb-3">
                        <div className="text-[0.65rem] font-mono uppercase tracking-widest text-ink-dim">
                          #{i + 1}
                        </div>
                        <div className="font-mono text-xs text-ink-soft tabular" title="vlr.gg rating">
                          {t.vlr_rating ?? '—'}
                        </div>
                      </div>
                      <div className="flex items-center gap-3 mb-2">
                        <TeamLogo name={t.name} logoUrl={t.logo_url} size="md" />
                        <div className="min-w-0 flex-1">
                          <div className="font-semibold text-ink text-base truncate flex items-center gap-1.5">
                            {t.name}
                            {countryFlag(t.country) && (
                              <span className="text-sm leading-none">{countryFlag(t.country)}</span>
                            )}
                          </div>
                          <div className="text-xs text-ink-dim font-mono tabular">
                            {t.wins}W – {t.losses}L
                          </div>
                        </div>
                      </div>
                    </div>
                  </motion.button>
                );
              })}
            </AnimatePresence>
          </div>
        )}
      </div>

      {/* Selected team roster */}
      <AnimatePresence>
        {selectedTeam && (
          <motion.div
            key={selectedTeam.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.4 }}
            className="mt-8"
          >
            <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
              {selectedTeam.name} roster
            </div>
            {roster.length === 0 ? (
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="aspect-[4/5] rounded-2xl" />
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {roster.map((p, i) => (
                  <motion.button
                    key={p.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: i * 0.05 }}
                    onClick={() => setPlayerId(p.id)}
                    className={cn(
                      'group relative bg-surface border rounded-2xl overflow-hidden text-left transition-all hover:-translate-y-1',
                      playerId === p.id
                        ? 'border-accent shadow-lg shadow-accent/10'
                        : 'border-border hover:border-border-strong',
                    )}
                  >
                    {/* Photo (or initials fallback) */}
                    <div className="aspect-square relative bg-gradient-to-br from-surface to-bg flex items-center justify-center">
                      {p.image_url ? (
                        <img
                          src={proxyImage(p.image_url)}
                          alt={p.name}
                          className="w-full h-full object-cover"
                          loading="lazy"
                          onError={(e) => {
                            // Hide broken image and show fallback below
                            (e.target as HTMLImageElement).style.display = 'none';
                          }}
                        />
                      ) : null}
                      {!p.image_url && (
                        <PlayerAvatar
                          name={p.name}
                          imageUrl={null}
                          country={null}
                          showFlag={false}
                          size="xl"
                        />
                      )}
                      {/* Country flag overlay */}
                      {countryFlag(p.country) && (
                        <span className="absolute top-2 right-2 text-2xl drop-shadow-lg">
                          {countryFlag(p.country)}
                        </span>
                      )}
                    </div>
                    {/* Name + role */}
                    <div className="p-3 border-t border-border bg-surface group-hover:bg-surface-hover transition-colors">
                      <div className="font-semibold text-ink truncate text-sm">
                        {p.name}
                      </div>
                      <div className="text-[0.65rem] text-ink-dim mt-0.5 truncate">
                        {p.real_name || 'View stats →'}
                      </div>
                    </div>
                  </motion.button>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Or search all players */}
      <div className="mt-16 pt-10 border-t border-border">
        <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
          Or search any player
        </div>
        <div className="max-w-md">
          <Select
            options={playerOptions}
            value={playerId}
            onChange={(v) => setPlayerId(Number(v))}
            placeholder="Pick a player..."
          />
        </div>
      </div>

      {/* Player detail */}
      <div id="player-detail">
        {summary && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mt-10"
          >
            <h2 className="text-3xl font-semibold tracking-tight text-ink mb-6">
              {summary.name}
            </h2>

            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-10">
              <StatTile
                label="Rating"
                value={summary.avg_rating.toFixed(2)}
                sub={`${summary.n_maps.toLocaleString()} maps`}
                index={0}
              />
              <StatTile label="ACS" value={Math.round(summary.avg_acs)} index={1} />
              <StatTile
                label="K/D"
                value={kd}
                sub={`${summary.total_kills} / ${summary.total_deaths}`}
                index={2}
              />
              <StatTile
                label="KAST"
                value={`${Math.round(summary.avg_kast)}%`}
                index={3}
              />
              <StatTile
                label="HS%"
                value={`${Math.round(summary.avg_hs)}%`}
                sub={`ADR ${summary.avg_adr.toFixed(1)}`}
                index={4}
              />
            </div>

            {recentFormChartData.length > 0 && (
              <div className="mb-10">
                <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
                  Recent form · last {recentFormChartData.length} maps
                </div>
                <div className="bg-surface border border-border rounded-2xl p-6">
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={recentFormChartData}>
                      <CartesianGrid stroke="#1F1F24" vertical={false} />
                      <XAxis dataKey="i" hide />
                      <YAxis
                        stroke="#6B6B72"
                        tick={{ fill: '#6B6B72', fontSize: 11 }}
                        domain={[0.5, 'auto']}
                      />
                      <Tooltip
                        contentStyle={{
                          background: '#0F0F12',
                          border: '1px solid #2A2A30',
                          borderRadius: '8px',
                          fontSize: '12px',
                        }}
                        labelStyle={{ color: '#A1A1AA' }}
                      />
                      <Line
                        type="monotone"
                        dataKey="rating"
                        stroke="#FA4454"
                        strokeWidth={2}
                        dot={{ fill: '#FA4454', r: 3 }}
                        activeDot={{ r: 5 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {summary.per_agent.length > 0 && (
              <div className="mb-10">
                <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
                  Agent specialization
                </div>
                <div className="bg-surface border border-border rounded-2xl overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="text-left px-4 py-3 text-[0.7rem] uppercase tracking-widest text-ink-dim font-medium">
                          Agent
                        </th>
                        <th className="text-right px-4 py-3 text-[0.7rem] uppercase tracking-widest text-ink-dim font-medium">
                          Maps
                        </th>
                        <th className="text-right px-4 py-3 text-[0.7rem] uppercase tracking-widest text-ink-dim font-medium">
                          Rating
                        </th>
                        <th className="text-right px-4 py-3 text-[0.7rem] uppercase tracking-widest text-ink-dim font-medium">
                          ACS
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {summary.per_agent.map((a: any) => (
                        <tr key={a.agent} className="border-b border-border last:border-0">
                          <td className="px-4 py-2.5 text-ink capitalize">{a.agent}</td>
                          <td className="px-4 py-2.5 text-right font-mono tabular text-ink-soft">
                            {a.played}
                          </td>
                          <td className="px-4 py-2.5 text-right font-mono tabular text-ink font-semibold">
                            {a.avg_rating}
                          </td>
                          <td className="px-4 py-2.5 text-right font-mono tabular text-ink-soft">
                            {a.avg_acs}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </div>
    </div>
  );
}
