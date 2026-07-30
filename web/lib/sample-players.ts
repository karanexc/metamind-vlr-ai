import type { PlayerSummary, PlayerListItem } from './api';

/**
 * A small set of well-known players with *illustrative* stats, used ONLY as an
 * offline fallback (e.g. previewing the UI with no backend running). When the
 * real API is reachable it returns live data and this is never used. Negative
 * ids guarantee no clash with real vlr.gg player ids.
 *
 * These numbers are representative, not authoritative — for demo/preview only.
 */
type Sample = Pick<
  PlayerSummary,
  | 'id' | 'name' | 'n_maps' | 'avg_rating' | 'avg_acs' | 'avg_kast'
  | 'avg_adr' | 'avg_hs' | 'total_kills' | 'total_deaths'
>;

const RAW: Sample[] = [
  { id: -1, name: 'aspas',     n_maps: 430, avg_rating: 1.22, avg_acs: 265, avg_kast: 73, avg_adr: 168, avg_hs: 24, total_kills: 7800, total_deaths: 5900 },
  { id: -2, name: 'Derke',     n_maps: 410, avg_rating: 1.15, avg_acs: 255, avg_kast: 72, avg_adr: 160, avg_hs: 30, total_kills: 7200, total_deaths: 5600 },
  { id: -3, name: 'TenZ',      n_maps: 360, avg_rating: 1.13, avg_acs: 258, avg_kast: 71, avg_adr: 162, avg_hs: 27, total_kills: 5400, total_deaths: 4300 },
  { id: -4, name: 'Chronicle', n_maps: 400, avg_rating: 1.14, avg_acs: 230, avg_kast: 76, avg_adr: 150, avg_hs: 22, total_kills: 6800, total_deaths: 5200 },
  { id: -5, name: 'Less',      n_maps: 390, avg_rating: 1.20, avg_acs: 232, avg_kast: 78, avg_adr: 148, avg_hs: 20, total_kills: 6900, total_deaths: 5000 },
  { id: -6, name: 'ZmjjKK',    n_maps: 320, avg_rating: 1.16, avg_acs: 270, avg_kast: 70, avg_adr: 170, avg_hs: 23, total_kills: 5200, total_deaths: 4200 },
  { id: -7, name: 'Demon1',    n_maps: 300, avg_rating: 1.18, avg_acs: 268, avg_kast: 72, avg_adr: 172, avg_hs: 21, total_kills: 4800, total_deaths: 3900 },
  { id: -8, name: 'Jinggg',    n_maps: 340, avg_rating: 1.13, avg_acs: 250, avg_kast: 72, avg_adr: 165, avg_hs: 33, total_kills: 5600, total_deaths: 4500 },
];

export const SAMPLE_PLAYER_LIST: PlayerListItem[] = RAW.map((p) => ({
  id: p.id,
  name: p.name,
  n_maps: p.n_maps,
}));

export const SAMPLE_PLAYER_SUMMARIES: Record<number, PlayerSummary> = Object.fromEntries(
  RAW.map((p) => [
    p.id,
    { ...p, per_agent: [], per_map: [], recent_form: [] } as PlayerSummary,
  ]),
);
