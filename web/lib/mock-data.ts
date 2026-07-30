/**
 * Central offline sample tournament. When the backend is unreachable,
 * `api` (see api.ts) routes every request through `resolveMock`, so the whole
 * app is explorable and "linked together" with one coherent dataset. On a real
 * deployment the backend answers and none of this is ever used.
 *
 * Everything is deterministic (seeded) and illustrative — not real stats.
 */

// Deterministic pseudo-random in [0,1).
function rng(seed: number): number {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}
const r2 = (n: number) => Math.round(n * 100) / 100;

// --- Teams ---------------------------------------------------------------
const TEAM_DEFS = [
  { id: 8001, name: 'Sentinels', region: 'americas', country: 'us' },
  { id: 8002, name: 'LOUD', region: 'americas', country: 'br' },
  { id: 8003, name: 'Fnatic', region: 'emea', country: 'gb' },
  { id: 8004, name: 'Paper Rex', region: 'pacific', country: 'sg' },
  { id: 8005, name: 'DRX', region: 'pacific', country: 'kr' },
  { id: 8006, name: 'Team Heretics', region: 'emea', country: 'es' },
  { id: 8007, name: 'EDward Gaming', region: 'china', country: 'cn' },
  { id: 8008, name: 'G2 Esports', region: 'americas', country: 'us' },
];

const ROSTERS: Record<number, string[]> = {
  8001: ['TenZ', 'zekken', 'Sacy', 'pANcada', 'johnqt'],
  8002: ['aspas', 'Less', 'tuyz', 'cauanzin', 'saadhak'],
  8003: ['Derke', 'Alfajer', 'Leo', 'Boaster', 'Chronicle'],
  8004: ['something', 'f0rsakeN', 'Jinggg', 'd4v41', 'mindfreak'],
  8005: ['MaKo', 'Rb', 'BuZz', 'Foxy9', 'Zest'],
  8006: ['MiniBoo', 'benjyfishy', 'RieNs', 'wo0t', 'Keiko'],
  8007: ['ZmjjKK', 'nobody', 'CHICHOO', 'Haodong', 'Smoggy'],
  8008: ['valyn', 'trent', 'JonahP', 'leaf', 'jawgemo'],
};

const ROLE_AGENTS = [
  ['Jett', 'Raze', 'Neon'],
  ['Sova', 'Fade', 'KAY/O'],
  ['Omen', 'Viper', 'Astra'],
  ['Killjoy', 'Cypher', 'Chamber'],
  ['Gekko', 'Breach', 'Skye'],
];
const COUNTRIES = ['us', 'br', 'kr', 'gb', 'es', 'sg', 'cn', 'jp', 'fr', 'se'];

interface MockPlayer {
  id: number;
  name: string;
  teamId: number;
  teamName: string;
  region: string;
  country: string;
  agents: string[];
  rating: number;
  acs: number;
  kast: number;
  adr: number;
  hs: number;
}

const PLAYERS: MockPlayer[] = [];
(() => {
  let pid = 7001;
  TEAM_DEFS.forEach((t) => {
    ROSTERS[t.id].forEach((name, i) => {
      const s = pid;
      PLAYERS.push({
        id: pid,
        name,
        teamId: t.id,
        teamName: t.name,
        region: t.region,
        country: COUNTRIES[pid % COUNTRIES.length],
        agents: ROLE_AGENTS[i],
        rating: r2(0.98 + rng(s * 3.1) * 0.28),
        acs: Math.round(195 + rng(s * 1.7) * 85),
        kast: Math.round(68 + rng(s * 2.3) * 12),
        adr: r2(135 + rng(s * 0.9) * 45),
        hs: Math.round(18 + rng(s * 4.2) * 20),
      });
      pid++;
    });
  });
})();

const playerById = (id: number) => PLAYERS.find((p) => p.id === id);
const teamById = (id: number) => TEAM_DEFS.find((t) => t.id === id);
const teamStrength = (id: number) => {
  const roster = PLAYERS.filter((p) => p.teamId === id);
  return roster.reduce((s, p) => s + p.rating, 0) / (roster.length || 1);
};

