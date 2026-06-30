'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { api, type TeamListItem, type MatchPrediction } from '@/lib/api';
import { Select } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { ProbBar } from '@/components/ui/prob-bar';
import { Counter } from '@/components/ui/counter';
import { cn } from '@/lib/utils';

export default function PredictPage() {
  const [teams, setTeams] = useState<TeamListItem[]>([]);
  const [teamAId, setTeamAId] = useState<number | null>(null);
  const [teamBId, setTeamBId] = useState<number | null>(null);
  const [bestOf, setBestOf] = useState<number>(3);
  const [loading, setLoading] = useState(false);
  const [prediction, setPrediction] = useState<MatchPrediction | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.teams(10).then(setTeams).catch(console.error);
  }, []);

  async function handlePredict() {
    if (!teamAId || !teamBId || teamAId === teamBId) return;
    setLoading(true);
    setError(null);
    setPrediction(null);
    try {
      const result = await api.predict(teamAId, teamBId, bestOf);
      setPrediction(result);
    } catch (e: any) {
      setError(e?.message || 'Prediction failed');
    } finally {
      setLoading(false);
    }
  }

  const teamOptions = teams.map((t) => ({
    value: t.id,
    label: t.name,
    sub: `${t.n_matches} matches`,
  }));

  return (
    <div className="max-w-6xl mx-auto px-6 lg:px-8 py-16">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
          Predict
        </div>
        <h1 className="text-display font-semibold tracking-tight text-gradient">
          Match prediction
        </h1>
        <p className="mt-4 text-base text-ink-soft max-w-2xl leading-relaxed">
          Pick two teams and a format. The model predicts series outcome,
          per-map win probabilities, and surfaces a warning if it's a cross-tier
          matchup with elevated uncertainty.
        </p>
      </motion.div>

      {/* Inputs */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.15 }}
        className="mt-10 bg-surface border border-border rounded-2xl p-6"
      >
        <div className="grid md:grid-cols-[1fr_auto_1fr] gap-4 items-end">
          <Select
            label="Team A"
            options={teamOptions}
            value={teamAId}
            onChange={(v) => setTeamAId(Number(v))}
            placeholder="Choose a team..."
          />
          <div className="hidden md:flex items-center justify-center px-2 pb-2.5 font-mono text-sm text-ink-dim tracking-widest">
            VS
          </div>
          <Select
            label="Team B"
            options={teamOptions}
            value={teamBId}
            onChange={(v) => setTeamBId(Number(v))}
            placeholder="Choose a team..."
          />
        </div>

        <div className="mt-4 grid md:grid-cols-[200px_1fr_auto] gap-4 items-end">
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
          <div />
          <Button
            variant="primary"
            size="lg"
            onClick={handlePredict}
            disabled={!teamAId || !teamBId || teamAId === teamBId || loading}
            loading={loading}
            className="min-w-[160px]"
          >
            {loading ? 'Predicting...' : 'Predict outcome'}
          </Button>
        </div>

        {teamAId && teamBId && teamAId === teamBId && (
          <p className="mt-3 text-xs text-warning">
            Pick two different teams.
          </p>
        )}
      </motion.div>

      {/* Error */}
      {error && (
        <div className="mt-6 bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Prediction result */}
      <AnimatePresence mode="wait">
        {prediction && (
          <motion.div
            key="result"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="mt-12"
          >
            <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
              Projected outcome
            </div>

            {/* Hero card */}
            <div className="relative bg-gradient-card border border-border rounded-3xl p-8 overflow-hidden">
              {/* Glow */}
              <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-96 h-96 bg-accent/15 rounded-full blur-[100px] pointer-events-none" />

              <div className="relative">
                {/* Teams + meta */}
                <div className="flex items-center justify-between gap-4 mb-8">
                  <div className="flex-1">
                    <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-2">
                      Team A
                    </div>
                    <div
                      className={cn(
                        'text-2xl md:text-3xl font-semibold tracking-tight',
                        prediction.prob_a >= 0.5 ? 'text-ink' : 'text-ink-soft',
                      )}
                    >
                      {prediction.team_a_name}
                    </div>
                  </div>

                  <div className="px-3 py-1.5 bg-bg/60 border border-border rounded-full text-xs font-mono text-ink-soft tracking-widest">
                    Bo{prediction.best_of}
                  </div>

                  <div className="flex-1 text-right">
                    <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-2">
                      Team B
                    </div>
                    <div
                      className={cn(
                        'text-2xl md:text-3xl font-semibold tracking-tight',
                        prediction.prob_b > prediction.prob_a ? 'text-ink' : 'text-ink-soft',
                      )}
                    >
                      {prediction.team_b_name}
                    </div>
                  </div>
                </div>

                {/* Probabilities + bar */}
                <div className="flex items-center gap-6">
                  <div
                    className={cn(
                      'font-mono font-semibold tabular',
                      'text-5xl md:text-6xl tracking-tight',
                      prediction.prob_a >= 0.5 ? 'text-ink' : 'text-ink-dim',
                    )}
                  >
                    <Counter value={prediction.prob_a * 100} format={(n) => `${Math.round(n)}%`} />
                  </div>
                  <div className="flex-1">
                    <ProbBar probA={prediction.prob_a} delay={0.3} />
                  </div>
                  <div
                    className={cn(
                      'font-mono font-semibold tabular text-right',
                      'text-5xl md:text-6xl tracking-tight',
                      prediction.prob_b > prediction.prob_a ? 'text-ink' : 'text-ink-dim',
                    )}
                  >
                    <Counter value={prediction.prob_b * 100} format={(n) => `${Math.round(n)}%`} />
                  </div>
                </div>

                {/* Meta */}
                <div className="mt-8 pt-6 border-t border-border flex items-center justify-center gap-6 text-sm text-ink-soft">
                  <div>
                    Projected:{' '}
                    <span className="font-mono font-semibold text-ink">
                      {prediction.predicted_score_a}–{prediction.predicted_score_b}
                    </span>
                  </div>
                  <div className="w-px h-4 bg-border" />
                  <div>
                    Confidence:{' '}
                    <span className="text-ink font-medium capitalize">
                      {prediction.confidence}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Cross-tier warning */}
            {prediction.cross_tier_warning && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.6 }}
                className="mt-4 bg-warning/5 border border-warning/30 rounded-xl p-4 flex gap-3"
              >
                <AlertTriangle className="w-5 h-5 text-warning flex-shrink-0 mt-0.5" />
                <div className="text-sm">
                  <div className="font-semibold text-warning mb-1">Cross-tier matchup</div>
                  <div className="text-ink-soft leading-relaxed">
                    {prediction.cross_tier_warning}
                  </div>
                </div>
              </motion.div>
            )}

            {/* Per-map */}
            <div className="mt-10">
              <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-4">
                Per-map prediction
              </div>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {prediction.map_predictions.map((mp, i) => {
                  const pa = Math.round(mp.prob_a * 100);
                  const pb = 100 - pa;
                  const aWins = mp.prob_a >= mp.prob_b;
                  return (
                    <motion.div
                      key={mp.map_name}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.4, delay: 0.5 + i * 0.08 }}
                      className="bg-surface border border-border rounded-xl p-4 text-center hover:border-border-strong transition-colors"
                    >
                      <div className="text-sm font-semibold text-ink mb-3">{mp.map_name}</div>
                      <div className="flex items-baseline justify-between font-mono text-sm tabular mb-2">
                        <span className={aWins ? 'text-ink font-semibold' : 'text-ink-dim'}>
                          {pa}%
                        </span>
                        <span className={!aWins ? 'text-ink font-semibold' : 'text-ink-dim'}>
                          {pb}%
                        </span>
                      </div>
                      <div className="h-1 bg-bg rounded-full overflow-hidden mb-3">
                        <motion.div
                          className="h-full bg-accent rounded-full"
                          initial={{ width: 0 }}
                          animate={{ width: `${pa}%` }}
                          transition={{ duration: 0.7, delay: 0.6 + i * 0.08 }}
                        />
                      </div>
                      <div
                        className={cn(
                          'text-[0.65rem] font-semibold uppercase tracking-widest',
                          mp.confidence === 'high' && 'text-success',
                          mp.confidence === 'medium' && 'text-warning',
                          mp.confidence === 'low' && 'text-ink-dim',
                        )}
                      >
                        {mp.confidence} confidence
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            </div>

            {/* Model note */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1 }}
              className="mt-6 text-xs text-ink-dim text-center"
            >
              {prediction.note}
            </motion.div>
          </motion.div>
        )}

        {!prediction && !loading && (
          <motion.div
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="mt-16 text-center text-sm text-ink-dim"
          >
            Pick two teams and a format above to generate a prediction.
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
