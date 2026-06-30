'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip,
  BarChart, Bar, CartesianGrid,
} from 'recharts';
import { api, type PlayerListItem, type PlayerSummary } from '@/lib/api';
import { Select } from '@/components/ui/select';
import { StatTile } from '@/components/ui/stat-tile';

export default function PlayersPage() {
  const [players, setPlayers] = useState<PlayerListItem[]>([]);
  const [playerId, setPlayerId] = useState<number | null>(null);
  const [summary, setSummary] = useState<PlayerSummary | null>(null);

  useEffect(() => {
    api.players(20).then(setPlayers).catch(console.error);
  }, []);

  useEffect(() => {
    if (playerId !== null) {
      setSummary(null);
      api.player(playerId).then(setSummary).catch(console.error);
    }
  }, [playerId]);

  const playerOptions = players.map((p) => ({
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
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-3">
          Players
        </div>
        <h1 className="text-display font-semibold tracking-tight text-gradient">
          Player explorer
        </h1>
        <p className="mt-4 text-base text-ink-soft max-w-2xl">
          Career stats, agent specialization, and recent form.
        </p>
      </motion.div>

      <div className="mt-10 max-w-md">
        <Select
          options={playerOptions}
          value={playerId}
          onChange={(v) => setPlayerId(Number(v))}
          placeholder="Pick a player..."
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

          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-10">
            <StatTile
              label="Rating"
              value={summary.avg_rating.toFixed(2)}
              sub={`${summary.n_maps.toLocaleString()} maps`}
              index={0}
            />
            <StatTile
              label="ACS"
              value={Math.round(summary.avg_acs)}
              index={1}
            />
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

          {/* Recent form chart */}
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

          {/* Per agent */}
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
  );
}
