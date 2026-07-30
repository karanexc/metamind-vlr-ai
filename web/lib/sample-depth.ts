import type { EventPlayer, PlayerEventAnalysis, PlayerEventMap } from './api';
import { SAMPLE_PLAYER_LIST, SAMPLE_PLAYER_SUMMARIES } from './sample-players';

/**
 * Offline sample data for the Depth page — used ONLY when the backend is
 * unreachable (e.g. previewing with no DB). Negative ids avoid clashing with
 * real vlr.gg ids. Series are generated deterministically so the preview is
 * stable. Illustrative numbers, not authoritative.
 */

export const SAMPLE_EVENTS = [
  { id: -101, name: 'Valorant Champions 2024 (sample)' },
  { id: -102, name: 'Masters Madrid 2024 (sample)' },
];

export const SAMPLE_EVENT_PLAYERS: EventPlayer[] = SAMPLE_PLAYER_LIST.map((p) => ({
  id: p.id,
  name: p.name,
  n_maps: 12,
}));

const OPPONENTS = ['Sentinels', 'LOUD', 'Fnatic', 'Paper Rex', 'DRX', 'Team Heretics', 'EDward Gaming', 'G2 Esports'];
const MAPS = ['Ascent', 'Bind', 'Haven', 'Split', 'Lotus', 'Sunset', 'Abyss', 'Pearl', 'Fracture'];
const AGENTS: Record<string, [string, string]> = {
  aspas: ['Jett', 'Raze'],
  Derke: ['Jett', 'Yoru'],
  TenZ: ['Jett', 'Raze'],
  Chronicle: ['Sova', 'KAY/O'],
  Less: ['Killjoy', 'Cypher'],
  ZmjjKK: ['Jett', 'Neon'],
  Demon1: ['Jett', 'Raze'],
  Jinggg: ['Raze', 'Jett'],
};

// Deterministic pseudo-random in [0,1) from a seed.
function rnd(seed: number): number {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}

export function buildSampleAnalysis(eventId: number, playerId: number): PlayerEventAnalysis | null {
  const base = SAMPLE_PLAYER_SUMMARIES[playerId];
  if (!base) return null;
  const evName = SAMPLE_EVENTS.find((e) => e.id === eventId)?.name || 'Sample Event';
  const n = 12;
  const [primary, secondary] = AGENTS[base.name] || ['Jett', 'Sova'];

  const series: PlayerEventMap[] = [];
  let kills = 0, deaths = 0, rSum = 0, acsSum = 0, kastSum = 0, adrSum = 0, hsSum = 0, wins = 0;

  for (let i = 0; i < n; i++) {
    const s = playerId * 7 + eventId * 3 + i * 13;
    const r1 = rnd(s), r2 = rnd(s + 1), r3 = rnd(s + 2), r4 = rnd(s + 3);
    const rating = Math.max(0.6, Math.min(1.7, base.avg_rating + (r1 - 0.5) * 0.5));
    const acs = Math.max(120, Math.round(base.avg_acs + (r2 - 0.5) * 90));
    const adr = Math.max(90, Math.round(base.avg_adr + (r3 - 0.5) * 55));
    const kast = Math.max(55, Math.min(95, Math.round(base.avg_kast + (r1 - 0.5) * 14)));
    const hs = Math.max(10, Math.round(base.avg_hs + (r2 - 0.5) * 14));
    const k = Math.round(14 + r1 * 12);
    const d = Math.round(11 + r2 * 9);
    const won = r4 > 0.42;
    const agent = i % 4 === 3 ? secondary : primary;

    kills += k; deaths += d; rSum += rating; acsSum += acs; kastSum += kast; adrSum += adr; hsSum += hs;
    if (won) wins++;

    series.push({
      index: i + 1,
      map_name: MAPS[i % MAPS.length],
      opponent: OPPONENTS[i % OPPONENTS.length],
      agent,
      rating: +rating.toFixed(2),
      acs,
      kills: k,
      deaths: d,
      kast,
      adr,
      hs,
      won,
      stage: i < 6 ? 'Group Stage' : 'Playoffs',
    });
  }

  const perAgentMap: Record<string, { maps: number; rating: number; acs: number }> = {};
  for (const m of series) {
    const a = (perAgentMap[m.agent as string] ||= { maps: 0, rating: 0, acs: 0 });
    a.maps++;
    a.rating += m.rating;
    a.acs += m.acs;
  }
  const per_agent = Object.entries(perAgentMap)
    .map(([agent, v]) => ({
      agent,
      maps: v.maps,
      avg_rating: +(v.rating / v.maps).toFixed(2),
      avg_acs: Math.round(v.acs / v.maps),
    }))
    .sort((a, b) => b.maps - a.maps);

  return {
    player_id: playerId,
    player_name: base.name,
    event_id: eventId,
    event_name: evName,
    n_maps: n,
    map_wins: wins,
    map_win_rate: +((wins / n) * 100).toFixed(1),
    avg_rating: +(rSum / n).toFixed(2),
    avg_acs: Math.round(acsSum / n),
    avg_kast: Math.round(kastSum / n),
    avg_adr: +(adrSum / n).toFixed(1),
    avg_hs: Math.round(hsSum / n),
    total_kills: kills,
    total_deaths: deaths,
    series,
    per_agent,
  };
}
