'use client';

import { useEffect, useRef } from 'react';

/**
 * The "alive" background layer, drawn on one canvas:
 *   - an always-visible faint dot grid
 *   - dots that brighten + grow in a radius around the cursor, with a spotlight
 *   - embers drifting slowly upward like spike sparks
 *   - occasional diagonal tracer streaks
 *
 * Valorant-red palette, decorative only (no pointer events, aria-hidden),
 * respects prefers-reduced-motion, and scales particle counts to the viewport.
 */
export function TacticalCanvas() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvasEl = ref.current;
    if (!canvasEl) return;
    const context = canvasEl.getContext('2d');
    if (!context) return;
    // Non-null aliases so nested draw/resize closures keep the narrowed type.
    const canvas: HTMLCanvasElement = canvasEl;
    const ctx: CanvasRenderingContext2D = context;

    const reduce =
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const GRID = 32;
    const SPOT = 170;
    const SPOT2 = SPOT * SPOT;

    let width = 0;
    let height = 0;
    const mouse = { x: -9999, y: -9999, active: false };

    function resize() {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = width + 'px';
      canvas.style.height = height + 'px';
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();

    // --- Embers ----------------------------------------------------------
    type Ember = { x: number; y: number; vx: number; vy: number; r: number; g: number; life: number; max: number };
    const emberCount = reduce ? 0 : Math.max(28, Math.min(95, Math.floor((width * height) / 18000)));
    const embers: Ember[] = [];
    const mkEmber = (seed: boolean): Ember => ({
      x: Math.random() * width,
      y: seed ? Math.random() * height : height + 8,
      vx: (Math.random() - 0.5) * 0.25,
      vy: -(0.2 + Math.random() * 0.7),
      r: 0.9 + Math.random() * 2.2,
      g: 70 + Math.floor(Math.random() * 100),
      life: 0,
      max: 240 + Math.random() * 460,
    });
    for (let i = 0; i < emberCount; i++) embers.push(mkEmber(true));

    // --- Meteors / tracers ----------------------------------------------
    type Meteor = { x: number; y: number; len: number; speed: number; angle: number };
    const meteors: Meteor[] = [];
    const mkMeteor = () => {
      const angle = Math.PI * 0.22 + (Math.random() - 0.5) * 0.18;
      meteors.push({
        x: Math.random() * width * 0.8 - width * 0.1,
        y: -30 - Math.random() * 120,
        len: 160 + Math.random() * 200,
        speed: 7 + Math.random() * 7,
        angle,
      });
    };

    let raf = 0;

    function draw() {
      ctx.clearRect(0, 0, width, height);

      // Always-on faint dot grid (single fill style → cheap)
      ctx.fillStyle = 'rgba(250,68,84,0.16)';
      for (let x = GRID / 2; x < width; x += GRID) {
        for (let y = GRID / 2; y < height; y += GRID) {
          ctx.fillRect(x, y, 1.6, 1.6);
        }
      }

      // Brighter dots + spotlight around the cursor
      if (mouse.active) {
        const x0 = Math.floor((mouse.x - SPOT) / GRID) * GRID;
        const y0 = Math.floor((mouse.y - SPOT) / GRID) * GRID;
        for (let x = x0; x <= mouse.x + SPOT; x += GRID) {
          for (let y = y0; y <= mouse.y + SPOT; y += GRID) {
            const dx = x - mouse.x;
            const dy = y - mouse.y;
            const d2 = dx * dx + dy * dy;
            if (d2 > SPOT2) continue;
            const f = 1 - d2 / SPOT2;
            ctx.fillStyle = `rgba(255,${90 - Math.floor(f * 30)},95,${(0.15 + f * 0.7).toFixed(3)})`;
            const s = 1.3 + f * 2.6;
            ctx.fillRect(x - s / 2, y - s / 2, s, s);
          }
        }
        const g = ctx.createRadialGradient(mouse.x, mouse.y, 0, mouse.x, mouse.y, SPOT + 60);
        g.addColorStop(0, 'rgba(250,68,84,0.12)');
        g.addColorStop(1, 'rgba(250,68,84,0)');
        ctx.fillStyle = g;
        ctx.fillRect(mouse.x - SPOT - 60, mouse.y - SPOT - 60, (SPOT + 60) * 2, (SPOT + 60) * 2);
      }

      if (!reduce) {
        // Embers
        for (const p of embers) {
          p.x += p.vx;
          p.y += p.vy;
          p.life++;
          if (p.y < -10 || p.life > p.max) Object.assign(p, mkEmber(false));
          const a = Math.max(0, 0.6 * (1 - p.life / p.max));
          ctx.fillStyle = `rgba(255,${p.g},60,${a.toFixed(3)})`;
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
          ctx.fill();
        }

        // Meteors
        if (Math.random() < 0.018 && meteors.length < 3) mkMeteor();
        for (let i = meteors.length - 1; i >= 0; i--) {
          const m = meteors[i];
          m.x += Math.cos(m.angle) * m.speed;
          m.y += Math.sin(m.angle) * m.speed;
          const tx = m.x - Math.cos(m.angle) * m.len;
          const ty = m.y - Math.sin(m.angle) * m.len;
          const grad = ctx.createLinearGradient(m.x, m.y, tx, ty);
          grad.addColorStop(0, 'rgba(255,130,120,0.6)');
          grad.addColorStop(1, 'rgba(255,130,120,0)');
          ctx.strokeStyle = grad;
          ctx.lineWidth = 1.6;
          ctx.beginPath();
          ctx.moveTo(m.x, m.y);
          ctx.lineTo(tx, ty);
          ctx.stroke();
          if (m.x > width + 80 || m.y > height + 80) meteors.splice(i, 1);
        }

        raf = requestAnimationFrame(draw);
      }
    }

    function onMove(e: MouseEvent) {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
      mouse.active = true;
      if (reduce) draw();
    }
    function onLeave() {
      mouse.active = false;
      if (reduce) draw();
    }

    window.addEventListener('resize', resize);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseout', onLeave);

    if (reduce) {
      draw();
    } else {
      raf = requestAnimationFrame(draw);
    }

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseout', onLeave);
    };
  }, []);

  return <canvas ref={ref} aria-hidden className="absolute inset-0" />;
}
