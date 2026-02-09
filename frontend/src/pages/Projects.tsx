import { useEffect, useState, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { listProjects } from '../api/client';
import type { ProjectSummary } from '../api/client';
import IndexingProgress from '../components/IndexingProgress';
import Favicon from '../components/Favicon';
import { CheckCircle, Clock, Send, Search, RefreshCw } from 'lucide-react';

export default function Projects() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadData = useCallback(() => {
    listProjects()
      .then((p) => { setProjects(p); setRefreshKey((k) => k + 1); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const hasProcessing = projects.some((p) => p.pending_count > 0);

  useEffect(() => {
    loadData();
    intervalRef.current = setInterval(loadData, 30000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [loadData]);

  if (loading) return <div className="text-slate-500">Loading...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div>
            <h2 className="text-2xl font-bold text-white">Projects</h2>
            <p className="text-sm text-slate-500 mt-1">{projects.length} projects</p>
          </div>
          {hasProcessing && (
            <span
              key={refreshKey}
              className="relative flex h-1 w-12 rounded-full overflow-hidden bg-slate-800 self-end mb-1.5"
              title="Prochain refresh"
            >
              <span
                className="absolute inset-y-0 left-0 rounded-full bg-cyan-500/70"
                style={{ animation: 'refreshCycle 30s linear forwards' }}
              />
            </span>
          )}
        </div>
        <Link
          to="/projects/new"
          className="bg-cyan-500 text-slate-950 px-4 py-2 rounded-lg text-sm font-medium hover:bg-cyan-400 transition-colors"
        >
          + New Project
        </Link>
      </div>

      {projects.length === 0 ? (
        <div className="bg-slate-900 rounded-xl border border-slate-800 p-12 text-center">
          <p className="text-slate-500 mb-3">No projects yet</p>
          <Link to="/projects/new" className="text-cyan-400 hover:underline text-sm">
            Create your first project
          </Link>
        </div>
      ) : (
        <div className="grid gap-4">
          {projects.map((p) => {
            const pctIndexed = p.total_urls > 0 ? Math.round(p.indexed_count / p.total_urls * 100) : 0;
            const pctNotIndexed = p.total_urls > 0 ? Math.round(p.not_indexed_count / p.total_urls * 100) : 0;
            const isProcessing = p.pending_count > 0;

            return (
              <Link
                key={p.id}
                to={`/projects/${p.id}`}
                className="bg-slate-900 rounded-xl border border-slate-800 p-5 hover:border-slate-700 transition-colors"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Favicon domain={p.main_domain} size={18} />
                    <h3 className="font-medium text-white">{p.name}</h3>
                  </div>
                  <div className="flex items-center gap-2">
                    {isProcessing && (
                      <span className="flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-medium bg-cyan-500/10 text-cyan-400">
                        <Send size={10} />
                        {p.pending_count} en cours
                      </span>
                    )}
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium ${
                        p.status === 'active'
                          ? 'bg-emerald-500/15 text-emerald-400'
                          : p.status === 'completed'
                          ? 'bg-cyan-500/15 text-cyan-400'
                          : 'bg-slate-700 text-slate-300'
                      }`}
                    >
                      {p.status}
                    </span>
                  </div>
                </div>

                {/* Stats row */}
                <div className="flex items-center gap-3 text-xs mb-3 flex-wrap">
                  <span className="flex items-center gap-1 text-slate-500">
                    {p.total_urls} URLs
                  </span>
                  <span className="flex items-center gap-1 text-emerald-400/80">
                    <CheckCircle size={11} />
                    {p.indexed_count} indexées ({pctIndexed}%)
                  </span>
                  {p.not_indexed_count > 0 && (
                    <span className="flex items-center gap-1 text-rose-400/80">
                      <Search size={11} />
                      {p.not_indexed_count} non indexées ({pctNotIndexed}%)
                    </span>
                  )}
                  {isProcessing && (
                    <span className="flex items-center gap-1 text-cyan-400/80">
                      <Clock size={11} />
                      {p.pending_count} en attente
                    </span>
                  )}
                  {p.recredited_count > 0 && (
                    <span className="flex items-center gap-1 text-amber-400/80">
                      <RefreshCw size={11} />
                      {p.recredited_count} recréditées
                    </span>
                  )}
                  <span className="text-slate-600 ml-auto">{new Date(p.created_at).toLocaleDateString()}</span>
                </div>

                <IndexingProgress indexed={p.indexed_count} total={p.total_urls} />
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