// --- Events + matches ----------------------------------------------------
const EVENTS = [
  { id: 9001, name: 'Valorant Champions 2025 (sample)' },
  { id: 9002, name: 'Masters Toronto 2025 (sample)' },
];

const MAP_POOL = ['Ascent', 'Bind', 'Haven', 'Lotus', 'Sunset', 'Split', 'Abyss'];

const MATCHUPS: [number, number][] = [
  [8001, 8002], [8003, 8004], [8005, 8006], [8007, 8008],
  [8001, 8003], [8002, 8004], [8005, 8007], [8006, 8008],
];

interface MockMatch {
  id: number;
  eventId: number;
  a: number;
  b: number;
  score_a: number;
  score_b: number;
  best_of: number;
  stage: string;
  datetime: string;
  maps: { index: number; name: string; sa: number; sb: number; picked_by: string }[];
}

const MATCHES: MockMatch[] = MATCHUPS.map((mu, i) => {
  const [a, b] = mu;
  const sA = teamStrength(a);
  const sB = teamStrength(b);
  const aWins = sA + (rng(i * 5 + 1) - 0.5) * 0.15 >= sB;
  const threeMaps = rng(i * 2 + 3) > 0.5;
  const nMaps = threeMaps ? 3 : 2;
  const maps = Array.from({ length: nMaps }).map((_, mi) => {
    // winner of this map
    const aMap = mi === 0 ? aWins : mi === 1 ? !aWins : aWins;
    const loserScore = 6 + Math.round(rng(i * 10 + mi) * 6);
    return {
      index: mi + 1,
      name: MAP_POOL[(i + mi) % MAP_POOL.length],
      sa: aMap ? 13 : loserScore,
      sb: aMap ? loserScore : 13,
      picked_by: mi % 2 === 0 ? teamById(a)!.name : teamById(b)!.name,
    };
  });
  return {
    id: 9101 + i,
    eventId: 9001,
    a,
    b,
    score_a: aWins ? 2 : threeMaps ? 1 : 0,
    score_b: aWins ? (threeMaps ? 1 : 0) : 2,
    best_of: 3,
    stage: i < 4 ? 'Group Stage: Week 1' : 'Playoffs: Upper Bracket',
    datetime: `2025-08-${String(10 + i).padStart(2, '0')}T18:00:00Z`,
    maps,
  };
});

const matchById = (id: number) => MATCHES.find((m) => m.id === id);

// Per-map player stat row for a given player, varied around their base.
function statRow(p: MockPlayer, seed: number, agent: string) {
  const rating = r2(Math.max(0.5, Math.min(1.8, p.rating + (rng(seed) - 0.5) * 0.5)));
  const acs = Math.max(120, Math.round(p.acs + (rng(seed + 1) - 0.5) * 90));
  return {
    player: p.name,
    team: p.teamName,
    agent,
    rating,
    acs,
    k: Math.round(14 + rng(seed + 2) * 12),
    d: Math.round(11 + rng(seed + 3) * 9),
    a: Math.round(4 + rng(seed + 4) * 8),
    kast: Math.max(55, Math.min(95, Math.round(p.kast + (rng(seed + 5) - 0.5) * 12))),
    adr: r2(Math.max(90, p.adr + (rng(seed + 6) - 0.5) * 50)),
    hs: Math.max(10, Math.round(p.hs + (rng(seed + 7) - 0.5) * 14)),
  };
}

