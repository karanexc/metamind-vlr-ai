// Single source of truth for talking to the backend.

import { resolveMock } from './mock-data';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiError extends Error {
  constructor(public status: number, public statusText: string, public body?: unknown) {
    super(`API error ${status}: ${statusText}`);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(init?.headers || {}),
      },
    });
  } catch (netErr) {
    // Backend unreachable (e.g. no server running) → offline sample data.
    const mock = resolveMock(path, init);
    if (mock !== undefined) return mock as T;
    throw netErr;
  }

  if (!res.ok) {
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      body = await res.text();
    }
    throw new ApiError(res.status, res.statusText, body);
  }
  return res.json() as Promise<T>;
}

// --- Types matching backend Pydantic schemas ----------------------------

export interface DatabaseStats {
  matches: number;
  real_matches: number;
  teams: number;
  events: number;
  players: number;
  maps: number;
  player_rows: number;
  earliest_match: string | null;
  latest_match: string | null;
}

export interface TeamListItem {
  id: number;
  name: string;
  n_matches: number;
  logo_url?: string | null;
}

export interface TeamSummary {
  id: number;
  name: string;
  n_matches: number;
  n_wins: number;
  match_win_rate: number;
  map_wins: number;
  map_total: number;
  map_win_rate: number;
  roster: { id: number; name: string }[];
  recent_matches: any[];
  per_map: { map: string; played: number; wins: number; win_rate: number }[];
}

export interface PlayerListItem {
  id: number;
  name: string;
  n_maps: number;
}

export interface PlayerSummary {
  id: number;
  name: string;
  image_url?: string | null;
  country?: string | null;
  n_maps: number;
  avg_rating: number;
  avg_acs: number;
  avg_kast: number;
  avg_adr: number;
  avg_hs: number;
  total_kills: number;
  total_deaths: number;
  per_agent: any[];
  per_map: any[];
  recent_form: any[];
}

export interface MatchListItem {
  match_id: number;
  team_a: string;
  team_b: string;
  score_a: number;
  score_b: number;
  best_of: number | null;
  stage: string | null;
  datetime: string | null;
  event: string | null;
}

export interface PlayerMapStat {
  player: string;
  team: string | null;
  agent: string | null;
  rating: number | null;
  acs: number | null;
  k: number | null;
  d: number | null;
  a: number | null;
  kast: number | null;
  adr: number | null;
  hs: number | null;
}

export interface MapDetail {
  index: number;
  name: string;
  score_a: number | null;
  score_b: number | null;
  picked_by: string | null;
  stats: PlayerMapStat[];
}

export interface MatchDetail {
  match_id: number;
  team_a_name: string;
  team_b_name: string;
  team_a_id: number | null;
  team_b_id: number | null;
  score_a: number | null;
  score_b: number | null;
  best_of: number | null;
  stage: string | null;
  patch: string | null;
  datetime: string | null;
  event_name: string | null;
  event_id: number | null;
  maps: MapDetail[];
}

export interface MapPrediction {
  map_name: string;
  prob_a: number;
  prob_b: number;
  confidence: string;
}

export interface MatchPrediction {
  team_a_name: string;
  team_b_name: string;
  prob_a: number;
  prob_b: number;
  predicted_score_a: number;
  predicted_score_b: number;
  best_of: number;
  map_predictions: MapPrediction[];
  confidence: string;
  note: string;
  cross_tier_warning: string | null;
}

export interface LossAnalysis {
  summary: string;
  key_factors: string[];
  standout_players: string[];
  underperformers: string[];
}

export interface TopPlayer {
  player: string;
  n_maps: number;
  avg_metric: number;
}

export interface LiveStatus {
  enabled: boolean;
  interval_minutes: number;
  status: string;
  running: boolean;
  last_run: string | null;
  last_result: Record<string, unknown> | null;
  next_run: string | null;
}

export interface RefreshResult {
  status: string;
  started: boolean;
}

export interface EventTeam {
  id: number;
  name: string;
}

export interface PickemForecastItem {
  team_id: number;
  team_name: string;
  champion_prob: number;
  expected_wins: number;
  win_rate: number;
  avg_win_prob: number;
}

export interface PickemForecast {
  format: string;
  best_of: number;
  n_sims: number;
  n_teams: number;
  teams: PickemForecastItem[];
  unavailable: string[];
  note: string;
}

export interface AgentMetaItem {
  agent: string;
  picks: number;
  pick_rate: number;
  win_rate: number;
  avg_rating: number;
  avg_acs: number;
}

export interface EventPlayer {
  id: number;
  name: string;
  n_maps: number;
}

export interface PlayerEventMap {
  index: number;
  map_name: string | null;
  opponent: string | null;
  agent: string | null;
  rating: number;
  acs: number;
  kills: number;
  deaths: number;
  kast: number;
  adr: number;
  hs: number;
  won: boolean;
  stage: string | null;
}

export interface PlayerEventAgent {
  agent: string;
  maps: number;
  avg_rating: number;
  avg_acs: number;
}

