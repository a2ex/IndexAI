import { Globe, CheckCircle, Clock, RefreshCw, XCircle } from 'lucide-react';

interface StatsCardsProps {
  total: number;
  indexed: number;
  pending: number;
  notIndexed: number;
  recredited: number;
  successRate: number;
  credits: number;
  indexedByService?: number;
}

const cards = [
  { key: 'total', label: 'Total URLs', icon: Globe, color: 'text-cyan-400', bg: 'bg-cyan-500/10' },
  { key: 'indexed', label: 'Indexed', icon: CheckCircle, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  { key: 'notIndexed', label: 'Not Indexed', icon: XCircle, color: 'text-rose-400', bg: 'bg-rose-500/10' },
  { key: 'pending', label: 'Pending', icon: Clock, color: 'text-amber-400', bg: 'bg-amber-500/10' },
  { key: 'recredited', label: 'Recredited', icon: RefreshCw, color: 'text-violet-400', bg: 'bg-violet-500/10' },
];

export default function StatsCards({ total, indexed, notIndexed, pending, recredited, successRate, credits, indexedByService }: StatsCardsProps) {
  const values: Record<string, number> = { total, indexed, notIndexed, pending, recredited };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
      {cards.map(({ key, label, icon: Icon, color, bg }) => (
        <div key={key} className="bg-slate-900 rounded-xl border border-slate-800 p-5">
          <div className="flex items-center gap-3">
            <div className={`${bg} p-2 rounded-lg`}>
              <Icon size={20} className={color} />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{values[key]}</p>
              <p className="text-xs text-slate-500">{label}</p>
              {key === 'indexed' && indexedByService != null && indexedByService > 0 && (
                <p className="text-[10px] text-emerald-400/80 mt-0.5">+{indexedByService} grâce à IndexAI</p>
              )}
            </div>
          </div>
        </div>
      ))}
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
        <div className="flex items-center gap-3">
          <div className="bg-cyan-500/10 p-2 rounded-lg">
            <span className="text-cyan-400 font-bold text-sm">{successRate}%</span>
          </div>
          <div>
            <p className="text-2xl font-bold text-white">{credits}</p>
            <p className="text-xs text-slate-500">Credits left</p>
          </div>
        </div>
      </div>
    </div>
  );
}
