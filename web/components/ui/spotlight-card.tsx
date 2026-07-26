'use client';

import { useRef, type ReactNode } from 'react';
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion';
import { cn } from '@/lib/utils';

/**
 * Wraps a card to give it two cursor-driven effects:
 *  - a soft accent "spotlight" glow that follows the pointer, and
 *  - a subtle 3D tilt toward the cursor.
 * The glow overlay is pointer-events-none so wrapped links/buttons stay clickable.
 */
export function SpotlightCard({
  children,
  className,
  radius = 240,
  tilt = 6,
}: {
  children: ReactNode;
  className?: string;
  radius?: number;
  tilt?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);

  // Normalised pointer position (0..1) within the card.
  const px = useMotionValue(0.5);
  const py = useMotionValue(0.5);
  // Raw pointer position (px) for the glow center.
  const gx = useMotionValue(-radius);
  const gy = useMotionValue(-radius);

  const rotateX = useSpring(useTransform(py, [0, 1], [tilt, -tilt]), { stiffness: 200, damping: 20 });
  const rotateY = useSpring(useTransform(px, [0, 1], [-tilt, tilt]), { stiffness: 200, damping: 20 });

  const glow = useTransform(
    [gx, gy],
    ([x, y]) =>
      `radial-gradient(${radius}px circle at ${x}px ${y}px, rgba(250,68,84,0.14), transparent 70%)`,
  );

  function onMove(e: React.MouseEvent<HTMLDivElement>) {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    px.set((e.clientX - r.left) / r.width);
    py.set((e.clientY - r.top) / r.height);
    gx.set(e.clientX - r.left);
    gy.set(e.clientY - r.top);
  }

  function onLeave() {
    px.set(0.5);
    py.set(0.5);
    gx.set(-radius);
    gy.set(-radius);
  }

  return (
    <motion.div
      ref={ref}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      style={{ rotateX, rotateY, transformPerspective: 900 }}
      className={cn('relative', className)}
    >
      <motion.div
        aria-hidden
        style={{ background: glow }}
        className="pointer-events-none absolute inset-0 rounded-2xl z-20"
      />
      {children}
    </motion.div>
  );
}
