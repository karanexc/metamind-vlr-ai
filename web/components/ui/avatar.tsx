'use client';

import { useState } from 'react';
import { avatarColor, initials, countryFlag, cn } from '@/lib/utils';

interface PlayerAvatarProps {
  name: string;
  imageUrl?: string | null;
  country?: string | null;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showFlag?: boolean;
  className?: string;
}

const SIZE_CLASSES = {
  sm: 'w-8 h-8 text-[10px]',
  md: 'w-12 h-12 text-sm',
  lg: 'w-16 h-16 text-base',
  xl: 'w-24 h-24 text-2xl',
};

const FLAG_SIZE = {
  sm: 'text-[10px]',
  md: 'text-xs',
  lg: 'text-sm',
  xl: 'text-lg',
};

/**
 * Renders a player's photo if we have one, falls back to colored initials
 * if not. Country flag emoji overlays the bottom-right corner.
 *
 * `next/image` would be the canonical choice here, but vlr.gg images aren't on
 * a domain we've added to next.config.js, and the user wants minimum friction.
 * A plain <img> works fine and lets the browser handle caching.
 */
export function PlayerAvatar({
  name,
  imageUrl,
  country,
  size = 'md',
  showFlag = true,
  className,
}: PlayerAvatarProps) {
  const [imgFailed, setImgFailed] = useState(false);
  const flag = showFlag ? countryFlag(country) : null;
  const showImage = imageUrl && !imgFailed;

  return (
    <div className={cn('relative inline-block', SIZE_CLASSES[size], className)}>
      {showImage ? (
        <img
          src={imageUrl!}
          alt={name}
          className="w-full h-full rounded-full object-cover bg-bg"
          onError={() => setImgFailed(true)}
          loading="lazy"
        />
      ) : (
        <div
          className="w-full h-full rounded-full flex items-center justify-center font-bold text-white"
          style={{
            background: `linear-gradient(135deg, ${avatarColor(name)}, ${avatarColor(name)}99)`,
          }}
        >
          {initials(name)}
        </div>
      )}
      {flag && (
        <span
          className={cn(
            'absolute -bottom-0.5 -right-0.5 rounded-full bg-bg p-0.5 shadow-md leading-none',
            FLAG_SIZE[size],
          )}
        >
          {flag}
        </span>
      )}
    </div>
  );
}


/**
 * Team logo with the same image-or-fallback pattern. Logos are usually
 * square so we use rounded-md rather than rounded-full.
 */
interface TeamLogoProps {
  name: string;
  logoUrl?: string | null;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const LOGO_SIZE = {
  sm: 'w-8 h-8 text-xs',
  md: 'w-10 h-10 text-sm',
  lg: 'w-14 h-14 text-base',
};

export function TeamLogo({ name, logoUrl, size = 'md', className }: TeamLogoProps) {
  const [imgFailed, setImgFailed] = useState(false);
  const showImage = logoUrl && !imgFailed;

  return (
    <div
      className={cn(
        'flex-shrink-0 rounded-md bg-bg border border-border flex items-center justify-center overflow-hidden',
        LOGO_SIZE[size],
        className,
      )}
    >
      {showImage ? (
        <img
          src={logoUrl!}
          alt={name}
          className="w-full h-full object-contain"
          onError={() => setImgFailed(true)}
          loading="lazy"
        />
      ) : (
        <span className="font-bold text-ink-dim">{initials(name)}</span>
      )}
    </div>
  );
}
