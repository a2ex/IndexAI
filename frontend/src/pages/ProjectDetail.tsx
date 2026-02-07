import { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getProject, getProjectStatus, exportProjectCsv, addUrls, getCredits } from '../api/client';
import type { ProjectDetail as ProjectDetailType, ProjectStatus } from '../api/client';
import IndexingProgress from '../components/IndexingProgress';
import URLStatusTable from '../components/URLStatusTable';
import StatsCards from '../components/StatsCards';
import { Loader2, Plus, Upload, ChevronDown, ChevronUp } from 'lucide-react';

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<ProjectDetailType | null>(null);
  const [status, setStatus] = useState<ProjectStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Add URLs form
  const [showAddUrls, setShowAddUrls] = useState(false);
  const [urlsText, setUrlsText] = useState('');
  const [credits, setCredits] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [addError, setAddError] = useState('');
  const [addSuccess, setAddSuccess] = useState('');

  const parsedUrls = urlsText
    .split('\n')
    .map((u) => u.trim())
    .filter((u) => u.length > 0 && u.startsWith('http'));

  const loadData = () => {
    if (!id) return;
    Promise.all([getProject(id), getProjectStatus(id)])
      .then(([p, s]) => {
        setProject(p);
        setStatus(s);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  const hasProcessing = status
    ? status.urls.some((u) => u.status === 'pending' || u.status === 'submitted' || u.status === 'indexing')
    : false;

  useEffect(() => {
    loadData();
  }, [id]);

  // Load credits when the Add URLs form is opened
  useEffect(() => {
    if (showAddUrls) {
      getCredits().then((c) => setCredits(c.balance)).catch(() => {});
    }
  }, [showAddUrls]);

  // Auto-refresh while tasks are processing
  useEffect(() => {
    if (hasProcessing) {
      intervalRef.current = setInterval(loadData, 10000);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [hasProcessing, id]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      setUrlsText((prev) => (prev ? prev + '\n' : '') + (ev.target?.result as string));
    };
    reader.readAsText(file);
  };

  const handleAddUrls = async () => {
    if (!id || parsedUrls.length === 0) return;
    if (parsedUrls.length > credits) {
      setAddError(`Not enough credits. You have ${credits}, need ${parsedUrls.length}`);
      return;
    }

    setSubmitting(true);
    setAddError('');
    setAddSuccess('');
    try {
      const result = await addUrls(id, parsedUrls);
      setAddSuccess(`${result.added} URL(s) added — ${result.credits_debited} credit(s) debited`);
      setUrlsText('');
      loadData();
      getCredits().then((c) => setCredits(c.balance)).catch(() => {});
    } catch (e: any) {
      setAddError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="text-gray-400">Loading...</div>;
  if (!project || !status) return <div className="text-red-500">Project not found</div>;

  return (
    <div className="space-y-6">
      <div>
        <Link to="/projects" className="text-sm text-blue-600 hover:underline">
          &larr; Back to projects
        </Link>
        <h2 className="text-2xl font-bold text-gray-900 mt-2">{project.name}</h2>
        {project.description && (
          <p className="text-sm text-gray-500 mt-1">{project.description}</p>
        )}
      </div>

      {hasProcessing && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center gap-3">
          <Loader2 size={18} className="text-blue-600 animate-spin" />
          <div>
            <p className="text-sm font-medium text-blue-800">Indexation in progress</p>
            <p className="text-xs text-blue-600 mt-0.5">
              {status!.urls.filter((u) => u.status === 'pending' || u.status === 'submitted' || u.status === 'indexing').length} URL{status!.urls.filter((u) => u.status === 'pending' || u.status === 'submitted' || u.status === 'indexing').length > 1 ? 's' : ''} being processed — auto-refreshing every 10s
            </p>
          </div>
        </div>
      )}

      <StatsCards
        total={status.total}
        indexed={status.indexed}
        pending={status.pending}
        recredited={status.recredited}
        successRate={status.success_rate}
        credits={0}
      />

      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-medium text-gray-700 mb-3">Overall Progress</h3>
        <IndexingProgress indexed={status.indexed} total={status.total} />
      </div>

      {/* Add URLs */}
      <div className="bg-white rounded-xl border border-gray-200">
        <button
          onClick={() => setShowAddUrls((v) => !v)}
          className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50 transition-colors rounded-xl"
        >
          <div className="flex items-center gap-2">
            <Plus size={16} className="text-blue-600" />
            <span className="text-sm font-medium text-gray-900">Add URLs</span>
          </div>
          {showAddUrls ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
        </button>

        {showAddUrls && (
          <div className="px-5 pb-5 space-y-4 border-t border-gray-100 pt-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                URLs (one per line)
              </label>
              <textarea
                value={urlsText}
                onChange={(e) => { setUrlsText(e.target.value); setAddError(''); setAddSuccess(''); }}
                placeholder={"https://example.com/new-page1\nhttps://example.com/new-page2"}
                rows={6}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <label className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline cursor-pointer mt-1">
                <Upload size={14} />
                Upload CSV/TXT
                <input
                  type="file"
                  accept=".csv,.txt"
                  onChange={handleFileUpload}
                  className="hidden"
                />
              </label>
            </div>

            <div className="bg-gray-50 rounded-lg p-3 flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-700">
                  <span className="font-bold text-lg">{parsedUrls.length}</span> URL(s) to add
                </p>
                <p className="text-xs text-gray-500 mt-0.5">
                  Cost: {parsedUrls.length} credit(s) | Balance: {credits}
                </p>
              </div>
              {parsedUrls.length > credits && (
                <span className="text-xs text-red-500 font-medium">Insufficient credits</span>
              )}
            </div>

            {addError && (
              <div className="bg-red-50 text-red-700 text-sm rounded-lg p-3">{addError}</div>
            )}
            {addSuccess && (
              <div className="bg-green-50 text-green-700 text-sm rounded-lg p-3">{addSuccess}</div>
            )}

            <button
              onClick={handleAddUrls}
              disabled={submitting || parsedUrls.length === 0 || parsedUrls.length > credits}
              className="w-full bg-blue-600 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? 'Submitting...' : `Add ${parsedUrls.length} URL(s) to project`}
            </button>
          </div>
        )}
      </div>

      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-gray-700">URLs ({status.total})</h3>
          <button
            onClick={() => exportProjectCsv(id!)}
            className="px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Export CSV
          </button>
        </div>
        <URLStatusTable urls={status.urls} onRefresh={loadData} />
      </div>
    </div>
  );
}
