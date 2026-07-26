'use client';

import { useEffect, useState } from 'react';
import { motion, useScroll, useSpring } from 'framer-motion';

/**
 * Decorative Valorant-HUD rails that live in the left/right page gutters on
 * wide screens. Corner brackets, a tick ruler, vertical labels, a live clock
 * and a scroll-progress bar. Purely cosmetic: aria-hidden, no pointer events,
 * and hidden entirely below ~1440px where there is no gutter to fill.
 */

function CornerBracket({ corner }: { corner: 'tl' | 'tr' | 'bl' | 'br' }) {
  const sides = {
    tl: 'border-t border-l',
    tr: 'border-t border-r',
    bl: 'border-b border-l',
    br: 'border-b border-r',
  }[corner];
  return <div className={`w-3 h-3 border-border-strong ${sides}`} />;
}

function TickRuler() {
  return (
    <div className="flex flex-col items-center gap-[7px] py-2">
      {Array.from({ length: 14 }).map((_, i) => (
        <div
          key={i}
          className={
            i % 4 === 0
              ? 'h-px w-3 bg-border-strong'
              : 'h-px w-1.5 bg-border'
          }
        />
      ))}
    </div>
  );
}

function LiveClock() {
  const [time, setTime] = useState('--:--:--');
  useEffect(() => {
    const tick = () =>
      setTime(
        new Date().toLocaleTimeString('en-GB', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        }),
      );
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);
  return (
    <span
      className="font-mono text-[0.6rem] tracking-widest text-ink-dim tabular"
      style={{ writingMode: 'vertical-rl' }}
    >
      {time}
    </span>
  );
}

export function HudRails() {
  const { scrollYProgress } = useScroll();
  const progress = useSpring(scrollYProgress, { stiffness: 120, damping: 30 });

  return (
    <div aria-hidden className="pointer-events-none select-none">
      {/* LEFT RAIL */}
      <div className="hidden min-[1440px]:flex fixed left-4 top-20 bottom-8 z-40 w-8 flex-col items-center justify-between">
        <div className="flex flex-col items-center gap-2">
          <CornerBracket corner="tl" />
          <span
            className="font-mono text-[0.6rem] uppercase tracking-[0.35em] text-ink-dim mt-2"
            style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
          >
            VLR // ANALYTICS
          </span>
        </div>

        <TickRuler />

        <div className="flex flex-col items-center gap-3">
          <LiveClock />
          <span className="relative flex w-1.5 h-1.5">
            <span className="absolute inline-flex w-full h-full rounded-full bg-accent opacity-75 animate-ping" />
            <span className="relative inline-flex w-1.5 h-1.5 rounded-full bg-accent" />
          </span>
          <CornerBracket corner="bl" />
        </div>
      </div>

      {/* RIGHT RAIL */}
      <div className="hidden min-[1440px]:flex fixed right-4 top-20 bottom-8 z-40 w-8 flex-col items-center justify-between">
        <div className="flex flex-col items-center gap-2">
          <CornerBracket corner="tr" />
          <span
            className="font-mono text-[0.6rem] uppercase tracking-[0.35em] text-ink-dim mt-2"
            style={{ writingMode: 'vertical-rl' }}
          >
            MATCH INTELLIGENCE
          </span>
        </div>

        {/* Scroll progress track */}
        <div className="relative flex-1 my-4 w-px bg-border/60 overflow-hidden rounded-full">
          <motion.div
            className="absolute top-0 left-0 w-full bg-gradient-to-b from-accent to-accent/20 origin-top"
            style={{ height: '100%', scaleY: progress }}
          />
        </div>

        <div className="flex flex-col items-center gap-3">
          <span
            className="font-mono text-[0.6rem] uppercase tracking-[0.3em] text-ink-dim"
            style={{ writingMode: 'vertical-rl' }}
          >
            v1.0
          </span>
          <CornerBracket corner="br" />
        </div>
      </div>
    </div>
  );
}
