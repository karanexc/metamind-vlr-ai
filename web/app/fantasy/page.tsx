'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { api, type PlayerListItem, type MatchPrediction } from '@/lib/api';
import { Select } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { ProbBar } from '@/components/ui/prob-bar';
import { Counter } from '@/components/ui/counter';
import { cn } from '@/lib/utils';

export default function FantasyPage() {
  const [players, setPlayers] = useState<PlayerListItem[]>([]);
  const [teamA, setTeamA] = useState<string[]>([]);
  const [teamB, setTeamB] = useState<string[]>([]);
  const [bestOf, setBestOf] = useState<number>(3);
  const [prediction, setPrediction] = useState<MatchPrediction | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.players(20).then(setPlayers).catch(console.error);
  }, []);

  function addToA(name: string) {
    if (teamA.includes(name) || teamA.length >= 5) return;
    setTeamA([...teamA, name]);
  }
  function addToB(name: string) {
    if (teamB.includes(name) || teamB.length >= 5) return;
    setTeamB([...teamB, name]);
  }

  async function simulate() {
    if (teamA.length !== 5 || teamB.length !== 5) return;
    setLoading(true);
    setPrediction(null);
    try {
      const r = await api.predictFantasy(teamA, teamB, bestOf);
      setPrediction(r);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  const playerOptions = players
    .filter((p) => !teamA.includes(p.name) && !teamB.includes(p.name))
    .map((p) => ({ value: p.name, label: p.name, sub: `${p.n_maps} maps` }));

  return (
    <div className="max-w-6xl mx-auto px-6 lg:px-8 py-16">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
          Fantasy
        </div>
        <h1 className="text-display font-semibold tracking-tight text-gradient">
          Build your roster.
        </h1>
        <p className="mt-4 text-base text-ink-soft max-w-2xl leading-relaxed">
          Mix and match any 5 players from anywhere in the database. The model evaluates
          them against another custom roster using their real performance data.
        </p>
      </motion.div>

      <div className="mt-10 grid md:grid-cols-2 gap-6">
        {(['A', 'B'] as const).map((side) => {
          const team = side === 'A' ? teamA : teamB;
          const setTeam = side === 'A' ? setTeamA : setTeamB;
          const add = side === 'A' ? addToA : addToB;
          return (
            <div key={side} className="bg-surface border border-border rounded-2xl p-5">
              <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
                Team {side} — {team.length}/5 players
              </div>
              <Select
                options={playerOptions}
                value={null}
                onChange={(v) => add(String(v))}
                placeholder={team.length >= 5 ? 'Full roster' : 'Add a player...'}
                disabled={team.length >= 5}
              />
              <div className="mt-4 space-y-2 min-h-[280px]">
                <AnimatePresence>
                  {team.map((name, i) => (
                    <motion.div
                      key={name}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 10 }}
                      className="flex items-center justify-between px-3 py-2 bg-bg border border-border rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-mono text-ink-dim w-4 tabular">
                          {i + 1}
                        </span>
                        <span className="text-sm font-medium text-ink">{name}</span>
                      </div>
                      <button
                        onClick={() => setTeam(team.filter((p) => p !== name))}
                        className="text-ink-dim hover:text-accent transition-colors"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </motion.div>
                  ))}
                </AnimatePresence>
                {team.length === 0 && (
                  <div className="h-[280px] flex items-center justify-center text-sm text-ink-dim">
                    Empty roster
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-6 flex items-center gap-4">
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
          disabled={teamA.length !== 5 || teamB.length !== 5 || loading}
          loading={loading}
          className="flex-1 max-w-[240px]"
        >
          {loading ? 'Simulating...' : 'Simulate matchup'}
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
