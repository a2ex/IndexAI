import type { IndexingSpeedStats } from '../api/client';

const tiers = [
  { label: '24h', key: 'pct_24h', countKey: 'indexed_24h', color: 'bg-red-500', text: 'text-red-400' },
  { label: '48h', key: 'pct_48h', countKey: 'indexed_48h', color: 'bg-orange-500', text: 'text-orange-400' },
  { label: '72h', key: 'pct_72h', countKey: 'indexed_72h', color: 'bg-amber-500', text: 'text-amber-400' },
  { label: '7d', key: 'pct_7d', countKey: 'indexed_7d', color: 'bg-emerald-500', text: 'text-emerald-400' },
] as const;

export default function IndexingSpeedCard({ stats }: { stats: IndexingSpeedStats }) {
  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
      <h3 className="text-sm font-medium text-slate-300 mb-4">Indexing Speed</h3>
      <div className="space-y-3">
        {tiers.map((tier) => {
          const pct = stats[tier.key] as number;
          const count = stats[tier.countKey] as number;
          return (
            <div key={tier.label} className="flex items-center gap-3">
              <span className={`text-xs font-mono w-8 text-right ${tier.text}`}>
                {tier.label}
              </span>
              <div className="flex-1 h-5 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className={`h-full ${tier.color} rounded-full transition-all duration-500`}
                  style={{ width: `${Math.max(pct, 1)}%` }}
                />
              </div>
              <span className="text-xs text-slate-400 w-24 text-right font-mono">
                {pct}% ({count}/{stats.total_submitted})
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