function buildMatchDetail(m: MockMatch) {
  const rosterA = PLAYERS.filter((p) => p.teamId === m.a);
  const rosterB = PLAYERS.filter((p) => p.teamId === m.b);
  const maps = m.maps.map((mp) => {
    const stats = [
      ...rosterA.map((p, k) => statRow(p, m.id * 100 + mp.index * 10 + k, p.agents[0])),
      ...rosterB.map((p, k) => statRow(p, m.id * 100 + mp.index * 10 + 50 + k, p.agents[0])),
    ].sort((x, y) => (y.rating || 0) - (x.rating || 0));
    return { index: mp.index, name: mp.name, score_a: mp.sa, score_b: mp.sb, picked_by: mp.picked_by, stats };
  });
  return {
    match_id: m.id,
    team_a_name: teamById(m.a)!.name,
    team_b_name: teamById(m.b)!.name,
    team_a_id: m.a,
    team_b_id: m.b,
    score_a: m.score_a,
    score_b: m.score_b,
    best_of: m.best_of,
    stage: m.stage,
    patch: '9.0',
    datetime: m.datetime,
    event_name: EVENTS.find((e) => e.id === m.eventId)!.name,
    event_id: m.eventId,
    maps,
  };
}

function matchListItem(m: MockMatch) {
  return {
    match_id: m.id,
    team_a: teamById(m.a)!.name,
    team_b: teamById(m.b)!.name,
    score_a: m.score_a,
    score_b: m.score_b,
    best_of: m.best_of,
    stage: m.stage,
    datetime: m.datetime,
    event: EVENTS.find((e) => e.id === m.eventId)!.name,
  };
}

function playerSummary(p: MockPlayer) {
  const recent_form = Array.from({ length: 10 }).map((_, i) => ({
    rating: r2(Math.max(0.6, Math.min(1.7, p.rating + (rng(p.id * 2 + i) - 0.5) * 0.45))),
  }));
  const per_agent = p.agents.slice(0, 2).map((agent, i) => ({
    agent,
    played: 20 - i * 7,
    avg_rating: r2(p.rating + (i === 0 ? 0.03 : -0.05)),
    avg_acs: Math.round(p.acs + (i === 0 ? 6 : -10)),
  }));
  const totalMaps = 60;
  return {
    id: p.id,
    name: p.name,
    n_maps: totalMaps,
    avg_rating: p.rating,
    avg_acs: p.acs,
    avg_kast: p.kast,
    avg_adr: p.adr,
    avg_hs: p.hs,
    total_kills: Math.round(totalMaps * (15 + p.rating * 4)),
    total_deaths: Math.round(totalMaps * 14),
    per_agent,
    per_map: [],
    recent_form,
  };
}

function leaderboardTeam(id: number, rank: number) {
  const t = teamById(id)!;
  const roster = PLAYERS.filter((p) => p.teamId === id);
  const wins = 18 - rank;
  const losses = 6 + rank;
  return {
    id: t.id,
    name: t.name,
    logo_url: null,
    country: t.country,
    region: t.region,
    matches_played: wins + losses,
    wins,
    losses,
    win_pct: r2((wins / (wins + losses)) * 100),
    roster: roster.map((p) => ({ id: p.id, name: p.name, image_url: null, country: p.country })),
  };
}

