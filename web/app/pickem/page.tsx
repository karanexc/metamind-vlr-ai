'use client';

import { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Trophy, X, Crown } from 'lucide-react';
import {
  api,
  type TeamListItem,
  type EventTeam,
  type PickemForecast,
} from '@/lib/api';
import { Select } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { TeamLogo } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

export default function PickemPage() {
  const [events, setEvents] = useState<{ id: number; name: string }[]>([]);
  const [eventId, setEventId] = useState<number | null>(null);
  const [allTeams, setAllTeams] = useState<TeamListItem[]>([]);
  const [selected, setSelected] = useState<EventTeam[]>([]);
  const [bestOf, setBestOf] = useState<number>(3);
  const [loadingTeams, setLoadingTeams] = useState(false);
  const [loading, setLoading] = useState(false);
  const [forecast, setForecast] = useState<PickemForecast | null>(null);

  useEffect(() => {
    api.events().then(setEvents).catch(console.error);
    api.teams(1).then(setAllTeams).catch(console.error);
  }, []);

  // Auto-fill teams when an event is picked.
  useEffect(() => {
    if (eventId === null) return;
    setLoadingTeams(true);
    setForecast(null);
    api
      .eventTeams(eventId)
      .then((t) => setSelected(t))
      .catch(console.error)
      .finally(() => setLoadingTeams(false));
  }, [eventId]);

  const selectedIds = useMemo(() => new Set(selected.map((s) => s.id)), [selected]);
  const addOptions = allTeams
    .filter((t) => !selectedIds.has(t.id))
    .map((t) => ({ value: t.id, label: t.name, sub: `${t.n_matches} matches` }));

  function addTeam(id: number) {
    if (selectedIds.has(id)) return;
    const t = allTeams.find((x) => x.id === id);
    if (t) setSelected([...selected, { id: t.id, name: t.name }]);
  }
  function removeTeam(id: number) {
    setSelected(selected.filter((s) => s.id !== id));
    setForecast(null);
  }

  async function runForecast() {
    if (selected.length < 2) return;
    setLoading(true);
    setForecast(null);
    try {
      const f = await api.pickemForecast(selected.map((s) => s.id), bestOf);
      setForecast(f);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  const topProb = forecast?.teams?.[0]?.champion_prob || 1;

  return (
    <div className="max-w-5xl mx-auto px-6 lg:px-8 py-16">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-2 text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
          <Trophy className="w-3.5 h-3.5 text-accent" />
          Pick&apos;em
        </div>
        <h1 className="text-display font-semibold tracking-tight text-gradient">
          Forecast the champion.
        </h1>
        <p className="mt-4 text-base text-ink-soft max-w-2xl leading-relaxed">
          Pick a tournament and the model simulates a full round-robin over the field
          thousands of times — using each pair&apos;s real win probability — to estimate
          every team&apos;s chance of finishing top of the table.
        </p>
      </motion.div>

      {/* Controls */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mt-10 bg-surface border border-border rounded-2xl p-6 space-y-4"
      >
        <div className="grid md:grid-cols-[1fr_160px] gap-4">
          <Select
            label="Tournament"
            options={events.map((e) => ({ value: e.id, label: e.name }))}
            value={eventId}
            onChange={(v) => setEventId(Number(v))}
            placeholder={events.length === 0 ? 'Loading events...' : 'Pick a tournament...'}
            disabled={events.length === 0}
          />
          <Select
            label="Format"
            options={[
              { value: 1, label: 'Best of 1' },
              { value: 3, label: 'Best of 3' },
              { value: 5, label: 'Best of 5' },
            ]}
            value={bestOf}
            onChange={(v) => setBestOf(Number(v))}
            searchable={false}
          />
        </div>

        {/* Selected teams */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim">
              Field — {selected.length} teams
            </div>
          </div>

          {loadingTeams ? (
            <div className="flex flex-wrap gap-2">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-9 w-32 rounded-lg" />
              ))}
            </div>
          ) : selected.length === 0 ? (
            <div className="text-sm text-ink-dim py-6 text-center border border-dashed border-border/70 rounded-lg">
              Pick a tournament to auto-fill its teams, or add teams below.
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              <AnimatePresence mode="popLayout">
                {selected.map((t) => (
                  <motion.div
                    key={t.id}
                    layout
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    className="group flex items-center gap-2 pl-2 pr-1 py-1 bg-bg border border-border rounded-lg"
                  >
                    <TeamLogo name={t.name} size="sm" />
                    <span className="text-sm text-ink font-medium">{t.name}</span>
                    <button
                      onClick={() => removeTeam(t.id)}
                      className="text-ink-dim hover:text-accent transition-colors p-1"
                      aria-label={`Remove ${t.name}`}
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}

          {/* Add team */}
          <div className="mt-3 max-w-xs">
            <Select
              options={addOptions}
              value={null}
              onChange={(v) => addTeam(Number(v))}
              placeholder="Add a team..."
              disabled={allTeams.length === 0}
            />
          </div>
        </div>

        <Button
          variant="primary"
          size="lg"
          onClick={runForecast}
          disabled={selected.length < 2 || loading}
          loading={loading}
          className="w-full sm:w-auto"
        >
          {loading ? 'Simulating tournament...' : 'Forecast the winner'}
        </Button>
      </motion.div>

      {/* Results */}
      <AnimatePresence mode="wait">
        {forecast && (
          <motion.div
            key="forecast"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
            className="mt-10"
          >
            <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-4">
              Championship odds · {forecast.n_teams} teams · Bo{forecast.best_of} ·{' '}
              {forecast.n_sims.toLocaleString()} sims
            </div>

            {forecast.teams.length === 0 ? (
              <div className="bg-surface border border-border rounded-2xl p-8 text-center text-sm text-ink-dim">
                {forecast.note}
              </div>
            ) : (
              <div className="space-y-2">
                {forecast.teams.map((t, i) => (
                  <motion.div
                    key={t.team_id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.4, delay: i * 0.04 }}
                    className={cn(
                      'relative bg-surface border rounded-xl overflow-hidden',
                      i === 0 ? 'border-accent/50' : 'border-border',
                    )}
                  >
                    {/* Probability fill bar */}
                    <div
                      className={cn(
                        'absolute inset-y-0 left-0',
                        i === 0 ? 'bg-accent/10' : 'bg-surface-hover/60',
                      )}
                      style={{ width: `${(t.champion_prob / topProb) * 100}%` }}
                    />
                    <div className="relative flex items-center gap-4 px-4 py-3">
                      <div className="w-6 flex justify-center">
                        {i === 0 ? (
                          <Crown className="w-5 h-5 text-accent" />
                        ) : (
                          <span className="text-sm font-mono text-ink-dim tabular">{i + 1}</span>
                        )}
                      </div>
                      <TeamLogo name={t.team_name} size="md" />
                      <div className="min-w-0 flex-1">
                        <div className="font-semibold text-ink truncate">{t.team_name}</div>
                        <div className="text-[0.7rem] text-ink-dim">
                          {t.expected_wins} exp. wins · {Math.round(t.avg_win_prob * 100)}% avg vs field
                        </div>
                      </div>
                      <div
                        className={cn(
                          'font-mono font-semibold tabular text-2xl',
                          i === 0 ? 'text-ink' : 'text-ink-soft',
                        )}
                      >
                        {(t.champion_prob * 100).toFixed(1)}%
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}

            {forecast.unavailable.length > 0 && (
              <div className="mt-4 text-xs text-ink-dim">
                Excluded (no recent lineup data): {forecast.unavailable.join(', ')}
              </div>
            )}
            <div className="mt-3 text-xs text-ink-dim">{forecast.note}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
