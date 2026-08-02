// vlr.gg's rankings regions — the single source of truth for the UI.
// Mirrors src/vlr/regions.py so the app's regional views match vlr.gg exactly.

export interface VlrRegion {
  slug: string;
  label: string;
  short: string;
}

export const VLR_REGIONS: VlrRegion[] = [
  { slug: 'north-america', label: 'North America', short: 'NA' },
  { slug: 'europe', label: 'Europe', short: 'EU' },
  { slug: 'brazil', label: 'Brazil', short: 'BR' },
  { slug: 'asia-pacific', label: 'Asia-Pacific', short: 'AP' },
  { slug: 'korea', label: 'Korea', short: 'KR' },
  { slug: 'china', label: 'China', short: 'CN' },
  { slug: 'japan', label: 'Japan', short: 'JP' },
  { slug: 'la-s', label: 'LA-S', short: 'LAS' },
  { slug: 'la-n', label: 'LA-N', short: 'LAN' },
  { slug: 'oceania', label: 'Oceania', short: 'OCE' },
  { slug: 'mena', label: 'MENA', short: 'MN' },
  { slug: 'gc', label: 'Game Changers', short: 'GC' },
  { slug: 'collegiate', label: 'Collegiate', short: 'CG' },
];

// Human label for a region slug (falls back to the slug itself).
export function regionLabel(slug: string | null | undefined): string {
  if (!slug) return '—';
  return VLR_REGIONS.find((r) => r.slug === slug)?.label ?? slug;
}
