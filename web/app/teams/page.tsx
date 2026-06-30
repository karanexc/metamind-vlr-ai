'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { api, type TeamListItem, type TeamSummary } from '@/lib/api';
import { Select } from '@/components/ui/select';
import { StatTile } from '@/components/ui/stat-tile';
import { formatDate, cn } from '@/lib/utils';

export default function TeamsPage() {
  const [teams, setTeams] = useState<TeamListItem[]>([]);
  const [teamId, setTeamId] = useState<number | null>(null);
  const [summary, setSummary] = useState<TeamSummary | null>(null);

  useEffect(() => {
    api.teams(5).then(setTeams).catch(console.error);
  }, []);

  useEffect(() => {
    if (teamId !== null) {
      setSummary(null);
      api.team(teamId).then(setSummary).catch(console.error);
    }
  }, [teamId]);

  const teamOptions = teams.map((t) => ({
    value: t.id,
    label: t.name,
    sub: `${t.n_matches} matches`,
  }));

  return (
    <div className="max-w-7xl mx-auto px-6 lg:px-8 py-16">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
          Teams
        </div>
        <h1 className="text-display font-semibold tracking-tight text-gradient">
          Team explorer
        </h1>
        <p className="mt-4 text-base text-ink-soft max-w-2xl">
          Recent matches, current roster, and per-map win rates for any team.
        </p>
      </motion.div>

      <div className="mt-10 max-w-md">
        <Select
          options={teamOptions}
          value={teamId}
          onChange={(v) => setTeamId(Number(v))}
          placeholder="Pick a team..."
        />
      </div>

      {summary && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mt-10"
        >
          <h2 className="text-3xl font-semibold tracking-tight text-ink mb-6">{summary.name}</h2>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
            <StatTile
              label="Matches"
              value={summary.n_matches}
              sub={`${summary.n_wins} wins`}
              index={0}
            />
            <StatTile
              label="Match win rate"
              value={`${summary.match_win_rate}%`}
              sub="all events"
              index={1}
            />
            <StatTile
              label="Maps"
              value={summary.map_total}
              sub={`${summary.map_wins} wins`}
              index={2}
            />
            <StatTile
              label="Map win rate"
              value={`${summary.map_win_rate}%`}
              index={3}
            />
          </div>

          {/* Roster */}
          {summary.roster.length > 0 && (
            <div className="mb-10">
              <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
                Current roster
              </div>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {summary.roster.slice(0, 5).map((p, i) => (
                  <motion.div
                    key={p.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.06 }}
                    className="bg-surface border border-border rounded-xl p-4 text-center hover:border-border-strong transition-colors"
                  >
                    <div className="text-[0.65rem] uppercase tracking-widest text-ink-dim mb-1">
                      Player
                    </div>
                    <div className="font-semibold text-ink">{p.name}</div>
                  </motion.div>
                ))}
              </div>
            </div>
          )}

          {/* Per map */}
          {summary.per_map.length > 0 && (
            <div className="mb-10">
              <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
                Map performance
              </div>
              <div className="bg-surface border border-border rounded-2xl p-5 space-y-3">
                {summary.per_map.map((m) => (
                  <div key={m.map} className="flex items-center gap-4">
                    <div className="w-20 text-sm font-medium text-ink">{m.map}</div>
                    <div className="flex-1 h-2 bg-bg rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-accent rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${m.win_rate}%` }}
                        transition={{ duration: 0.8 }}
                      />
                    </div>
                    <div className="text-sm font-mono tabular w-16 text-right text-ink">
                      {m.win_rate}%
                    </div>
                    <div className="text-xs font-mono tabular w-16 text-right text-ink-dim">
                      {m.played} plays
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recent matches */}
          {summary.recent_matches.length > 0 && (
            <div>
              <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
                Recent matches
              </div>
              <div className="space-y-2">
                {summary.recent_matches.map((m: any) => {
                  const isTeamA = m.team_a === summary.name;
                  const own = isTeamA ? m.score_a : m.score_b;
                  const opp = isTeamA ? m.score_b : m.score_a;
                  const oppName = isTeamA ? m.team_b : m.team_a;
                  const won = own > opp;
                  return (
                    <div
                      key={m.match_id}
                      className="flex items-center gap-4 px-4 py-3 bg-surface border border-border rounded-xl"
                    >
                      <div className={cn(
                        'w-8 h-8 rounded-md flex items-center justify-center text-xs font-mono font-bold text-white',
                        won ? 'bg-success' : 'bg-accent',
                      )}>
                        {won ? 'W' : 'L'}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-[0.65rem] uppercase tracking-widest text-ink-dim mb-0.5">
                          {m.event || '—'} · {formatDate(m.datetime)}
                          {m.best_of && ` · Bo${m.best_of}`}
                        </div>
                        <div className="text-sm text-ink">
                          vs <span className="font-medium">{oppName}</span>{' '}
                          <span className="font-mono font-semibold ml-2 tabular">
                            {own}–{opp}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}
