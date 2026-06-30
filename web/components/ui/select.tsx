'use client';

import { useEffect, useRef, useState } from 'react';
import { ChevronDown, Check, Search } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';

interface SelectOption {
  value: string | number;
  label: string;
  sub?: string;
}

interface SelectProps {
  options: SelectOption[];
  value: string | number | null;
  onChange: (value: string | number) => void;
  placeholder?: string;
  label?: string;
  searchable?: boolean;
  disabled?: boolean;
}

export function Select({
  options,
  value,
  onChange,
  placeholder = 'Select...',
  label,
  searchable = true,
  disabled,
}: SelectProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const ref = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
        setSearch('');
      }
    }
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  useEffect(() => {
    if (open && searchable && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [open, searchable]);

  const selected = options.find((o) => o.value === value);
  const filtered = search
    ? options.filter((o) => o.label.toLowerCase().includes(search.toLowerCase()))
    : options;

  return (
    <div ref={ref} className="relative">
      {label && (
        <label className="block text-[0.7rem] font-medium uppercase tracking-widest text-ink-dim mb-2">
          {label}
        </label>
      )}
      <button
        type="button"
        disabled={disabled}
        onClick={() => !disabled && setOpen(!open)}
        className={cn(
          'w-full flex items-center justify-between gap-2 px-4 py-2.5 text-sm bg-surface border border-border rounded-lg text-ink',
          'hover:border-border-strong transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent/50',
          open && 'border-border-strong',
          disabled && 'opacity-50 cursor-not-allowed',
        )}
      >
        <span className={cn('truncate text-left', !selected && 'text-ink-dim')}>
          {selected ? selected.label : placeholder}
        </span>
        <ChevronDown
          className={cn(
            'w-4 h-4 text-ink-soft transition-transform',
            open && 'rotate-180',
          )}
        />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
            className="absolute z-50 w-full mt-2 bg-surface-high border border-border rounded-lg shadow-2xl overflow-hidden"
          >
            {searchable && (
              <div className="relative border-b border-border">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-ink-dim" />
                <input
                  ref={inputRef}
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search..."
                  className="w-full pl-9 pr-3 py-2.5 text-sm bg-transparent text-ink placeholder:text-ink-dim focus:outline-none"
                />
              </div>
            )}
            <div className="max-h-72 overflow-y-auto py-1">
              {filtered.length === 0 ? (
                <div className="px-4 py-3 text-sm text-ink-dim text-center">
                  No matches
                </div>
              ) : (
                filtered.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => {
                      onChange(opt.value);
                      setOpen(false);
                      setSearch('');
                    }}
                    className={cn(
                      'w-full px-3 py-2 text-sm flex items-center justify-between gap-2 hover:bg-surface-hover transition-colors',
                      value === opt.value && 'text-accent',
                    )}
                  >
                    <span className="text-left flex-1 min-w-0">
                      <span className="block truncate">{opt.label}</span>
                      {opt.sub && (
                        <span className="block text-xs text-ink-dim mt-0.5">
                          {opt.sub}
                        </span>
                      )}
                    </span>
                    {value === opt.value && (
                      <Check className="w-3.5 h-3.5 flex-shrink-0" />
                    )}
                  </button>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