export interface PlayerEventAnalysis {
  player_id: number;
  player_name: string;
  event_id: number;
  event_name: string;
  n_maps: number;
  map_wins: number;
  map_win_rate: number;
  avg_rating: number;
  avg_acs: number;
  avg_kast: number;
  avg_adr: number;
  avg_hs: number;
  total_kills: number;
  total_deaths: number;
  series: PlayerEventMap[];
  per_agent: PlayerEventAgent[];
}

export interface RegionalTeam {
  id: number;
  name: string;
  logo_url: string | null;
  country: string | null;
  matches_played: number;
  wins: number;
  losses: number;
  win_pct: number;
  vlr_rating?: number | null;
  vlr_rank?: number | null;
}

export interface TeamRosterPlayer {
  id: number;
  name: string;
  image_url: string | null;
  country: string | null;
  real_name: string | null;
  last_played: string | null;
}

export interface LeaderboardTeam extends RegionalTeam {
  region: string | null;
  roster: {
    id: number;
    name: string;
    image_url: string | null;
    country: string | null;
  }[];
}

// VCT ability telemetry (historical 2022-24 module)
export interface AbilitySummary {
  games: number;
  players: number;
  agents: number;
  year_min: number | null;
  year_max: number | null;
  tiers: string[];
}

export interface AbilityAgent {
  agent: string;
  role: string | null;
  games: number;
  ability_casts_per_round: number;
  ults_per_game: number;
  ult_per_round: number;
  kd: number;
  win_rate: number;
}

export interface AbilityPlayer {
  player_name: string;
  team_tag: string | null;
  games: number;
  ability_casts_per_round: number;
  ults_per_game: number;
  kd: number;
  win_rate: number;
  found?: boolean;
  agents?: { agent: string; games: number; ults: number }[];
}

export interface AbilityImpact {
  rounds: number;
  utility_edge_win_rate: number;
  ult_win_rate: number;
  util_diff_buckets: { bucket: string; n: number; win_rate: number }[];
  ult_buckets: { ults: string; n: number; win_rate: number }[];
  by_condition: { condition: string; rounds: number; avg_util: number; avg_ults: number }[];
}

export interface MapImpact {
  map: string;
  games: number;
  rounds: number;
  utility_edge_win_rate: number;
  ult_win_rate: number;
  avg_util_per_round: number;
}

export interface VctGameListItem {
  game_id: string;
  map: string | null;
  tier: string;
  year: number;
  team_a_tag: string | null;
  team_b_tag: string | null;
  winner_tag: string | null;
  score_a: number;
  score_b: number;
  played_at: string | null;
  total_rounds: number | null;
}

export interface VctTimelineEvent {
  t: number | null;
  k: string; // ability | ult | kill | plant | defuse
  team: number | null; // 0 = team A, 1 = team B
  slot?: string;
}

export interface VctRoundDetail {
  round_number: number;
  winner_tag: string | null;
  win_condition: string | null;
  attacker_tag: string | null;
  winner_util: number;
  loser_util: number;
  winner_ults: number;
  loser_ults: number;
  opening_kill_tag: string | null;
  spike_planted: boolean;
  spike_defused: boolean;
  is_pistol: boolean;
  is_map_point: boolean;
  is_clutch: boolean;
  timeline: VctTimelineEvent[];
}

export interface VctMatchPlayer {
  handle: string;
  player_name: string;
  team_tag: string | null;
  agent: string | null;
  role: string | null;
  ability_casts: number;
  ult_casts: number;
  kills: number;
  deaths: number;
  won: boolean;
}

export interface VctMatchTeam {
  team_tag: string | null;
  util: number;
  ults: number;
  kills: number;
  won: boolean;
}

export interface VctMatchHighlights {
  most_utility: { player_name: string; agent: string | null; value: number } | null;
  most_ults: { player_name: string; agent: string | null; value: number } | null;
  top_fragger: { player_name: string; agent: string | null; value: number } | null;
  utility_edge_rounds: number;
  total_rounds: number;
  decisive_round: number | null;
}

export interface VctGameRounds {
  found: boolean;
  game?: {
    game_id: string;
    map: string | null;
    tier: string;
    year: number;
    team_a_tag: string | null;
    team_b_tag: string | null;
    winner_tag: string | null;
    total_rounds: number | null;
    played_at: string | null;
  };
  players?: VctMatchPlayer[];
  teams?: VctMatchTeam[];
  highlights?: VctMatchHighlights;
  rounds?: VctRoundDetail[];
}

// --- API methods --------------------------------------------------------

