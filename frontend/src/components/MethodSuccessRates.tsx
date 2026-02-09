import { Search, Zap, Radio, Bell, Archive, Link, Globe, Share2 } from 'lucide-react';
import type { MethodStats } from '../api/client';

const methodConfig: Record<string, {
  icon: React.ReactNode;
  label: string;
  color: string;
  barColor: string;
}> = {
  google_api: {
    icon: <Search size={14} strokeWidth={2.5} />,
    label: 'Google API',
    color: 'text-blue-400',
    barColor: 'bg-blue-500',
  },
  indexnow: {
    icon: <Zap size={14} strokeWidth={2.5} />,
    label: 'IndexNow',
    color: 'text-amber-400',
    barColor: 'bg-amber-500',
  },
  pingomatic: {
    icon: <Radio size={14} strokeWidth={2.5} />,
    label: 'Ping-O-Matic',
    color: 'text-violet-400',
    barColor: 'bg-violet-500',
  },
  websub: {
    icon: <Bell size={14} strokeWidth={2.5} />,
    label: 'WebSub',
    color: 'text-cyan-400',
    barColor: 'bg-cyan-500',
  },
  archive_org: {
    icon: <Archive size={14} strokeWidth={2.5} />,
    label: 'Archive.org',
    color: 'text-orange-400',
    barColor: 'bg-orange-500',
  },
  backlink_pings: {
    icon: <Link size={14} strokeWidth={2.5} />,
    label: 'Backlinks',
    color: 'text-emerald-400',
    barColor: 'bg-emerald-500',
  },
  sitemap_ping_google: {
    icon: <Globe size={14} strokeWidth={2.5} />,
    label: 'Sitemap Google',
    color: 'text-blue-300',
    barColor: 'bg-blue-400',
  },
  sitemap_ping_bing: {
    icon: <Globe size={14} strokeWidth={2.5} />,
    label: 'Sitemap Bing',
    color: 'text-sky-400',
    barColor: 'bg-sky-500',
  },
  social_signals: {
    icon: <Share2 size={14} strokeWidth={2.5} />,
    label: 'Social Signals',
    color: 'text-pink-400',
    barColor: 'bg-pink-500',
  },
};

const methodOrder = [
  'google_api', 'indexnow', 'pingomatic', 'websub',
  'archive_org', 'backlink_pings', 'sitemap_ping_google',
  'sitemap_ping_bing', 'social_signals',
];

export default function MethodSuccessRates({ methods }: { methods: Record<string, MethodStats> }) {
  const sorted = methodOrder.filter((m) => m in methods);

  if (sorted.length === 0) {
    return null;
  }

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
      <h3 className="text-sm font-medium text-slate-300 mb-4">Method Success Rates</h3>
      <div className="space-y-3">
        {sorted.map((key) => {
          const cfg = methodConfig[key];
          const stats = methods[key];
          if (!cfg) return null;
          return (
            <div key={key} className="flex items-center gap-3">
              <div className={`flex items-center gap-1.5 w-28 ${cfg.color}`}>
                {cfg.icon}
                <span className="text-xs font-medium truncate">{cfg.label}</span>
              </div>
              <div className="flex-1 h-5 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className={`h-full ${cfg.barColor} rounded-full transition-all duration-500`}
                  style={{ width: `${Math.max(stats.rate, 1)}%` }}
                />
              </div>
              <span className="text-xs text-slate-400 w-28 text-right font-mono">
                {stats.rate}% ({stats.success}/{stats.total_attempts})
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
