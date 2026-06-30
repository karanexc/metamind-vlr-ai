'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowRight, Sparkles, BarChart3, Zap } from 'lucide-react';
import { api, type DatabaseStats, type MatchListItem, type TopPlayer } from '@/lib/api';
import { Counter } from '@/components/ui/counter';
import { StatTile } from '@/components/ui/stat-tile';
import { formatDate } from '@/lib/utils';

export default function HomePage() {
  const [stats, setStats] = useState<DatabaseStats | null>(null);
  const [matches, setMatches] = useState<MatchListItem[]>([]);
  const [topPlayers, setTopPlayers] = useState<TopPlayer[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.stats(),
      api.recentMatches(6),
      api.topPlayers('rating', 30, 10),
    ])
      .then(([s, m, p]) => {
        setStats(s);
        setMatches(m);
        setTopPlayers(p);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      {/* HERO */}
      <section className="relative overflow-hidden">
        {/* Animated background */}
        <div className="absolute inset-0 grid-bg pointer-events-none" />
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] rounded-full bg-accent/10 blur-[120px] opacity-60" />
        </div>

        <div className="relative max-w-7xl mx-auto px-6 lg:px-8 pt-24 pb-20">
          {/* Eyebrow */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="flex items-center gap-2 mb-8"
          >
            <div className="flex items-center gap-1.5 px-3 py-1 bg-surface border border-border rounded-full text-xs text-ink-soft">
              <span className="relative flex w-1.5 h-1.5">
                <span className="absolute inline-flex w-full h-full rounded-full bg-accent opacity-75 animate-ping" />
                <span className="relative inline-flex w-1.5 h-1.5 rounded-full bg-accent" />
              </span>
              <span className="font-medium">Live data</span>
              <span className="text-ink-dim">·</span>
              <span>{stats ? `${stats.real_matches.toLocaleString()} matches indexed` : 'Indexing...'}</span>
            </div>
          </motion.div>

          {/* Hero headline */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
            className="text-hero font-semibold tracking-tighter text-gradient max-w-5xl"
          >
            Match intelligence for
            <br />
            competitive Valorant.
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.25, ease: [0.16, 1, 0.3, 1] }}
            className="mt-8 text-lg text-ink-soft max-w-2xl leading-relaxed"
          >
            Prediction, performance analysis, and roster intelligence — powered by an
            XGBoost model trained on every Tier 1 and Challengers match since 2024,
            grounded by GPT-4o for human-language explanations.
          </motion.p>

          {/* CTAs */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="mt-10 flex flex-wrap gap-3"
          >
            <Link
              href="/predict"
              className="group inline-flex items-center gap-2 px-5 py-3 bg-accent text-white font-medium rounded-lg shadow-lg shadow-accent/20 hover:shadow-accent/30 hover:bg-accent-hover transition-all"
            >
              Make a prediction
              <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </Link>
            <Link
              href="/match-analysis"
              className="inline-flex items-center gap-2 px-5 py-3 bg-surface border border-border text-ink font-medium rounded-lg hover:border-border-strong hover:bg-surface-hover transition-all"
            >
              Browse analyses
            </Link>
          </motion.div>
        </div>
      </section>

      {/* STATS STRIP */}
      {stats && (
        <section className="max-w-7xl mx-auto px-6 lg:px-8 -mt-4 mb-24">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatTile
              label="Matches"
              value={stats.real_matches}
              sub={`${(stats.matches - stats.real_matches).toLocaleString()} forfeits excluded`}
              index={0}
            />
            <StatTile label="Teams" value={stats.teams} index={1} />
            <StatTile label="Events" value={stats.events} index={2} />
            <StatTile
              label="Players"
              value={stats.players}
              sub={`${stats.player_rows.toLocaleString()} performances`}
              index={3}
            />
          </div>
        </section>
      )}

      {/* TOOLS */}
      <section className="max-w-7xl mx-auto px-6 lg:px-8 mb-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
            What you can do
          </div>
          <h2 className="text-display font-semibold tracking-tight text-gradient max-w-3xl">
            Three tools, one model, real predictions.
          </h2>
        </motion.div>

        <div className="mt-12 grid md:grid-cols-3 gap-4">
          {[
            {
              icon: Zap,
              title: 'Match prediction',
              body: 'Pick two teams. Get win probabilities, projected scoreline, and per-map breakdown grounded in the model.',
              href: '/predict',
            },
            {
              icon: Sparkles,
              title: 'AI match analysis',
              body: 'Pick a past match. Get a coaching-ready breakdown grounded in the model attribution and per-player stats.',
              href: '/match-analysis',
            },
            {
              icon: BarChart3,
              title: 'Fantasy mode',
              body: 'Build a 5-player roster from anywhere in the database. Simulate against any team or another roster.',
              href: '/fantasy',
            },
          ].map((tool, i) => (
            <motion.div
              key={tool.href}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
            >
              <Link
                href={tool.href}
                className="group relative block bg-surface border border-border rounded-2xl p-6 h-full hover:border-border-strong transition-all duration-300 hover:-translate-y-1 overflow-hidden"
              >
                {/* Subtle accent glow on hover */}
                <div className="absolute -top-20 -right-20 w-40 h-40 bg-accent/10 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

                <div className="relative">
                  <div className="w-10 h-10 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center mb-4">
                    <tool.icon className="w-5 h-5 text-accent" />
                  </div>
                  <h3 className="text-lg font-semibold text-ink mb-2">{tool.title}</h3>
                  <p className="text-sm text-ink-soft leading-relaxed">{tool.body}</p>
                  <div className="mt-4 inline-flex items-center gap-1 text-sm text-ink-soft group-hover:text-accent transition-colors">
                    Open
                    <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                  </div>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      </section>

      {/* RECENT MATCHES + TOP PLAYERS */}
      <section className="max-w-7xl mx-auto px-6 lg:px-8 mb-24 grid lg:grid-cols-5 gap-6">
        {/* Recent matches */}
        <div className="lg:col-span-3">
          <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
            Recent matches
          </div>
          <h2 className="text-2xl font-semibold text-ink mb-6">Latest results</h2>
          <div className="space-y-2">
            {matches.map((m, i) => {
              const aWon = m.score_a > m.score_b;
              return (
                <motion.div
                  key={m.match_id}
                  initial={{ opacity: 0, x: -10 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4, delay: i * 0.05 }}
                  className="bg-surface border border-border rounded-xl px-4 py-3 hover:border-border-strong transition-colors"
                >
                  <div className="text-[0.7rem] uppercase tracking-wider text-ink-dim mb-1.5">
                    {m.event || '—'} · {formatDate(m.datetime)}
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <span className={aWon ? 'text-ink font-semibold' : 'text-ink-soft'}>
                        {m.team_a}
                      </span>
                      <span className="font-mono font-semibold text-ink tabular px-2">
                        {m.score_a}–{m.score_b}
                      </span>
                      <span className={!aWon ? 'text-ink font-semibold' : 'text-ink-soft'}>
                        {m.team_b}
                      </span>
                    </div>
                    {m.best_of && (
                      <span className="text-xs font-mono text-ink-dim">Bo{m.best_of}</span>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>

        {/* Top players */}
        <div className="lg:col-span-2">
          <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
            By avg rating
          </div>
          <h2 className="text-2xl font-semibold text-ink mb-6">Top performers</h2>
          <div className="bg-surface border border-border rounded-2xl overflow-hidden">
            {topPlayers.map((p, i) => (
              <motion.div
                key={p.player}
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.3, delay: i * 0.04 }}
                className="flex items-center justify-between px-4 py-3 border-b border-border last:border-0 hover:bg-surface-hover transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-xs font-mono text-ink-dim w-5 tabular">{i + 1}</span>
                  <span className="text-ink text-sm font-medium truncate">{p.player}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-ink-dim font-mono tabular">{p.n_maps}</span>
                  <span className="text-sm font-mono font-semibold text-ink tabular">
                    {p.avg_metric.toFixed(2)}
                  </span>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
