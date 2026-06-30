'use client';

import { useEffect, useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { ChevronRight, Search } from 'lucide-react';
import { api, type LeaderboardTeam } from '@/lib/api';
import { PlayerAvatar, TeamLogo } from '@/components/ui/avatar';
import { cn, countryFlag } from '@/lib/utils';

type RegionFilter = 'all' | 'americas' | 'emea' | 'pacific' | 'china';

const REGIONS: { value: RegionFilter; label: string }[] = [
  { value: 'all', label: 'All Regions' },
  { value: 'americas', label: 'Americas' },
  { value: 'emea', label: 'EMEA' },
  { value: 'pacific', label: 'Pacific' },
  { value: 'china', label: 'China' },
];

export default function TeamsPage() {
  const [region, setRegion] = useState<RegionFilter>('all');
  const [teams, setTeams] = useState<LeaderboardTeam[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [expanded, setExpanded] = useState<number | null>(null);

  useEffect(() => {
    setLoading(true);
    setTeams([]);
    api
      .teamsLeaderboard(region, 50)
      .then((data) => setTeams(data))
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, [region]);

  const filteredTeams = useMemo(() => {
    if (!search.trim()) return teams;
    const q = search.trim().toLowerCase();
    return teams.filter(
      (t) =>
        t.name.toLowerCase().includes(q) ||
        t.roster.some((p) => p.name.toLowerCase().includes(q)),
    );
  }, [teams, search]);

  return (
    <div className="max-w-7xl mx-auto px-6 lg:px-8 py-16">
      {/* Hero */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
          Team rankings
        </div>
        <h1 className="text-display font-semibold tracking-tight text-gradient">
          Valorant world rankings.
        </h1>
        <p className="mt-4 text-base text-ink-soft max-w-2xl">
          Teams ranked by match win rate over the last 180 days. Minimum 5
          decided matches required to appear on the leaderboard.
        </p>
      </motion.div>

      {/* Region tabs + search */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.15 }}
        className="mt-10 flex flex-wrap items-center justify-between gap-4"
      >
        <div className="flex gap-1 p-1 bg-surface border border-border rounded-xl w-fit">
          {REGIONS.map((r) => (
            <button
              key={r.value}
              onClick={() => setRegion(r.value)}
              className={cn(
                'px-4 py-1.5 text-sm font-medium rounded-lg transition-all',
                region === r.value
                  ? 'bg-accent text-white shadow-lg shadow-accent/20'
                  : 'text-ink-soft hover:text-ink hover:bg-surface-hover',
              )}
            >
              {r.label}
            </button>
          ))}
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-dim" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search teams or players..."
            className="pl-9 pr-4 py-2 bg-surface border border-border rounded-lg text-sm text-ink placeholder:text-ink-dim focus:outline-none focus:border-border-strong w-72"
          />
        </div>
      </motion.div>

      {/* Leaderboard table */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25 }}
        className="mt-8 bg-surface border border-border rounded-2xl overflow-hidden"
      >
        {/* Header row */}
        <div className="hidden md:grid grid-cols-[60px_1fr_120px_140px_minmax(280px,1fr)_40px] gap-4 px-6 py-3 border-b border-border bg-bg/40">
          <div className="text-[0.65rem] font-medium uppercase tracking-widest text-ink-dim">
            Rank
          </div>
          <div className="text-[0.65rem] font-medium uppercase tracking-widest text-ink-dim">
            Team
          </div>
          <div className="text-[0.65rem] font-medium uppercase tracking-widest text-ink-dim">
            Region
          </div>
          <div className="text-[0.65rem] font-medium uppercase tracking-widest text-ink-dim">
            Record
          </div>
          <div className="text-[0.65rem] font-medium uppercase tracking-widest text-ink-dim">
            Roster
          </div>
          <div />
        </div>

        {/* Empty/loading */}
        {loading && (
          <div className="px-6 py-16 text-center text-sm text-ink-dim">
            <div className="inline-flex items-center gap-2">
              <span className="relative flex w-2 h-2">
                <span className="absolute inline-flex w-full h-full rounded-full bg-accent opacity-75 animate-ping" />
                <span className="relative inline-flex w-2 h-2 rounded-full bg-accent" />
              </span>
              Loading leaderboard...
            </div>
          </div>
        )}

        {!loading && filteredTeams.length === 0 && (
          <div className="px-6 py-16 text-center text-sm text-ink-dim">
            No teams match your search.
          </div>
        )}

        {/* Rows */}
        {!loading &&
          filteredTeams.map((team, idx) => {
            const isExpanded = expanded === team.id;
            return (
              <motion.div
                key={team.id}
                layout
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: Math.min(idx * 0.02, 0.5) }}
                className={cn(
                  'border-b border-border last:border-0 transition-colors',
                  isExpanded ? 'bg-bg/30' : 'hover:bg-bg/20',
                )}
              >
                {/* Main row */}
                <button
                  onClick={() => setExpanded(isExpanded ? null : team.id)}
                  className="w-full grid grid-cols-[60px_1fr] md:grid-cols-[60px_1fr_120px_140px_minmax(280px,1fr)_40px] gap-4 px-6 py-4 text-left items-center"
                >
                  {/* Rank */}
                  <div className="flex items-center gap-1.5">
                    {idx < 3 ? (
                      <div
                        className={cn(
                          'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold',
                          idx === 0 && 'bg-gradient-to-br from-yellow-400 to-amber-600 text-white',
                          idx === 1 && 'bg-gradient-to-br from-zinc-300 to-zinc-500 text-zinc-900',
                          idx === 2 && 'bg-gradient-to-br from-orange-400 to-orange-700 text-white',
                        )}
                      >
                        {idx + 1}
                      </div>
                    ) : (
                      <div className="w-7 h-7 flex items-center justify-center text-sm font-mono text-ink-dim tabular">
                        {idx + 1}
                      </div>
                    )}
                  </div>

                  {/* Team logo + name */}
                  <div className="flex items-center gap-3 min-w-0">
                    <TeamLogo name={team.name} logoUrl={team.logo_url} size="md" />
                    <div className="min-w-0">
                      <div className="font-semibold text-ink truncate flex items-center gap-1.5">
                        {team.name}
                        {countryFlag(team.country) && (
                          <span className="text-sm leading-none flex-shrink-0">
                            {countryFlag(team.country)}
                          </span>
                        )}
                      </div>
                      <div className="text-[0.7rem] text-ink-dim md:hidden mt-0.5">
                        {team.region || '—'} · {team.wins}W-{team.losses}L
                      </div>
                    </div>
                  </div>

                  {/* Region (md+) */}
                  <div className="hidden md:block text-sm text-ink-soft capitalize">
                    {team.region || '—'}
                  </div>

                  {/* Record + win% (md+) */}
                  <div className="hidden md:flex items-baseline gap-2">
                    <div className="font-mono font-semibold text-ink tabular">
                      {team.win_pct.toFixed(0)}%
                    </div>
                    <div className="text-xs text-ink-dim font-mono tabular">
                      {team.wins}–{team.losses}
                    </div>
                  </div>

                  {/* Roster row (md+) */}
                  <div className="hidden md:flex items-center gap-2">
                    {team.roster.length === 0 ? (
                      <span className="text-xs text-ink-dim">—</span>
                    ) : (
                      team.roster.slice(0, 5).map((p) => (
                        <div
                          key={p.id}
                          className="group/p relative"
                          title={p.name}
                        >
                          <PlayerAvatar
                            name={p.name}
                            imageUrl={p.image_url}
                            country={p.country}
                            size="md"
                          />
                          {/* Hover label */}
                          <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-bg border border-border-strong rounded-md px-2 py-1 text-[0.7rem] text-ink opacity-0 group-hover/p:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                            {p.name}
                          </div>
                        </div>
                      ))
                    )}
                  </div>

                  {/* Expand arrow (md+) */}
                  <div className="hidden md:flex justify-end">
                    <ChevronRight
                      className={cn(
                        'w-4 h-4 text-ink-dim transition-transform',
                        isExpanded && 'rotate-90',
                      )}
                    />
                  </div>
                </button>

                {/* Expanded details */}
                {isExpanded && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="px-6 pb-5 pt-2 border-t border-border bg-bg/20">
                      <div className="grid md:grid-cols-2 gap-6">
                        <div>
                          <div className="text-[0.65rem] uppercase tracking-widest text-ink-dim mb-2">
                            Full roster
                          </div>
                          <div className="space-y-2">
                            {team.roster.map((p) => (
                              <a
                                key={p.id}
                                href={`/players?id=${p.id}`}
                                className="flex items-center gap-3 p-2 rounded-lg hover:bg-surface-hover transition-colors"
                              >
                                <PlayerAvatar
                                  name={p.name}
                                  imageUrl={p.image_url}
                                  country={p.country}
                                  size="md"
                                />
                                <div className="min-w-0 flex-1">
                                  <div className="font-semibold text-ink truncate">
                                    {p.name}
                                  </div>
                                </div>
                              </a>
                            ))}
                          </div>
                        </div>
                        <div>
                          <div className="text-[0.65rem] uppercase tracking-widest text-ink-dim mb-2">
                            Form (last 180 days)
                          </div>
                          <div className="grid grid-cols-2 gap-3">
                            <div className="bg-surface border border-border rounded-lg p-3">
                              <div className="text-[0.65rem] uppercase tracking-widest text-ink-dim mb-1">
                                Matches
                              </div>
                              <div className="font-mono text-xl font-semibold text-ink tabular">
                                {team.matches_played}
                              </div>
                            </div>
                            <div className="bg-surface border border-border rounded-lg p-3">
                              <div className="text-[0.65rem] uppercase tracking-widest text-ink-dim mb-1">
                                Win rate
                              </div>
                              <div className="font-mono text-xl font-semibold text-accent tabular">
                                {team.win_pct.toFixed(1)}%
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}
              </motion.div>
            );
          })}
      </motion.div>

      {/* Footer note */}
      <div className="mt-6 text-xs text-ink-dim text-center">
        Rankings calculated from {teams.length} teams. Updated continuously as new
        matches are scraped.
      </div>
    </div>
  );
}
