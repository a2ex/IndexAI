import { useEffect, useState } from 'react';
import { listProjects, getCredits, getDailyStats } from '../api/client';
import type { ProjectSummary, DailyStats } from '../api/client';
import StatsCards from '../components/StatsCards';
import IndexingProgress from '../components/IndexingProgress';
import Charts from '../components/Charts';
import { Link } from 'react-router-dom';

export default function Dashboard() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [credits, setCredits] = useState(0);
  const [chartData, setChartData] = useState<DailyStats[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([listProjects(), getCredits(), getDailyStats(30)])
      .then(([p, c, stats]) => {
        setProjects(p);
        setCredits(c.balance);
        setChartData(stats);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const totalUrls = projects.reduce((s, p) => s + p.total_urls, 0);
  const totalIndexed = projects.reduce((s, p) => s + p.indexed_count, 0);
  const totalPending = totalUrls - totalIndexed - projects.reduce((s, p) => s + p.failed_count, 0);
  const successRate = totalUrls > 0 ? Math.round((totalIndexed / totalUrls) * 100 * 10) / 10 : 0;

  if (loading) {
    return <div className="text-gray-400">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
        <p className="text-sm text-gray-500 mt-1">Overview of your indexation activity</p>
      </div>

      <StatsCards
        total={totalUrls}
        indexed={totalIndexed}
        pending={totalPending}
        recredited={0}
        successRate={successRate}
        credits={credits}
      />

      <Charts data={chartData} />

      <div className="bg-white rounded-xl border border-gray-200">
        <div className="p-5 border-b border-gray-200 flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-700">Recent Projects</h3>
          <Link to="/projects/new" className="text-sm text-blue-600 hover:underline">
            + New Project
          </Link>
        </div>
        {projects.length === 0 ? (
          <div className="p-8 text-center text-gray-400">
            <p>No projects yet</p>
            <Link to="/projects/new" className="text-blue-600 hover:underline text-sm mt-2 inline-block">
              Create your first project
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {projects.slice(0, 5).map((p) => (
              <Link
                key={p.id}
                to={`/projects/${p.id}`}
                className="flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">{p.name}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {p.indexed_count}/{p.total_urls} indexed
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