function buildDepthAnalysis(eventId: number, playerId: number) {
  const p = playerById(playerId);
  if (!p) return null;
  const n = 12;
  const opponents = TEAM_DEFS.filter((t) => t.id !== p.teamId).map((t) => t.name);
  const series = Array.from({ length: n }).map((_, i) => {
    const s = playerId * 7 + eventId * 3 + i * 13;
    const rating = r2(Math.max(0.6, Math.min(1.7, p.rating + (rng(s) - 0.5) * 0.5)));
    return {
      index: i + 1,
      map_name: MAP_POOL[i % MAP_POOL.length],
      opponent: opponents[i % opponents.length],
      agent: p.agents[i % 4 === 3 ? 1 : 0],
      rating,
      acs: Math.max(120, Math.round(p.acs + (rng(s + 1) - 0.5) * 90)),
      kills: Math.round(14 + rng(s + 2) * 12),
      deaths: Math.round(11 + rng(s + 3) * 9),
      kast: Math.max(55, Math.min(95, Math.round(p.kast + (rng(s) - 0.5) * 14))),
      adr: r2(Math.max(90, p.adr + (rng(s + 2) - 0.5) * 55)),
      hs: Math.max(10, Math.round(p.hs + (rng(s + 1) - 0.5) * 14)),
      won: rng(s + 4) > 0.42,
      stage: i < 6 ? 'Group Stage' : 'Playoffs',
    };
  });
  const n0 = series.length;
  const sum = (f: (x: any) => number) => series.reduce((a, x) => a + f(x), 0);
  const perAgent: Record<string, { maps: number; rating: number; acs: number }> = {};
  for (const m of series) {
    const a = (perAgent[m.agent] ||= { maps: 0, rating: 0, acs: 0 });
    a.maps++; a.rating += m.rating; a.acs += m.acs;
  }
  return {
    player_id: p.id,
    player_name: p.name,
    event_id: eventId,
    event_name: EVENTS.find((e) => e.id === eventId)?.name || 'Sample Event',
    n_maps: n0,
    map_wins: series.filter((x) => x.won).length,
    map_win_rate: r2((series.filter((x) => x.won).length / n0) * 100),
    avg_rating: r2(sum((x) => x.rating) / n0),
    avg_acs: Math.round(sum((x) => x.acs) / n0),
    avg_kast: Math.round(sum((x) => x.kast) / n0),
    avg_adr: r2(sum((x) => x.adr) / n0),
    avg_hs: Math.round(sum((x) => x.hs) / n0),
    total_kills: sum((x) => x.kills),
    total_deaths: sum((x) => x.deaths),
    series,
    per_agent: Object.entries(perAgent)
      .map(([agent, v]) => ({ agent, maps: v.maps, avg_rating: r2(v.rating / v.maps), avg_acs: Math.round(v.acs / v.maps) }))
      .sort((x, y) => y.maps - x.maps),
  };
}

function buildPrediction(nameA: string, nameB: string, pA: number, bestOf: number) {
  const clamp = (x: number) => Math.max(0.2, Math.min(0.8, x));
  const prob_a = clamp(pA);
  const wins = (bestOf + 1) / 2;
  const map_predictions = MAP_POOL.slice(0, 5).map((name, i) => {
    const p = clamp(prob_a + (rng(i * 3 + 1) - 0.5) * 0.1);
    return { map_name: name, prob_a: r2(p), prob_b: r2(1 - p), confidence: Math.abs(p - 0.5) > 0.15 ? 'high' : Math.abs(p - 0.5) > 0.07 ? 'medium' : 'low' };
  });
  return {
    team_a_name: nameA,
    team_b_name: nameB,
    prob_a: r2(prob_a),
    prob_b: r2(1 - prob_a),
    predicted_score_a: prob_a >= 0.5 ? wins : Math.round((1 - prob_a) * bestOf),
    predicted_score_b: prob_a >= 0.5 ? Math.round((1 - prob_a) * bestOf) : wins,
    best_of: bestOf,
    map_predictions,
    confidence: Math.abs(prob_a - 0.5) > 0.15 ? 'high' : Math.abs(prob_a - 0.5) > 0.07 ? 'medium' : 'low',
    note: 'Sample prediction (offline demo data).',
    cross_tier_warning: null,
  };
}

