// Single source of truth for talking to the backend.

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiError extends Error {
  constructor(public status: number, public statusText: string, public body?: unknown) {
    super(`API error ${status}: ${statusText}`);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
  });

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
  match: (id: number) => request<MatchDetail>(`/api/v1/matches/${id}`),
  events: () => request<{ id: number; name: string }[]>('/api/v1/events'),

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
};
