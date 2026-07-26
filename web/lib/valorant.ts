// Client-side helpers for pulling official Valorant art from the free
// community CDN at valorant-api.com. Every call is cached at module scope and
// fails soft (returns empty), so the UI degrades gracefully to its own styling
// when offline or blocked — nothing ever renders a broken image.

export interface ValAgent {
  name: string;
  role: string;
  icon: string; // square display icon
  portrait: string; // tall full-body portrait (transparent PNG)
  gradient: string[]; // role/agent gradient hex colors
}

const MAPS_URL = 'https://valorant-api.com/v1/maps';
const AGENTS_URL = 'https://valorant-api.com/v1/agents?isPlayableCharacter=true';

let mapsPromise: Promise<Record<string, string>> | null = null;

/** Returns a `{ mapName: splashImageUrl }` lookup. Empty object on failure. */
export function getMapArt(): Promise<Record<string, string>> {
  if (!mapsPromise) {
    mapsPromise = fetch(MAPS_URL)
      .then((r) => r.json())
      .then((j) => {
        const out: Record<string, string> = {};
        for (const m of j?.data ?? []) {
          if (m?.displayName && m?.splash) out[m.displayName] = m.splash;
        }
        return out;
      })
      .catch(() => ({}));
  }
  return mapsPromise;
}

let agentsPromise: Promise<ValAgent[]> | null = null;

/** Returns the playable agent roster with art. Empty array on failure. */
export function getAgents(): Promise<ValAgent[]> {
  if (!agentsPromise) {
    agentsPromise = fetch(AGENTS_URL)
      .then((r) => r.json())
      .then((j) =>
        (j?.data ?? [])
          .map((a: any) => ({
            name: a.displayName as string,
            role: a.role?.displayName ?? '',
            icon: a.displayIcon as string,
            portrait: a.fullPortrait as string,
            gradient: (a.backgroundGradientColors ?? []).map((c: string) =>
              c.startsWith('#') ? c : `#${c}`,
            ),
          }))
          .filter((a: ValAgent) => a.portrait && a.name),
      )
      .catch(() => [] as ValAgent[]);
  }
  return agentsPromise;
}
