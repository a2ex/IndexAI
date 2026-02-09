import { useEffect, useState, useRef, useCallback } from 'react';
import { listProjects, getCredits, getDailyStats, getIndexingStats } from '../api/client';
import type { ProjectSummary, DailyStats, IndexingStats } from '../api/client';
import StatsCards from '../components/StatsCards';
import IndexingProgress from '../components/IndexingProgress';
import IndexingSpeedCard from '../components/IndexingSpeedCard';
import MethodSuccessRates from '../components/MethodSuccessRates';
import Charts from '../components/Charts';
import { Link } from 'react-router-dom';
import Favicon from '../components/Favicon';
import { Activity, CheckCircle, Send, Search, RefreshCw } from 'lucide-react';

export default function Dashboard() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [credits, setCredits] = useState(0);
  const [chartData, setChartData] = useState<DailyStats[]>([]);
  const [indexingStats, setIndexingStats] = useState<IndexingStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadData = useCallback(() => {
    Promise.all([listProjects(), getCredits(), getDailyStats(30), getIndexingStats()])
      .then(([p, c, stats, iStats]) => {
        setProjects(p);
        setCredits(c.balance);
        setChartData(stats);
        setIndexingStats(iStats);
        setRefreshKey((k) => k + 1);
        setError('');
      })
      .catch((e) => setError(e.message || 'Failed to load dashboard data'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadData();
    intervalRef.current = setInterval(loadData, 60000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [loadData]);

  const totalUrls = projects.reduce((s, p) => s + p.total_urls, 0);
  const totalIndexed = projects.reduce((s, p) => s + p.indexed_count, 0);
  const totalNotIndexed = totalUrls - totalIndexed;
  const totalPending = projects.reduce((s, p) => s + p.pending_count, 0);
  const totalRecredited = projects.reduce((s, p) => s + p.recredited_count, 0);
  const successRate = totalUrls > 0 ? Math.round((totalIndexed / totalUrls) * 100 * 10) / 10 : 0;

  if (loading) {
    return <div className="text-slate-500">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white">Dashboard</h2>
        <p className="text-sm text-slate-500 mt-1">Overview of your indexation activity</p>
      </div>

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm rounded-lg p-3">
          {error}
        </div>
      )}

      <StatsCards
        total={totalUrls}
        indexed={totalIndexed}
        notIndexed={totalNotIndexed}
        pending={totalPending}
        recredited={totalRecredited}
        successRate={successRate}
        credits={credits}
        indexedByService={indexingStats?.indexed_by_service}
      />

      {/* Active Tasks & Indexation Status Widget */}
      {projects.length > 0 && (() => {
        const activeProjects = projects.filter((p) => p.pending_count > 0);
        const totalProcessing = totalPending;
        const indexedPct = totalUrls > 0 ? (totalIndexed / totalUrls * 100).toFixed(1) : '0.0';
        const notIndexedPct = totalUrls > 0 ? (totalNotIndexed / totalUrls * 100).toFixed(1) : '0.0';
        const processingPct = totalUrls > 0 ? (totalProcessing / totalUrls * 100).toFixed(1) : '0.0';
        const recreditedPct = totalUrls > 0 ? (totalRecredited / totalUrls * 100).toFixed(1) : '0.0';

        return (
          <div className="bg-slate-900 rounded-xl border border-slate-800">
            <div className="p-5 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity size={16} className="text-cyan-400" />
                <h3 className="text-sm font-medium text-slate-300">Statut d'indexation</h3>
              </div>
              <span
                key={refreshKey}
                className="relative flex h-1 w-16 rounded-full overflow-hidden bg-slate-800"
                title="Prochain refresh"
              >
                <span
                  className="absolute inset-y-0 left-0 rounded-full bg-cyan-500/70"
                  style={{ animation: 'refreshCycle 60s linear forwards' }}
                />
              </span>
            </div>

            <div className="p-5 space-y-4">
              {/* Global KPIs */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3 text-center">
                  <CheckCircle size={14} className="text-emerald-400 mx-auto mb-1" />
                  <p className="text-lg font-bold text-emerald-400">{indexedPct}%</p>
                  <p className="text-[10px] text-emerald-400/70">{totalIndexed} indexées</p>
                </div>
                <div className="bg-cyan-500/10 border border-cyan-500/20 rounded-lg p-3 text-center">
                  <Send size={14} className="text-cyan-400 mx-auto mb-1" />
                  <p className="text-lg font-bold text-cyan-400">{processingPct}%</p>
                  <p className="text-[10px] text-cyan-400/70">{totalProcessing} en cours</p>
                </div>
                <div className="bg-rose-500/10 border border-rose-500/20 rounded-lg p-3 text-center">
                  <Search size={14} className="text-rose-400 mx-auto mb-1" />
                  <p className="text-lg font-bold text-rose-400">{notIndexedPct}%</p>
                  <p className="text-[10px] text-rose-400/70">{totalNotIndexed} non indexées</p>
                </div>
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 text-center">
                  <RefreshCw size={14} className="text-amber-400 mx-auto mb-1" />
                  <p className="text-lg font-bold text-amber-400">{recreditedPct}%</p>
                  <p className="text-[10px] text-amber-400/70">{totalRecredited} recréditées</p>
                </div>
              </div>

              {/* Active projects */}
              {activeProjects.length > 0 && (
                <div>
                  <p className="text-xs text-slate-500 mb-2">
                    {activeProjects.length} projet{activeProjects.length > 1 ? 's' : ''} avec tâches actives
                  </p>
                  <div className="space-y-2">
                    {activeProjects.slice(0, 5).map((p) => {
                      const pctIndexed = p.total_urls > 0 ? Math.round(p.indexed_count / p.total_urls * 100) : 0;
                      return (
                        <Link
                          key={p.id}
                          to={`/projects/${p.id}`}
                          className="flex items-center gap-3 p-2.5 rounded-lg bg-slate-800/50 hover:bg-slate-800 transition-colors"
                        >
                          <Favicon domain={p.main_domain} size={14} />
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-medium text-white truncate">{p.name}</p>
                            <p className="text-[10px] text-slate-500">
                              {p.indexed_count}/{p.total_urls} indexées ({pctIndexed}%) · {p.pending_count} en cours
                            </p>
                          </div>
                          <div className="w-24">
                            <IndexingProgress indexed={p.indexed_count} total={p.total_urls} />
                          </div>
                        </Link>
                      );
                    })}
                  </div>
                </div>
              )}

              {activeProjects.length === 0 && (
                <p className="text-xs text-slate-500 text-center py-2">
                  Aucune tâche d'indexation en cours
                </p>
              )}
            </div>
          </div>
        );
      })()}

      {indexingStats && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <IndexingSpeedCard stats={indexingStats.speed} />
          <MethodSuccessRates methods={indexingStats.methods} />
        </div>
      )}

      <Charts data={chartData} />

      <div className="bg-slate-900 rounded-xl border border-slate-800">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <h3 className="text-sm font-medium text-slate-300">Recent Projects</h3>
          <Link to="/projects/new" className="text-sm text-cyan-400 hover:underline">
            + New Project
          </Link>
        </div>
        {projects.length === 0 ? (
          <div className="p-8 text-center text-slate-500">
            <p>No projects yet</p>
            <Link to="/projects/new" className="text-cyan-400 hover:underline text-sm mt-2 inline-block">
              Create your first project
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/50">
            {projects.slice(0, 5).map((p) => (
              <Link
                key={p.id}
                to={`/projects/${p.id}`}
                className="flex items-center justify-between p-4 hover:bg-slate-800/50 transition-colors"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <Favicon domain={p.main_domain} size={16} />
                    <p className="text-sm font-medium text-white">{p.name}</p>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    {p.indexed_count}/{p.total_urls} indexed ({p.total_urls > 0 ? Math.round(p.indexed_count / p.total_urls * 100) : 0}%)
                  </p>
                </div>
                <div className="w-48">
                  <IndexingProgress indexed={p.indexed_count} total={p.total_urls} />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
