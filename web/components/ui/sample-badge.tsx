'use client';

import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Shows a small fixed "Sample data" pill when the backend is unreachable, so
 * it's clear the app is running on the built-in offline sample tournament.
 * Hidden entirely once a real backend answers /health.
 */
export function SampleBadge() {
  const [sample, setSample] = useState(false);

  useEffect(() => {
    let alive = true;
    fetch(`${API}/health`, { cache: 'no-store' })
      .then((r) => {
        if (alive) setSample(!r.ok);
      })
      .catch(() => {
        if (alive) setSample(true);
      });
    return () => {
      alive = false;
    };
  }, []);

  if (!sample) return null;

  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-[60] inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-warning/10 border border-warning/30 text-warning text-xs backdrop-blur-md">
      <span className="relative flex w-1.5 h-1.5">
        <span className="absolute inline-flex w-full h-full rounded-full bg-warning opacity-75 animate-ping" />
        <span className="relative inline-flex w-1.5 h-1.5 rounded-full bg-warning" />
      </span>
      Sample data — backend not connected
    </div>
  );
}
