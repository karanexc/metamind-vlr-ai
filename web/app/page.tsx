'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowRight, Sparkles, BarChart3, Zap, Shield, Users, Map as MapIcon } from 'lucide-react';
import { api, type DatabaseStats, type MatchListItem, type TopPlayer } from '@/lib/api';
import { StatTile } from '@/components/ui/stat-tile';
import { Skeleton } from '@/components/ui/skeleton';
import { SpotlightCard } from '@/components/ui/spotlight-card';
import { LiveRefresh } from '@/components/ui/live-refresh';
import { getMapArt, getAgents, type ValAgent } from '@/lib/valorant';
import { formatDate } from '@/lib/utils';

// Current competitive map pool — static, so it renders regardless of the API.
const MAP_POOL = [
  'Abyss', 'Ascent', 'Bind', 'Fracture', 'Haven',
  'Lotus', 'Pearl', 'Split', 'Sunset',
];

export default function HomePage() {
  const [stats, setStats] = useState<DatabaseStats | null>(null);
  const [matches, setMatches] = useState<MatchListItem[]>([]);
  const [topPlayers, setTopPlayers] = useState<TopPlayer[]>([]);
  const [loading, setLoading] = useState(true);
  const [mapArt, setMapArt] = useState<Record<string, string>>({});
  const [agents, setAgents] = useState<ValAgent[]>([]);

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

  // Official Valorant art (map splashes + agent portraits). Fails soft.
  useEffect(() => {
    getMapArt().then(setMapArt).catch(() => {});
    getAgents().then(setAgents).catch(() => {});
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
            <LiveRefresh />
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
            <Link
              href="/fantasy"
              className="inline-flex items-center gap-2 px-5 py-3 text-ink-soft font-medium rounded-lg hover:text-ink hover:bg-surface transition-all"
            >
              Build a fantasy roster
              <ArrowRight className="w-4 h-4" />
            </Link>
          </motion.div>
        </div>
      </section>

      {/* STATS STRIP — always reserves its space; skeletons while loading */}
      <section className="max-w-7xl mx-auto px-6 lg:px-8 -mt-4 mb-24">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {loading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-[104px]" />
            ))
          ) : stats ? (
            <>
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
            </>
          ) : (
            <div className="col-span-2 md:col-span-4 bg-surface border border-border rounded-2xl p-6 text-sm text-ink-dim text-center">
              Dataset stats are unavailable right now. Once the API is connected they load automatically.
            </div>
          )}
        </div>
      </section>

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
              <SpotlightCard className="h-full">
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
              </SpotlightCard>
            </motion.div>
          ))}
        </div>
      </section>

      {/* EXPLORE THE DATASET — surfaces Teams + Players */}
      <section className="max-w-7xl mx-auto px-6 lg:px-8 mb-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
            Explore the dataset
          </div>
          <h2 className="text-2xl font-semibold text-ink">Dig into teams and players.</h2>
        </motion.div>

        <div className="mt-8 grid md:grid-cols-2 gap-4">
          {[
            {
              icon: Shield,
              title: 'Teams',
              body: 'Regional leaderboards with logos, rosters, map win-rates and recent form.',
              href: '/teams',
              stat: stats ? `${stats.teams.toLocaleString()} teams tracked` : null,
            },
            {
              icon: Users,
              title: 'Players',
              body: 'Every player with photos, agents, per-map splits and a rolling form chart.',
              href: '/players',
              stat: stats ? `${stats.players.toLocaleString()} players` : null,
            },
          ].map((card, i) => (
            <motion.div
              key={card.href}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
            >
              <SpotlightCard className="h-full">
              <Link
                href={card.href}
                className="group relative flex items-center gap-5 bg-gradient-card border border-border rounded-2xl p-6 h-full hover:border-border-strong transition-all duration-300 hover:-translate-y-1 overflow-hidden"
              >
                <div className="absolute -bottom-16 -left-10 w-40 h-40 bg-accent/10 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <div className="relative w-12 h-12 rounded-xl bg-surface border border-border flex items-center justify-center flex-shrink-0 group-hover:border-accent/40 transition-colors">
                  <card.icon className="w-6 h-6 text-ink-soft group-hover:text-accent transition-colors" />
                </div>
                <div className="relative min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-semibold text-ink">{card.title}</h3>
                    {card.stat && (
                      <span className="text-xs font-mono text-ink-dim tabular">{card.stat}</span>
                    )}
                  </div>
                  <p className="text-sm text-ink-soft leading-relaxed mt-1">{card.body}</p>
                </div>
                <ArrowRight className="relative w-5 h-5 text-ink-dim ml-auto flex-shrink-0 group-hover:text-accent group-hover:translate-x-0.5 transition-all" />
              </Link>
              </SpotlightCard>
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
            {loading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-[68px] rounded-xl" />
              ))
            ) : matches.length > 0 ? (
              matches.map((m, i) => {
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
              })
            ) : (
              <div className="bg-surface border border-border rounded-xl px-4 py-10 text-sm text-ink-dim text-center">
                No recent matches to show yet.
              </div>
            )}
          </div>
        </div>

        {/* Top players */}
        <div className="lg:col-span-2">
          <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
            By avg rating
          </div>
          <h2 className="text-2xl font-semibold text-ink mb-6">Top performers</h2>
          {loading ? (
            <Skeleton className="h-[352px] rounded-2xl" />
          ) : topPlayers.length > 0 ? (
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
          ) : (
            <div className="bg-surface border border-border rounded-2xl px-4 py-10 text-sm text-ink-dim text-center">
              No player leaderboard yet.
            </div>
          )}
        </div>
      </section>

      {/* MAP POOL — static showcase, always renders */}
      <section className="max-w-7xl mx-auto px-6 lg:px-8 mb-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="flex items-end justify-between gap-4"
        >
          <div>
            <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
              Competitive map pool
            </div>
            <h2 className="text-2xl font-semibold text-ink">Every map the model knows.</h2>
          </div>
          <div className="hidden sm:flex items-center gap-2 text-xs text-ink-dim">
            <MapIcon className="w-4 h-4" />
            {MAP_POOL.length} maps in rotation
          </div>
        </motion.div>

        <div className="mt-8 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-9 gap-3">
          {MAP_POOL.map((name, i) => (
            <motion.div
              key={name}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.05 }}
              className="group relative aspect-[3/4] rounded-xl border border-border overflow-hidden bg-gradient-card hover:border-accent/40 transition-colors"
            >
              {mapArt[name] && (
                <>
                  <img
                    src={mapArt[name]}
                    alt={name}
                    loading="lazy"
                    className="absolute inset-0 w-full h-full object-cover opacity-70 group-hover:opacity-90 group-hover:scale-105 transition-all duration-500"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-bg via-bg/50 to-transparent" />
                </>
              )}
              <div className="absolute inset-0 grid-bg opacity-40" />
              <div className="absolute -top-8 -right-8 w-24 h-24 bg-accent/10 rounded-full blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              <div className="absolute top-3 left-3 text-xs font-mono text-ink-dim tabular">
                {String(i + 1).padStart(2, '0')}
              </div>
              <div className="absolute bottom-3 left-3 right-3">
                <div className="text-sm font-semibold text-ink group-hover:text-accent transition-colors">
                  {name}
                </div>
                <div className="text-[0.65rem] uppercase tracking-widest text-ink-dim mt-0.5">
                  Map
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* AGENTS SHOWCASE — marquee of official agent art (loads on network) */}
      {agents.length > 0 && (
        <section className="mb-24">
          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
            >
              <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
                The roster
              </div>
              <h2 className="text-2xl font-semibold text-ink">Every agent in the game.</h2>
            </motion.div>
          </div>

          <div className="marquee relative mt-8 overflow-hidden">
            <div className="absolute left-0 top-0 bottom-0 w-24 z-10 bg-gradient-to-r from-bg to-transparent pointer-events-none" />
            <div className="absolute right-0 top-0 bottom-0 w-24 z-10 bg-gradient-to-l from-bg to-transparent pointer-events-none" />
            <div className="flex gap-4 w-max animate-marquee px-4">
              {[...agents, ...agents].map((a, i) => {
                const g = a.gradient?.length ? a.gradient : ['#FA4454', '#7A2730'];
                return (
                  <div
                    key={`${a.name}-${i}`}
                    className="group relative w-40 h-56 rounded-2xl overflow-hidden border border-border flex-shrink-0"
                    style={{ background: `linear-gradient(160deg, ${g[0]}, ${g[g.length - 1]})` }}
                  >
                    <div className="absolute inset-0 bg-bg/30" />
                    <img
                      src={a.portrait}
                      alt={a.name}
                      loading="lazy"
                      className="absolute inset-0 w-full h-full object-cover object-top scale-105 group-hover:scale-110 transition-transform duration-500"
                    />
                    <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-bg to-transparent" />
                    <div className="absolute bottom-3 left-3 right-3">
                      <div className="text-sm font-semibold text-ink truncate">{a.name}</div>
                      <div className="text-[0.65rem] uppercase tracking-widest text-ink-soft">
                        {a.role}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