export const api = {
  stats: () => request<DatabaseStats>('/api/v1/stats'),

  teams: (minMatches = 5) =>
    request<TeamListItem[]>(`/api/v1/teams?min_matches=${minMatches}`),
  team: (id: number) => request<TeamSummary>(`/api/v1/teams/${id}`),

  players: (minMaps = 10) =>
    request<PlayerListItem[]>(`/api/v1/players?min_maps=${minMaps}`),
  player: (id: number) => request<PlayerSummary>(`/api/v1/players/${id}`),
  topPlayers: (metric: string, minMaps = 30, limit = 10) =>
    request<TopPlayer[]>(
      `/api/v1/players/top/${metric}?min_maps=${minMaps}&limit=${limit}`,
    ),

  recentMatches: (limit = 20) =>
    request<MatchListItem[]>(`/api/v1/matches/recent?limit=${limit}`),
  matchesByTier: (tier: string, limit = 60) =>
    request<MatchListItem[]>(`/api/v1/matches/by-tier/${tier}?limit=${limit}`),
  match: (id: number) => request<MatchDetail>(`/api/v1/matches/${id}`),
  events: () => request<{ id: number; name: string }[]>('/api/v1/events'),

  regionalTopTeams: (region: string, limit = 5) =>
    request<RegionalTeam[]>(
      `/api/v1/regions/${region}/top-teams?limit=${limit}`,
    ),
  teamRoster: (teamId: number) =>
    request<TeamRosterPlayer[]>(`/api/v1/teams/${teamId}/roster`),
  teamsLeaderboard: (region: string, limit = 50) =>
    request<LeaderboardTeam[]>(
      `/api/v1/regions/${region}/teams-leaderboard?limit=${limit}`,
    ),

  predict: (teamAId: number, teamBId: number, bestOf: number) =>
    request<MatchPrediction>('/api/v1/predict', {
      method: 'POST',
      body: JSON.stringify({
        team_a_id: teamAId,
        team_b_id: teamBId,
        best_of: bestOf,
      }),
    }),

  predictFantasy: (teamA: string[], teamB: string[], bestOf: number) =>
    request<MatchPrediction>('/api/v1/predict/fantasy', {
      method: 'POST',
      body: JSON.stringify({
        team_a_players: teamA,
        team_b_players: teamB,
        best_of: bestOf,
      }),
    }),

  explain: (matchId: number, regenerate = false) =>
    request<LossAnalysis>(
      `/api/v1/explain/${matchId}${regenerate ? '?regenerate=true' : ''}`,
    ),

  // Live scrape
  liveStatus: () => request<LiveStatus>('/api/v1/live/status'),
  refresh: () => request<RefreshResult>('/api/v1/live/refresh', { method: 'POST' }),

  // Pick'em
  eventTeams: (eventId: number) =>
    request<EventTeam[]>(`/api/v1/pickem/events/${eventId}/teams`),
  pickemForecast: (teamIds: number[], bestOf: number) =>
    request<PickemForecast>('/api/v1/pickem/forecast', {
      method: 'POST',
      body: JSON.stringify({ team_ids: teamIds, best_of: bestOf }),
    }),

  // Agent meta
  metaMaps: () => request<string[]>('/api/v1/meta/maps'),
  metaAgents: (map?: string, minPicks = 20) =>
    request<AgentMetaItem[]>(
      `/api/v1/meta/agents?min_picks=${minPicks}${map ? `&map=${encodeURIComponent(map)}` : ''}`,
    ),

  // Player depth analysis
  eventPlayers: (eventId: number) =>
    request<EventPlayer[]>(`/api/v1/depth/events/${eventId}/players`),
  playerEventAnalysis: (eventId: number, playerId: number) =>
    request<PlayerEventAnalysis>(`/api/v1/depth/events/${eventId}/players/${playerId}`),

  // VCT ability telemetry (historical 2022-24)
  abilitiesSummary: () => request<AbilitySummary>('/api/v1/abilities/summary'),
  abilitiesAgents: (minGames = 5, map = '') =>
    request<AbilityAgent[]>(
      `/api/v1/abilities/agents?min_games=${minGames}${map ? `&map=${encodeURIComponent(map)}` : ''}`,
    ),
  abilitiesPlayers: (search = '', limit = 50) =>
    request<AbilityPlayer[]>(
      `/api/v1/abilities/players?search=${encodeURIComponent(search)}&limit=${limit}`,
    ),
  abilitiesPlayer: (name: string) =>
    request<AbilityPlayer>(`/api/v1/abilities/players/${encodeURIComponent(name)}`),
  abilitiesImpact: (map = '') =>
    request<AbilityImpact>(
      `/api/v1/abilities/impact${map ? `?map=${encodeURIComponent(map)}` : ''}`,
    ),
  abilitiesImpactMaps: () => request<MapImpact[]>('/api/v1/abilities/impact/maps'),
  abilitiesGames: (opts: { map?: string; search?: string; limit?: number } = {}) =>
    request<VctGameListItem[]>(
      `/api/v1/abilities/games?map=${encodeURIComponent(opts.map ?? '')}&search=${encodeURIComponent(
        opts.search ?? '',
      )}&limit=${opts.limit ?? 60}`,
    ),
  abilitiesGameRounds: (gameId: string) =>
    request<VctGameRounds>(`/api/v1/abilities/games/${encodeURIComponent(gameId)}/rounds`),
};