// --- Router --------------------------------------------------------------
export function resolveMock(rawPath: string, init?: RequestInit): any {
  const [path, query = ''] = rawPath.replace(/^\/api\/v1/, '').split('?');
  const qs = new URLSearchParams(query);
  const method = (init?.method || 'GET').toUpperCase();
  const body = init?.body ? JSON.parse(init.body as string) : {};
  const seg = path.split('/').filter(Boolean);

  // stats
  if (path === '/stats') {
    const totalMaps = MATCHES.reduce((s, m) => s + m.maps.length, 0);
    return {
      matches: MATCHES.length,
      real_matches: MATCHES.length,
      teams: TEAM_DEFS.length,
      events: EVENTS.length,
      players: PLAYERS.length,
      maps: totalMaps,
      player_rows: totalMaps * 10,
      earliest_match: MATCHES[0].datetime,
      latest_match: MATCHES[MATCHES.length - 1].datetime,
    };
  }

  // matches
  if (path === '/matches/recent' || path.startsWith('/matches/by-tier/')) {
    return MATCHES.map(matchListItem);
  }
  if (seg[0] === 'matches' && seg.length === 2) {
    const m = matchById(Number(seg[1]));
    return m ? buildMatchDetail(m) : undefined;
  }

  // events
  if (path === '/events') return EVENTS;

  // players
  if (path === '/players' && method === 'GET') {
    return PLAYERS.map((p) => ({ id: p.id, name: p.name, n_maps: 60 }));
  }
  if (seg[0] === 'players' && seg[1] === 'top') {
    const limit = Number(qs.get('limit') || 10);
    return [...PLAYERS]
      .sort((a, b) => b.rating - a.rating)
      .slice(0, limit)
      .map((p) => ({ player: p.name, n_maps: 60, avg_metric: p.rating }));
  }
  if (seg[0] === 'players' && seg.length === 2) {
    const p = playerById(Number(seg[1]));
    return p ? playerSummary(p) : undefined;
  }

  // teams
  if (path === '/teams' && method === 'GET') {
    return TEAM_DEFS.map((t) => ({ id: t.id, name: t.name, n_matches: 24 }));
  }
  if (seg[0] === 'teams' && seg[2] === 'roster') {
    const roster = PLAYERS.filter((p) => p.teamId === Number(seg[1]));
    return roster.map((p) => ({ id: p.id, name: p.name, image_url: null, country: p.country, real_name: null, last_played: null }));
  }
  if (seg[0] === 'regions' && seg[2] === 'top-teams') {
    const region = seg[1];
    const ranked = TEAM_DEFS.filter((t) => t.region === region).length
      ? TEAM_DEFS.filter((t) => t.region === region)
      : TEAM_DEFS;
    return ranked.slice(0, 5).map((t, i) => {
      const lb = leaderboardTeam(t.id, i);
      return { id: lb.id, name: lb.name, logo_url: null, country: lb.country, matches_played: lb.matches_played, wins: lb.wins, losses: lb.losses, win_pct: lb.win_pct };
    });
  }
  if (seg[0] === 'regions' && seg[2] === 'teams-leaderboard') {
    const region = seg[1];
    const pool = region === 'all' ? TEAM_DEFS : TEAM_DEFS.filter((t) => t.region === region);
    return (pool.length ? pool : TEAM_DEFS).map((t, i) => leaderboardTeam(t.id, i));
  }
  if (seg[0] === 'teams' && seg.length === 2) {
    const t = teamById(Number(seg[1]));
    if (!t) return undefined;
    const roster = PLAYERS.filter((p) => p.teamId === t.id);
    return {
      id: t.id, name: t.name, n_matches: 24, n_wins: 15, match_win_rate: 62.5,
      map_wins: 34, map_total: 55, map_win_rate: 61.8,
      roster: roster.map((p) => ({ id: p.id, name: p.name })),
      recent_matches: [], per_map: [],
    };
  }

  // predict
  if (path === '/predict' && method === 'POST') {
    const a = teamById(body.team_a_id);
    const b = teamById(body.team_b_id);
    const pA = 0.5 + (teamStrength(body.team_a_id) - teamStrength(body.team_b_id)) * 1.6;
    return buildPrediction(a?.name || 'Team A', b?.name || 'Team B', pA, body.best_of || 3);
  }
  if (path === '/predict/fantasy' && method === 'POST') {
    const avg = (names: string[]) => {
      const ps = names.map((n) => PLAYERS.find((p) => p.name === n)).filter(Boolean) as MockPlayer[];
      return ps.length ? ps.reduce((s, p) => s + p.rating, 0) / ps.length : 1.0;
    };
    const pA = 0.5 + (avg(body.team_a_players || []) - avg(body.team_b_players || [])) * 1.8;
    return buildPrediction('Team A', 'Team B', pA, body.best_of || 3);
  }

  // explain
  if (seg[0] === 'explain') {
    const m = matchById(Number(seg[1]));
    const winner = m ? (m.score_a > m.score_b ? teamById(m.a)!.name : teamById(m.b)!.name) : 'the winner';
    const loser = m ? (m.score_a > m.score_b ? teamById(m.b)!.name : teamById(m.a)!.name) : 'the loser';
    return {
      summary: `${winner} controlled the tempo against ${loser}, converting strong mid-round reads into a decisive series. (Sample analysis.)`,
      key_factors: ['Superior first-blood trades on attack', 'Better retake conversions in clutch rounds', 'Map-pool advantage on the decider'],
      standout_players: [`${winner} duelist popped off with a 1.35 rating`, 'Controller anchored every post-plant'],
      underperformers: [`${loser} initiator struggled to get value from utility`],
    };
  }

  // pick'em
  if (seg[0] === 'pickem' && seg[1] === 'events' && seg[3] === 'teams') {
    return TEAM_DEFS.map((t) => ({ id: t.id, name: t.name }));
  }
  if (path === '/pickem/forecast' && method === 'POST') {
    const ids: number[] = body.team_ids || [];
    const strengths = ids.map((id) => ({ id, s: Math.exp(teamStrength(id) * 6) }));
    const total = strengths.reduce((a, x) => a + x.s, 0) || 1;
    const teams = strengths
      .map(({ id, s }) => {
        const t = teamById(id);
        const champ = s / total;
        return {
          team_id: id,
          team_name: t?.name || `Team ${id}`,
          champion_prob: r2(champ),
          expected_wins: r2(champ * (ids.length - 1) * 1.5),
          win_rate: r2(0.4 + champ),
          avg_win_prob: r2(0.45 + champ * 0.4),
        };
      })
      .sort((a, b) => b.champion_prob - a.champion_prob);
    return {
      format: 'round_robin',
      best_of: body.best_of || 3,
      n_sims: 20000,
      n_teams: ids.length,
      teams,
      unavailable: [],
      note: 'Sample round-robin forecast (offline demo data).',
    };
  }

  // meta
  if (path === '/meta/maps') return MAP_POOL;
  if (path === '/meta/agents') {
    const agents = ['Jett', 'Raze', 'Sova', 'Omen', 'Killjoy', 'Cypher', 'KAY/O', 'Fade', 'Neon', 'Gekko', 'Viper', 'Breach'];
    const picks = agents.map((a, i) => 400 - i * 25 - Math.round(rng(i * 2) * 30));
    const total = picks.reduce((s, x) => s + x, 0);
    return agents.map((agent, i) => ({
      agent,
      picks: picks[i],
      pick_rate: r2((picks[i] / total) * 100),
      win_rate: r2(46 + rng(i * 3 + 1) * 10),
      avg_rating: r2(1.0 + (rng(i * 5) - 0.5) * 0.2),
      avg_acs: Math.round(200 + rng(i * 7) * 60),
    }));
  }

  // depth
  if (seg[0] === 'depth' && seg[3] === 'players' && seg.length === 5) {
    return buildDepthAnalysis(Number(seg[2]), Number(seg[4]));
  }
  if (seg[0] === 'depth' && seg[3] === 'players') {
    // players in this sample event = everyone
    return PLAYERS.map((p) => ({ id: p.id, name: p.name, n_maps: 12 }));
  }

  // live
  if (path === '/live/status') {
    return { enabled: true, interval_minutes: 120, status: 'ok', last_run: MATCHES[MATCHES.length - 1].datetime, last_inserted: 3, next_run: null };
  }
  if (path === '/live/refresh') {
    return { inserted: 0, ran_at: MATCHES[MATCHES.length - 1].datetime };
  }

  return undefined;
}
