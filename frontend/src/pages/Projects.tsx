import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listProjects } from '../api/client';
import type { ProjectSummary } from '../api/client';
import IndexingProgress from '../components/IndexingProgress';

export default function Projects() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-gray-400">Loading...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Projects</h2>
          <p className="text-sm text-gray-500 mt-1">{projects.length} projects</p>
        </div>
        <Link
          to="/projects/new"
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          + New Project
        </Link>
      </div>

      {projects.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <p className="text-gray-400 mb-3">No projects yet</p>
          <Link to="/projects/new" className="text-blue-600 hover:underline text-sm">
            Create your first project
          </Link>
        </div>
      ) : (
        <div className="grid gap-4">
          {projects.map((p) => (
            <Link
              key={p.id}
              to={`/projects/${p.id}`}
              className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow"
            >
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-medium text-gray-900">{p.name}</h3>
                <span
                  className={`px-2 py-1 rounded-full text-xs font-medium ${
                    p.status === 'active'
                      ? 'bg-green-100 text-green-700'
                      : p.status === 'completed'
                      ? 'bg-blue-100 text-blue-700'
                      : 'bg-gray-100 text-gray-700'
                  }`}
                >
                  {p.status}
                </span>
              </div>
              <div className="flex items-center gap-6 text-sm text-gray-500 mb-3">
                <span>{p.total_urls} URLs</span>
                <span>{p.indexed_count} indexed</span>
                <span>{new Date(p.created_at).toLocaleDateString()}</span>
              </div>
              <IndexingProgress indexed={p.indexed_count} total={p.total_urls} />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
