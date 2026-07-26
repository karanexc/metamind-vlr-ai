'use client';

import { motion, useReducedMotion } from 'framer-motion';

/**
 * Fixed, full-viewport decorative layer that sits behind all page content.
 * Slowly drifting accent orbs + a faint grid give every tab a sense of depth
 * and motion even when its data area is empty. Purely decorative, so it's
 * aria-hidden and ignores pointer events. Respects prefers-reduced-motion.
 */
export function AmbientBackground() {
  const reduce = useReducedMotion();

  return (
    <div
      aria-hidden
      className="fixed inset-0 -z-10 overflow-hidden pointer-events-none"
    >
      {/* Faint grid */}
      <div className="absolute inset-0 grid-bg opacity-40" />

      {/* Drifting accent orb — top left */}
      <motion.div
        className="absolute -top-[10%] left-[12%] w-[45vw] h-[45vw] max-w-[640px] max-h-[640px] rounded-full bg-accent/10 blur-[130px]"
        animate={reduce ? undefined : { x: [0, 60, -30, 0], y: [0, 40, 20, 0], scale: [1, 1.12, 0.95, 1] }}
        transition={{ duration: 28, repeat: Infinity, ease: 'easeInOut' }}
      />

      {/* Drifting cool orb — bottom right (a touch of contrast) */}
      <motion.div
        className="absolute -bottom-[15%] right-[8%] w-[40vw] h-[40vw] max-w-[560px] max-h-[560px] rounded-full bg-[#22D3EE]/[0.05] blur-[130px]"
        animate={reduce ? undefined : { x: [0, -50, 20, 0], y: [0, -30, -10, 0], scale: [1, 1.15, 1, 1] }}
        transition={{ duration: 34, repeat: Infinity, ease: 'easeInOut' }}
      />

      {/* Small drifting accent — center */}
      <motion.div
        className="absolute top-[42%] left-[52%] w-[30vw] h-[30vw] max-w-[420px] max-h-[420px] rounded-full bg-accent/[0.05] blur-[120px]"
        animate={reduce ? undefined : { x: [0, 30, -40, 0], y: [0, -40, 30, 0] }}
        transition={{ duration: 31, repeat: Infinity, ease: 'easeInOut' }}
      />

      {/* Fine film grain for texture */}
      <div className="absolute inset-0 noise-overlay opacity-70" />

      {/* Bottom vignette so content grounds into the page */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-bg/80" />
    </div>
  );
}
