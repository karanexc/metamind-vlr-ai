'use client';

import { useEffect, useState } from 'react';
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion';

interface CounterProps {
  value: number;
  duration?: number;
  format?: (n: number) => string;
  className?: string;
}

export function Counter({
  value,
  duration = 1.2,
  format = (n) => new Intl.NumberFormat('en-US').format(Math.round(n)),
  className,
}: CounterProps) {
  const motionValue = useMotionValue(0);
  const spring = useSpring(motionValue, {
    duration: duration * 1000,
    stiffness: 50,
    damping: 20,
  });
  const display = useTransform(spring, (latest) => format(latest));
  const [text, setText] = useState(format(0));

  useEffect(() => {
    motionValue.set(value);
    return display.on('change', (v) => setText(v));
  }, [value, motionValue, display]);

  return <motion.span className={className}>{text}</motion.span>;
}
