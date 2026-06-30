export function Footer() {
  return (
    <footer className="border-t border-border/30 mt-32">
      <div className="max-w-7xl mx-auto px-6 lg:px-8 py-8 flex flex-col md:flex-row items-center justify-between gap-4">
        <p className="text-xs text-ink-dim">
          Data sourced from vlr.gg · Predictions via custom ML model
        </p>
        <p className="text-xs text-ink-dim">
          Built as MSc dissertation research · 2026
        </p>
      </div>
    </footer>
  );
}
