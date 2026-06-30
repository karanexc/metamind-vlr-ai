'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { RefreshCw, ArrowUp, ArrowDown } from 'lucide-react';
import { api, type MatchListItem, type MatchDetail, type LossAnalysis } from '@/lib/api';
import { Select } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { formatDate, cn } from '@/lib/utils';

const TIER_OPTIONS = [
  { value: 'all', label: 'All tiers', sub: 'Recent matches across all events' },
  { value: 'international', label: 'International (VCT)', sub: 'Masters, Champions, Kickoff' },
  { value: 'tier1', label: 'Tier 1 Regional', sub: 'VCT regional leagues' },
  { value: 'tier2', label: 'Tier 2 / Challengers', sub: 'VCL, regional challengers' },
];

export default function MatchAnalysisPage() {
  const [tier, setTier] = useState<string>('all');
  const [matches, setMatches] = useState<MatchListItem[]>([]);
  const [matchId, setMatchId] = useState<number | null>(null);
  const [match, setMatch] = useState<MatchDetail | null>(null);
  const [analysis, setAnalysis] = useState<LossAnalysis | null>(null);
  const [loading, setLoading] = useState(false);

  // Load matches when tier changes
  useEffect(() => {
    setMatches([]);
    setMatchId(null);
    setMatch(null);
    setAnalysis(null);
    api.matchesByTier(tier, 100).then(setMatches).catch(console.error);
  }, [tier]);

  useEffect(() => {
    if (matchId === null) return;
    setMatch(null);
    setAnalysis(null);
    api.match(matchId).then(setMatch).catch(console.error);
  }, [matchId]);

  async function loadAnalysis(regenerate = false) {
    if (!matchId) return;
    setLoading(true);
    try {
      const a = await api.explain(matchId, regenerate);
      setAnalysis(a);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (matchId !== null) loadAnalysis(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [matchId]);

  const matchOptions = matches.map((m) => ({
    value: m.match_id,
    label: `${m.team_a} ${m.score_a}–${m.score_b} ${m.team_b}`,
    sub: `${m.event || '—'} · ${formatDate(m.datetime)}`,
  }));

  const aWon = match && match.score_a !== null && match.score_b !== null && match.score_a > match.score_b;
  const winner = match ? (aWon ? match.team_a_name : match.team_b_name) : '';
  const loser = match ? (aWon ? match.team_b_name : match.team_a_name) : '';

  return (
    <div className="max-w-6xl mx-auto px-6 lg:px-8 py-16">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
          Match analysis
        </div>
        <h1 className="text-display font-semibold tracking-tight text-gradient">
          AI-generated match breakdown
        </h1>
        <p className="mt-4 text-base text-ink-soft max-w-2xl leading-relaxed">
          Pick a tier, then a match. The XGBoost model identifies the most influential
          features via SHAP attribution. GPT-4o verbalizes them into a coaching-ready
          breakdown.
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mt-10 bg-surface border border-border rounded-2xl p-6 space-y-4"
      >
        <Select
          label="Tier"
          options={TIER_OPTIONS}
          value={tier}
          onChange={(v) => setTier(String(v))}
          searchable={false}
        />
        <Select
          label="Match"
          options={matchOptions}
          value={matchId}
          onChange={(v) => setMatchId(Number(v))}
          placeholder={
            matches.length === 0
              ? 'Loading matches...'
              : `Pick from ${matches.length} matches...`
          }
          disabled={matches.length === 0}
        />
      </motion.div>

      <AnimatePresence mode="wait">
        {match && (
          <motion.div
            key={match.match_id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.5 }}
            className="mt-10 space-y-8"
          >
            {/* Hero match card */}
            <div className="relative bg-gradient-card border border-border rounded-3xl p-8 overflow-hidden">
              <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-96 h-96 bg-accent/10 rounded-full blur-[100px]" />
              <div className="relative">
                <div className="flex justify-between items-baseline mb-6">
                  <div>
                    <div className="text-[0.7rem] uppercase tracking-widest text-ink-dim">
                      {match.event_name}
                    </div>
                    <div className="text-sm text-ink-soft mt-1">
                      {match.stage} · Bo{match.best_of}
                      {match.patch && ` · Patch ${match.patch}`}
                    </div>
                  </div>
                  <div className="text-sm text-ink-soft">{formatDate(match.datetime, 'long')}</div>
                </div>

                <div className="flex items-center justify-center gap-8 md:gap-12">
                  <div className={cn(
                    'text-2xl md:text-3xl font-semibold text-right flex-1',
                    aWon ? 'text-ink' : 'text-ink-soft',
                  )}>
                    {match.team_a_name}
                  </div>
                  <div className="font-mono text-5xl md:text-6xl font-semibold tracking-tight tabular flex items-baseline gap-2">
                    <span className={aWon ? 'text-ink' : 'text-ink-dim'}>{match.score_a}</span>
                    <span className="text-ink-dim text-3xl">:</span>
                    <span className={!aWon ? 'text-ink' : 'text-ink-dim'}>{match.score_b}</span>
                  </div>
                  <div className={cn(
                    'text-2xl md:text-3xl font-semibold flex-1',
                    !aWon ? 'text-ink' : 'text-ink-soft',
                  )}>
                    {match.team_b_name}
                  </div>
                </div>
              </div>
            </div>

            {/* AI Analysis */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-1">
                    AI analysis
                  </div>
                  <h2 className="text-xl font-semibold text-ink">
                    Why did {loser} drop this match to {winner}?
                  </h2>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => loadAnalysis(true)}
                  loading={loading}
                  disabled={loading}
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  Regenerate
                </Button>
              </div>

              {loading && !analysis && (
                <div className="bg-surface border border-border rounded-2xl p-12 text-center">
                  <div className="inline-flex items-center gap-2 text-sm text-ink-soft">
                    <span className="relative flex w-2 h-2">
                      <span className="absolute inline-flex w-full h-full rounded-full bg-accent opacity-75 animate-ping" />
                      <span className="relative inline-flex w-2 h-2 rounded-full bg-accent" />
                    </span>
                    Generating analysis...
                  </div>
                </div>
              )}

              {analysis && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="space-y-4"
                >
                  <div className="bg-surface border border-border border-l-2 border-l-accent rounded-2xl p-6">
                    <div className="text-base text-ink leading-relaxed">
                      {analysis.summary}
                    </div>
                  </div>

                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <h3 className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
                        What swung the result
                      </h3>
                      <div className="bg-surface border border-border rounded-2xl p-2">
                        {analysis.key_factors.map((f, i) => (
                          <div
                            key={i}
                            className="px-3 py-2.5 text-sm text-ink-soft border-b border-border last:border-0"
                          >
                            {f}
                          </div>
                        ))}
                      </div>
                    </div>

                    <div>
                      <h3 className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
                        Performances
                      </h3>
                      <div className="bg-surface border border-border rounded-2xl p-2">
                        {analysis.standout_players.map((p, i) => (
                          <div
                            key={i}
                            className="px-3 py-2.5 text-sm text-ink-soft border-b border-border last:border-0 flex items-start gap-2"
                          >
                            <ArrowUp className="w-3.5 h-3.5 text-success flex-shrink-0 mt-0.5" />
                            {p}
                          </div>
                        ))}
                        {analysis.underperformers.map((p, i) => (
                          <div
                            key={i}
                            className="px-3 py-2.5 text-sm text-ink-soft border-b border-border last:border-0 flex items-start gap-2"
                          >
                            <ArrowDown className="w-3.5 h-3.5 text-accent flex-shrink-0 mt-0.5" />
                            {p}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </div>

            {/* Per-map summary */}
            <div>
              <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
                Map-by-map
              </div>
              <div className="space-y-3">
                {match.maps.map((m) => (
                  <div
                    key={m.index}
                    className="bg-surface border border-border rounded-xl px-5 py-3 flex items-center justify-between"
                  >
                    <div>
                      <div className="text-xs text-ink-dim">Map {m.index}</div>
                      <div className="font-semibold text-ink">{m.name}</div>
                    </div>
                    <div className="font-mono font-semibold text-ink tabular">
                      {m.score_a}–{m.score_b}
                    </div>
                    {m.picked_by && (
                      <div className="text-xs text-ink-dim px-2 py-1 bg-bg rounded">
                        {m.picked_by} pick
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
