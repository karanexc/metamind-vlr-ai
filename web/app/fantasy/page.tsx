'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Crosshair, Zap, Cloud, Shield, Shuffle, Swords, Trophy, Users } from 'lucide-react';
import {
  api,
  type PlayerListItem,
  type TeamListItem,
  type TeamRosterPlayer,
  type MatchPrediction,
} from '@/lib/api';
import { Select } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { ProbBar } from '@/components/ui/prob-bar';
import { Counter } from '@/components/ui/counter';
import { PlayerAvatar, TeamLogo } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
import { getAgents, type ValAgent } from '@/lib/valorant';
import { cn, countryFlag } from '@/lib/utils';

// Valorant role archetypes — flavor for the 5 roster slots.
const ROLES = [
  { name: 'Duelist', hint: 'Entry / fragger', icon: Crosshair },
  { name: 'Initiator', hint: 'Info / setup', icon: Zap },
  { name: 'Controller', hint: 'Smokes / space', icon: Cloud },
  { name: 'Sentinel', hint: 'Anchor / lockdown', icon: Shield },
  { name: 'Flex', hint: 'Fill / swing', icon: Shuffle },
];

type Mode = 'custom' | 'challenge';

export default function FantasyPage() {
  const [mode, setMode] = useState<Mode>('custom');

  const [players, setPlayers] = useState<PlayerListItem[]>([]);
  const [teamA, setTeamA] = useState<string[]>([]);
  const [teamB, setTeamB] = useState<string[]>([]);
  const [bestOf, setBestOf] = useState<number>(3);
  const [prediction, setPrediction] = useState<MatchPrediction | null>(null);
  const [loading, setLoading] = useState(false);

  // Challenge mode: pick a real team as the opponent (side A).
  const [teams, setTeams] = useState<TeamListItem[]>([]);
  const [challengeTeamId, setChallengeTeamId] = useState<number | null>(null);
  const [challengeRoster, setChallengeRoster] = useState<TeamRosterPlayer[]>([]);
  const [rosterLoading, setRosterLoading] = useState(false);

  const [agents, setAgents] = useState<ValAgent[]>([]);

  useEffect(() => {
    api.players(20).then(setPlayers).catch(console.error);
    getAgents().then(setAgents).catch(() => {});
  }, []);

  // One representative agent icon per role archetype (for empty-slot flavor).
  const roleIcon: Record<string, string> = {};
  for (const role of ['Duelist', 'Initiator', 'Controller', 'Sentinel']) {
    const match = agents.find((a) => a.role === role && a.icon);
    if (match) roleIcon[role] = match.icon;
  }

  useEffect(() => {
    if (mode === 'challenge' && teams.length === 0) {
      api.teams(20).then(setTeams).catch(console.error);
    }
  }, [mode, teams.length]);

  useEffect(() => {
    if (challengeTeamId === null) {
      setChallengeRoster([]);
      return;
    }
    setRosterLoading(true);
    setPrediction(null);
    api
      .teamRoster(challengeTeamId)
      .then((r) => setChallengeRoster(r.slice(0, 5)))
      .catch(console.error)
      .finally(() => setRosterLoading(false));
  }, [challengeTeamId]);

  const challengeTeam = teams.find((t) => t.id === challengeTeamId) || null;
  const challengeNames = challengeRoster.map((p) => p.name);

  // Side A's player names depend on the mode.
  const teamAPlayers = mode === 'challenge' ? challengeNames : teamA;
  const ready = teamAPlayers.length === 5 && teamB.length === 5;

  function addToTeam(
    team: string[],
    setTeam: (v: string[]) => void,
    otherUsed: string[],
    name: string,
  ) {
    if (team.includes(name) || otherUsed.includes(name) || team.length >= 5) return;
    setTeam([...team, name]);
  }

  async function simulate() {
    if (!ready) return;
    setLoading(true);
    setPrediction(null);
    try {
      const r = await api.predictFantasy(teamAPlayers, teamB, bestOf);
      setPrediction(r);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  const usedElsewhere = mode === 'challenge' ? challengeNames : teamA;
  const playerOptions = players
    .filter((p) => !teamB.includes(p.name) && !usedElsewhere.includes(p.name))
    .map((p) => ({ value: p.name, label: p.name, sub: `${p.n_maps} maps` }));

  const teamOptions = teams.map((t) => ({
    value: t.id,
    label: t.name,
    sub: `${t.n_matches} matches`,
  }));

  // --- A manual 5-slot draft panel ----------------------------------------
  function draftPanel(opts: {
    team: string[];
    setTeam: (v: string[]) => void;
    otherUsed: string[];
    accent: boolean;
    title: string;
  }) {
    const { team, setTeam, otherUsed, accent, title } = opts;
    return (
      <div className="relative bg-surface border border-border rounded-2xl p-5 overflow-hidden">
        <div
          className={cn(
            'absolute -top-16 w-40 h-40 rounded-full blur-3xl',
            accent ? '-left-10 bg-accent/10' : '-right-10 bg-[#22D3EE]/10',
          )}
        />
        <div className="relative">
          <div className="flex items-center justify-between mb-3">
            <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim">
              {title}
            </div>
            <div className="flex items-center gap-1.5">
              {Array.from({ length: 5 }).map((_, i) => (
                <span
                  key={i}
                  className={cn(
                    'w-4 h-1 rounded-full transition-colors',
                    i < team.length ? (accent ? 'bg-accent' : 'bg-[#22D3EE]') : 'bg-border',
                  )}
                />
              ))}
            </div>
          </div>

          <Select
            options={playerOptions}
            value={null}
            onChange={(v) => addToTeam(team, setTeam, otherUsed, String(v))}
            placeholder={team.length >= 5 ? 'Full roster ✓' : 'Draft a player...'}
            disabled={team.length >= 5}
          />

          <div className="mt-4 space-y-2">
            {ROLES.map((role, i) => {
              const name = team[i];
              return (
                <div key={role.name}>
                  <AnimatePresence mode="wait">
                    {name ? (
                      <motion.div
                        key={`filled-${name}`}
                        layout
                        initial={{ opacity: 0, scale: 0.94 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.94 }}
                        transition={{ type: 'spring', stiffness: 400, damping: 28 }}
                        className="group flex items-center gap-3 px-3 py-2.5 bg-bg border border-border rounded-lg hover:border-border-strong transition-colors"
                      >
                        <div
                          className={cn(
                            'w-8 h-8 rounded-md flex items-center justify-center flex-shrink-0',
                            accent ? 'bg-accent/10 text-accent' : 'bg-[#22D3EE]/10 text-[#22D3EE]',
                          )}
                        >
                          <role.icon className="w-4 h-4" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="text-sm font-semibold text-ink truncate">{name}</div>
                          <div className="text-[0.65rem] uppercase tracking-widest text-ink-dim">
                            {role.name}
                          </div>
                        </div>
                        <button
                          onClick={() => setTeam(team.filter((p) => p !== name))}
                          className="text-ink-dim hover:text-accent transition-colors opacity-0 group-hover:opacity-100"
                          aria-label={`Remove ${name}`}
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </motion.div>
                    ) : (
                      <motion.div
                        key="empty"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="flex items-center gap-3 px-3 py-2.5 border border-dashed border-border/70 rounded-lg"
                      >
                        <div className="w-8 h-8 rounded-md bg-surface flex items-center justify-center flex-shrink-0 overflow-hidden">
                          {roleIcon[role.name] ? (
                            <img
                              src={roleIcon[role.name]}
                              alt={role.name}
                              loading="lazy"
                              className="w-5 h-5 object-contain opacity-70"
                            />
                          ) : (
                            <role.icon className="w-4 h-4 text-ink-dim" />
                          )}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="text-sm font-medium text-ink-dim">{role.name}</div>
                          <div className="text-[0.65rem] text-ink-dim/70">{role.hint}</div>
                        </div>
                        <span className="text-[0.65rem] uppercase tracking-widest text-ink-dim/60">
                          Empty
                        </span>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  // --- The real-team opponent panel (challenge mode) ----------------------
  function challengePanel() {
    return (
      <div className="relative bg-surface border border-border rounded-2xl p-5 overflow-hidden">
        <div className="absolute -top-16 -left-10 w-40 h-40 rounded-full blur-3xl bg-accent/10" />
        <div className="relative">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-1.5 text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim">
              <Trophy className="w-3.5 h-3.5 text-accent" />
              Opponent — real team
            </div>
            {challengeTeam && (
              <span className="text-[0.65rem] font-mono text-ink-dim tabular">
                {challengeRoster.length}/5
              </span>
            )}
          </div>

          <Select
            options={teamOptions}
            value={challengeTeamId}
            onChange={(v) => setChallengeTeamId(Number(v))}
            placeholder={teams.length === 0 ? 'Loading teams...' : 'Pick a team to beat...'}
            disabled={teams.length === 0}
          />

          {challengeTeam && (
            <div className="mt-4 flex items-center gap-3 px-3 py-2.5 bg-accent/5 border border-accent/20 rounded-lg">
              <TeamLogo name={challengeTeam.name} size="md" />
              <div className="min-w-0">
                <div className="text-sm font-semibold text-ink truncate">{challengeTeam.name}</div>
                <div className="text-[0.65rem] uppercase tracking-widest text-ink-dim">
                  Full lineup
                </div>
              </div>
            </div>
          )}

          <div className="mt-4 space-y-2">
            {rosterLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-[52px] rounded-lg" />
              ))
            ) : challengeRoster.length > 0 ? (
              challengeRoster.map((p, i) => (
                <motion.div
                  key={p.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: i * 0.05 }}
                  className="flex items-center gap-3 px-3 py-2.5 bg-bg border border-border rounded-lg"
                >
                  <PlayerAvatar name={p.name} imageUrl={p.image_url} country={p.country} size="sm" />
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-semibold text-ink truncate flex items-center gap-1.5">
                      {p.name}
                      {countryFlag(p.country) && (
                        <span className="text-xs leading-none">{countryFlag(p.country)}</span>
                      )}
                    </div>
                    {p.real_name && (
                      <div className="text-[0.65rem] text-ink-dim truncate">{p.real_name}</div>
                    )}
                  </div>
                  <span className="text-[0.6rem] uppercase tracking-widest text-accent/70 font-medium">
                    Locked
                  </span>
                </motion.div>
              ))
            ) : (
              <div className="flex flex-col items-center justify-center gap-2 py-10 text-center border border-dashed border-border/70 rounded-lg">
                <Users className="w-5 h-5 text-ink-dim" />
                <div className="text-sm text-ink-dim">Pick a team to load its lineup.</div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  const nameA = mode === 'challenge' ? challengeTeam?.name || 'Opponent' : 'Team A';
  const nameB = mode === 'challenge' ? 'Your roster' : 'Team B';
  const favored = prediction ? (prediction.prob_a >= prediction.prob_b ? nameA : nameB) : '';
  const draftedCount = teamAPlayers.length + teamB.length;

  return (
    <div className="max-w-6xl mx-auto px-6 lg:px-8 py-16">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-2 text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
          <Swords className="w-3.5 h-3.5 text-accent" />
          Fantasy
        </div>
        <h1 className="text-display font-semibold tracking-tight text-gradient">
          Build your roster.
        </h1>
        <p className="mt-4 text-base text-ink-soft max-w-2xl leading-relaxed">
          Draft five players and see how they stack up — against another custom roster, or
          against a real Tier 1 team&apos;s full lineup. The model scores both sides on their
          real performance data.
        </p>
      </motion.div>

      {/* Mode toggle */}
      <div className="mt-8 inline-flex gap-1 p-1 bg-surface border border-border rounded-xl">
        {[
          { id: 'custom' as Mode, label: 'Custom vs Custom', icon: Users },
          { id: 'challenge' as Mode, label: 'Challenge a team', icon: Trophy },
        ].map((m) => (
          <button
            key={m.id}
            onClick={() => {
              setMode(m.id);
              setPrediction(null);
            }}
            className={cn(
              'flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all',
              mode === m.id
                ? 'bg-accent text-white shadow-lg shadow-accent/20'
                : 'text-ink-soft hover:text-ink hover:bg-surface-hover',
            )}
          >
            <m.icon className="w-4 h-4" />
            {m.label}
          </button>
        ))}
      </div>

      {/* Draft board: Side A · VS · Side B */}
      <div className="mt-6 grid md:grid-cols-[1fr_auto_1fr] gap-4 md:gap-3 items-start">
        {mode === 'challenge'
          ? challengePanel()
          : draftPanel({ team: teamA, setTeam: setTeamA, otherUsed: teamB, accent: true, title: 'Team A' })}

        {/* Animated VS core */}
        <div className="hidden md:flex flex-col items-center justify-center pt-24">
          <motion.div
            className="relative w-14 h-14 rounded-full bg-surface border border-border flex items-center justify-center"
            animate={{
              boxShadow: ready
                ? ['0 0 0 0 rgba(250,68,84,0.0)', '0 0 0 8px rgba(250,68,84,0.08)', '0 0 0 0 rgba(250,68,84,0.0)']
                : '0 0 0 0 rgba(250,68,84,0)',
            }}
            transition={{ duration: 1.8, repeat: ready ? Infinity : 0, ease: 'easeInOut' }}
          >
            <span className="font-mono font-semibold text-sm tracking-widest text-ink-soft">VS</span>
          </motion.div>
          <div className="mt-3 h-24 w-px bg-gradient-to-b from-border to-transparent" />
        </div>

        {draftPanel({
          team: teamB,
          setTeam: setTeamB,
          otherUsed: usedElsewhere,
          accent: false,
          title: mode === 'challenge' ? 'Your roster' : 'Team B',
        })}
      </div>

      {/* Controls */}
      <div className="mt-6 flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
        <Select
          options={[
            { value: 1, label: 'Bo1' },
            { value: 3, label: 'Bo3' },
            { value: 5, label: 'Bo5' },
          ]}
          value={bestOf}
          onChange={(v) => setBestOf(Number(v))}
          searchable={false}
        />
        <Button
          variant="primary"
          size="lg"
          onClick={simulate}
          disabled={!ready || loading}
          loading={loading}
          className="flex-1 sm:max-w-[280px]"
        >
          {loading
            ? 'Simulating...'
            : ready
              ? mode === 'challenge'
                ? `Can you beat ${nameA}?`
                : 'Simulate matchup'
              : `Draft ${Math.max(0, 10 - draftedCount)} more`}
        </Button>
      </div>

      <AnimatePresence>
        {prediction && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.6 }}
            className="mt-10 bg-gradient-card border border-border rounded-3xl p-8 relative overflow-hidden"
          >
            <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-96 h-96 bg-accent/15 rounded-full blur-[100px]" />
            <div className="relative">
              <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-4 text-center">
                Simulated outcome
              </div>

              {/* Matchup labels */}
              <div className="flex items-center justify-between text-sm font-semibold mb-2">
                <span className={prediction.prob_a >= prediction.prob_b ? 'text-ink' : 'text-ink-dim'}>
                  {nameA}
                </span>
                <span className={prediction.prob_b > prediction.prob_a ? 'text-ink' : 'text-ink-dim'}>
                  {nameB}
                </span>
              </div>

              <div className="flex items-center gap-6">
                <div className={cn(
                  'font-mono font-semibold tabular text-5xl tracking-tight',
                  prediction.prob_a >= 0.5 ? 'text-ink' : 'text-ink-dim',
                )}>
                  <Counter value={prediction.prob_a * 100} format={(n) => `${Math.round(n)}%`} />
                </div>
                <div className="flex-1">
                  <ProbBar probA={prediction.prob_a} delay={0.3} />
                </div>
                <div className={cn(
                  'font-mono font-semibold tabular text-5xl tracking-tight text-right',
                  prediction.prob_b > prediction.prob_a ? 'text-ink' : 'text-ink-dim',
                )}>
                  <Counter value={prediction.prob_b * 100} format={(n) => `${Math.round(n)}%`} />
                </div>
              </div>

              <div className="mt-6 text-center text-sm text-ink-soft">
                <span className="text-ink font-semibold">{favored}</span> favoured
                <span className="mx-3 text-ink-dim">·</span>
                Projected:{' '}
                <span className="font-mono font-semibold text-ink">
                  {prediction.predicted_score_a}–{prediction.predicted_score_b}
                </span>
                <span className="mx-3 text-ink-dim">·</span>
                Confidence: <span className="text-ink capitalize">{prediction.confidence}</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
