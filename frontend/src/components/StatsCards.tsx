import { Globe, CheckCircle, Clock, RefreshCw } from 'lucide-react';

interface StatsCardsProps {
  total: number;
  indexed: number;
  pending: number;
  recredited: number;
  successRate: number;
  credits: number;
}

const cards = [
  { key: 'total', label: 'Total URLs', icon: Globe, color: 'text-blue-600', bg: 'bg-blue-50' },
  { key: 'indexed', label: 'Indexed', icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-50' },
  { key: 'pending', label: 'Pending', icon: Clock, color: 'text-yellow-600', bg: 'bg-yellow-50' },
  { key: 'recredited', label: 'Recredited', icon: RefreshCw, color: 'text-purple-600', bg: 'bg-purple-50' },
];

export default function StatsCards({ total, indexed, pending, recredited, successRate, credits }: StatsCardsProps) {
  const values: Record<string, number> = { total, indexed, pending, recredited };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
      {cards.map(({ key, label, icon: Icon, color, bg }) => (
        <div key={key} className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center gap-3">
            <div className={`${bg} p-2 rounded-lg`}>
              <Icon size={20} className={color} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{values[key]}</p>
              <p className="text-xs text-gray-500">{label}</p>
            </div>
          </div>
        </div>
      ))}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex items-center gap-3">
          <div className="bg-indigo-50 p-2 rounded-lg">
            <span className="text-indigo-600 font-bold text-sm">{successRate}%</span>
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{credits}</p>
            <p className="text-xs text-gray-500">Credits left</p>
          </div>
        </div>
      </div>
    </div>
  );
}
