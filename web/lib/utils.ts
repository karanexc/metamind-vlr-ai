import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(iso: string | null | undefined, format: 'short' | 'long' = 'short'): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (format === 'long') {
    return d.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  }
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function formatNumber(n: number): string {
  return new Intl.NumberFormat('en-US').format(n);
}

/**
 * Convert an ISO-2 country code (e.g. 'us', 'kr') into a Unicode flag emoji.
 * Returns null if the code is missing or malformed — caller can fall back to
 * showing nothing.
 */
export function countryFlag(code: string | null | undefined): string | null {
  if (!code || code.length !== 2 || !/^[a-z]{2}$/i.test(code)) return null;
  // Flag emojis are formed by mapping each ASCII letter to its
  // Regional Indicator Symbol (U+1F1E6 = 🇦 for 'A')
  const upper = code.toUpperCase();
  const codepoints = [...upper].map(c => 0x1F1A5 + c.charCodeAt(0));
  return String.fromCodePoint(...codepoints);
}

/**
 * Stable color from a string — used as a fallback when a player photo is
 * missing. Same input always produces the same color so the UI feels stable.
 */
export function avatarColor(name: string): string {
  const colors = [
    '#7C3AED', '#0EA5E9', '#10B981', '#F59E0B',
    '#EC4899', '#EF4444', '#6366F1', '#14B8A6',
  ];
  if (!name) return colors[0];
  return colors[name.charCodeAt(0) % colors.length];
}

export function initials(name: string): string {
  if (!name) return '?';
  return name.slice(0, 2).toUpperCase();
}

/**
 * Route a vlr image-CDN URL through our own same-origin /api/img proxy.
 *
 * Team logos and player photos live on owcdn.net (behind CloudFront), which
 * 403s hotlinked <img> loads coming from another origin. The block is on the
 * browser's Sec-Fetch-Dest/Sec-Fetch-Site headers — set by the browser and
 * impossible to strip from the page — so the only fix is to fetch the image
 * server-side. The proxy does that and re-serves it from our origin.
 *
 * Only owcdn URLs are rewritten; game assets (valorant-api.com), relative
 * paths and data: URLs are returned untouched.
 */
export function proxyImage(url?: string | null): string | undefined {
  if (!url) return undefined;
  if (/^https?:\/\/([a-z0-9-]+\.)*owcdn\.net\//i.test(url)) {
    return `/api/img?u=${encodeURIComponent(url)}`;
  }
  return url;
}
