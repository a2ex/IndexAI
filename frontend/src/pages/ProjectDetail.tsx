import { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getProject, getProjectStatus, exportProjectCsv, addUrls, getCredits, getGscSitemaps, importGscUrls, listServiceAccounts, updateProject, triggerVerification } from '../api/client';
import type { ProjectDetail as ProjectDetailType, ProjectStatus, GscSitemap, ServiceAccountSummary } from '../api/client';
import IndexingProgress from '../components/IndexingProgress';
import URLStatusTable from '../components/URLStatusTable';
import StatsCards from '../components/StatsCards';
import { Loader2, Plus, Upload, ChevronDown, ChevronUp, Globe, Settings, Check } from 'lucide-react';
import Favicon from '../components/Favicon';

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<ProjectDetailType | null>(null);
  const [status, setStatus] = useState<ProjectStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const verifyTriggered = useRef(false);

  // Add URLs form
  const [showAddUrls, setShowAddUrls] = useState(false);
  const [urlsText, setUrlsText] = useState('');
  const [credits, setCredits] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [addError, setAddError] = useState('');
  const [addSuccess, setAddSuccess] = useState('');

  // GSC Import
  const [showGscImport, setShowGscImport] = useState(false);
  const [gscSitemaps, setGscSitemaps] = useState<GscSitemap[]>([]);
  const [gscLoading, setGscLoading] = useState(false);
  const [gscSelected, setGscSelected] = useState<Set<string>>(new Set());
  const [gscImporting, setGscImporting] = useState(false);
  const [gscError, setGscError] = useState('');
  const [gscSuccess, setGscSuccess] = useState('');

  // GSC Configuration
  const [showGscConfig, setShowGscConfig] = useState(false);
  const [serviceAccounts, setServiceAccounts] = useState<ServiceAccountSummary[]>([]);
  const [saLoading, setSaLoading] = useState(false);
  const [saSaving, setSaSaving] = useState(false);
  const [saSuccess, setSaSuccess] = useState('');
  const [saError, setSaError] = useState('');

  // URL pagination & filters (server-side)
  const PAGE_SIZE = 100;
  const [urlPage, setUrlPage] = useState(0);
  const [urlStatusFilter, setUrlStatusFilter] = useState('all');
  const [urlSearch, setUrlSearch] = useState('');
  const [urlSearchDebounced, setUrlSearchDebounced] = useState('');
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const parsedUrls = urlsText
    .split('\n')
    .map((u) => u.trim())
    .filter((u) => u.length > 0 && u.startsWith('http'));

  const [loadError, setLoadError] = useState('');

  const loadData = (opts?: { page?: number; statusF?: string; search?: string }) => {
    if (!id) return;
    const page = opts?.page ?? urlPage;
    const sf = opts?.statusF ?? urlStatusFilter;
    const sq = opts?.search ?? urlSearchDebounced;
    Promise.all([
      getProject(id),
      getProjectStatus(id, { limit: PAGE_SIZE, offset: page * PAGE_SIZE, status: sf, search: sq }),
    ])
      .then(([p, s]) => {
        setProject(p);
        setStatus(s);
        setLoadError('');
      })
      .catch((e) => setLoadError(e.message || 'Failed to load project'))
      .finally(() => setLoading(false));
  };

  const hasProcessing = status
    ? status.pending > 0 || status.verifying > 0
    : false;

  useEffect(() => {
    loadData();
  }, [id]);

  // Auto-trigger verification when the project has verifying URLs
  useEffect(() => {
    if (id && status && status.verifying > 0 && !verifyTriggered.current) {
      verifyTriggered.current = true;
      triggerVerification(id).catch(() => {});
    }
  }, [id, status]);

  // Load credits when the Add URLs form is opened
  useEffect(() => {
    if (showAddUrls) {
      getCredits().then((c) => setCredits(c.balance)).catch(() => {});
    }
  }, [showAddUrls]);

  // Auto-refresh while tasks are processing
  useEffect(() => {
    if (hasProcessing) {
      intervalRef.current = setInterval(loadData, 30000);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [hasProcessing, id]);

  // Load GSC sitemaps when the section is opened
  useEffect(() => {
    if (showGscImport && id) {
      setGscLoading(true);
      setGscError('');
      getGscSitemaps(id)
        .then((sitemaps) => setGscSitemaps(sitemaps))
        .catch((e) => setGscError(e.message))
        .finally(() => setGscLoading(false));
    }
  }, [showGscImport, id]);

  // Load service accounts when GSC config is opened
  useEffect(() => {
    if (showGscConfig) {
      setSaLoading(true);
      listServiceAccounts()
        .then((sas) => setServiceAccounts(sas))
        .catch(() => {})
        .finally(() => setSaLoading(false));
    }
  }, [showGscConfig]);

  const handleSaSave = async (saId: string | null) => {
    if (!id) return;
    setSaSaving(true);
    setSaError('');
    setSaSuccess('');
    try {
      await updateProject(id, { gsc_service_account_id: saId });
      setSaSuccess(saId ? 'Service account assigned' : 'Service account removed');
      // Reload project to reflect the change
      loadData();
    } catch (e: any) {
      setSaError(e.message);
    } finally {
      setSaSaving(false);
    }
  };

  const toggleGscSitemap = (path: string) => {
    setGscSelected((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const handleGscImport = async () => {
    if (!id || gscSelected.size === 0) return;
    setGscImporting(true);
    setGscError('');
    setGscSuccess('');
    try {
      const result = await importGscUrls(id, Array.from(gscSelected));
      const parts: string[] = [];
      if (result.added > 0) parts.push(`${result.added} URL(s) added`);
      if (result.duplicates_skipped > 0) parts.push(`${result.duplicates_skipped} duplicate(s) skipped`);
      if (result.credits_debited > 0) parts.push(`${result.credits_debited} credit(s) debited`);
      setGscSuccess(parts.join(' — ') || 'No new URLs to import');
      setGscSelected(new Set());
      loadData();
      // Reload sitemaps to update imported status
      getGscSitemaps(id).then((s) => setGscSitemaps(s)).catch(() => {});
    } catch (e: any) {
      setGscError(e.message);
    } finally {
      setGscImporting(false);
    }
  };

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

  if (loading) return <div className="text-slate-500">Loading...</div>;
  if (loadError) return (
    <div className="space-y-4">
      <Link to="/projects" className="text-sm text-cyan-400 hover:underline">&larr; Back to projects</Link>
      <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm rounded-lg p-3">{loadError}</div>
    </div>
  );
  if (!project || !status) return <div className="text-rose-400">Project not found</div>;

  return (
    <div className="space-y-6">
      <div>
        <Link to="/projects" className="text-sm text-cyan-400 hover:underline">
          &larr; Back to projects
        </Link>
        <div className="flex items-center gap-2.5 mt-2">
          <Favicon domain={project.main_domain} size={24} />
          <h2 className="text-2xl font-bold text-white">{project.name}</h2>
        </div>
        {project.description && (
          <p className="text-sm text-slate-500 mt-1">{project.description}</p>
        )}
      </div>

      {hasProcessing && (() => {
        const verified = status!.indexed + status!.not_indexed + status!.recredited;
        const total = status!.total;
        const verifyingCount = status!.verifying;
        const pendingCount = status!.pending;
        const progressPct = total > 0 ? (verified / total * 100) : 0;
        const verifyingPct = total > 0 ? (verifyingCount / total * 100) : 0;
        return (
          <div className="bg-cyan-500/10 border border-cyan-500/20 rounded-xl overflow-hidden">
            <div className="p-4">
              <div className="flex-1">
                <p className="text-sm font-medium text-cyan-300">
                  Verification : {verified} / {total}
                  {verifyingCount > 0 && ` — ${verifyingCount} en cours`}
                </p>
                <p className="text-xs text-cyan-400/70 mt-0.5">
                  {pendingCount > 0 && `${pendingCount} en attente · `}
                  auto-refresh 30s
                </p>
              </div>
            </div>
            <div className="h-2 bg-slate-800 overflow-hidden rounded-b-xl flex">
              {progressPct > 0 && (
                <div
                  className="h-full bg-emerald-500 transition-all duration-700"
                  style={{ width: `${progressPct}%` }}
                />
              )}
              {verifyingPct > 0 && (
                <div
                  className="h-full animate-pulse transition-all duration-700"
                  style={{ width: `${verifyingPct}%`, backgroundColor: '#3b82f6' }}
                />
              )}
            </div>
          </div>
        );
      })()}

      <StatsCards
        total={status.total}
        indexed={status.indexed}
        notIndexed={status.total - status.indexed}
        pending={status.pending}
        recredited={status.recredited}
        successRate={status.success_rate}
        credits={0}
        indexedByService={status.indexed_by_service}
      />

      <div className="bg-slate-900 rounded-xl border border-slate-800 p-5">
        <h3 className="text-sm font-medium text-slate-300 mb-3">Overall Progress</h3>
        <IndexingProgress indexed={status.indexed} total={status.total} />
      </div>

      {/* GSC Configuration */}
      <div className="bg-slate-900 rounded-xl border border-slate-800">
        <button
          onClick={() => setShowGscConfig((v) => !v)}
          className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-800/50 transition-colors rounded-xl"
        >
          <div className="flex items-center gap-2">
            <Settings size={16} className="text-cyan-400" />
            <span className="text-sm font-medium text-white">GSC Configuration</span>
            {project.gsc_service_account_id ? (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-500/15 text-emerald-400">
                <Check size={10} /> Configured
              </span>
            ) : (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-700 text-slate-400">
                Global
              </span>
            )}
          </div>
          {showGscConfig ? <ChevronUp size={16} className="text-slate-500" /> : <ChevronDown size={16} className="text-slate-500" />}
        </button>

        {showGscConfig && (
          <div className="px-5 pb-5 space-y-4 border-t border-slate-800/50 pt-4">
            <p className="text-xs text-slate-500">
              Assign a Google Search Console service account to this project. The checker will auto-detect the GSC property matching your domain.
            </p>

            {saLoading ? (
              <div className="flex items-center gap-2 text-slate-400 text-sm">
                <Loader2 size={14} className="animate-spin" />
                Loading service accounts...
              </div>
            ) : (
              <div className="space-y-2">
                {/* "None / Global fallback" option */}
                <label
                  className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
                    !project.gsc_service_account_id ? 'bg-cyan-500/10 border border-cyan-500/20' : 'bg-slate-800 hover:bg-slate-750'
                  }`}
                >
                  <input
                    type="radio"
                    name="gsc_sa"
                    checked={!project.gsc_service_account_id}
                    onChange={() => handleSaSave(null)}
                    disabled={saSaving}
                    className="text-cyan-500 focus:ring-cyan-500/50"
                  />
                  <div>
                    <p className="text-sm text-white">Global (default)</p>
                    <p className="text-xs text-slate-500">Uses the global GSC service account from settings</p>
                  </div>
                </label>

                {serviceAccounts.map((sa) => (
                  <label
                    key={sa.id}
                    className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
                      project.gsc_service_account_id === sa.id ? 'bg-cyan-500/10 border border-cyan-500/20' : 'bg-slate-800 hover:bg-slate-750'
                    }`}
                  >
                    <input
                      type="radio"
                      name="gsc_sa"
                      checked={project.gsc_service_account_id === sa.id}
                      onChange={() => handleSaSave(sa.id)}
                      disabled={saSaving}
                      className="text-cyan-500 focus:ring-cyan-500/50"
                    />
                    <div>
                      <p className="text-sm text-white">{sa.name}</p>
                      <p className="text-xs text-slate-500 font-mono">{sa.email}</p>
                    </div>
                  </label>
                ))}

                {serviceAccounts.length === 0 && (
                  <p className="text-sm text-slate-500">No service accounts available.</p>
                )}
              </div>
            )}

            {saSaving && (
              <div className="flex items-center gap-2 text-slate-400 text-sm">
                <Loader2 size={14} className="animate-spin" />
                Saving...
              </div>
            )}
            {saError && (
              <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm rounded-lg p-3">{saError}</div>
            )}
            {saSuccess && (
              <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm rounded-lg p-3">{saSuccess}</div>
            )}
          </div>
        )}
      </div>

      {/* Add URLs */}
      <div className="bg-slate-900 rounded-xl border border-slate-800">
        <button
          onClick={() => setShowAddUrls((v) => !v)}
          className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-800/50 transition-colors rounded-xl"
        >
          <div className="flex items-center gap-2">
            <Plus size={16} className="text-cyan-400" />
            <span className="text-sm font-medium text-white">Add URLs</span>
          </div>
          {showAddUrls ? <ChevronUp size={16} className="text-slate-500" /> : <ChevronDown size={16} className="text-slate-500" />}
        </button>

        {showAddUrls && (
          <div className="px-5 pb-5 space-y-4 border-t border-slate-800/50 pt-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                URLs (one per line)
              </label>
              <textarea
                value={urlsText}
                onChange={(e) => { setUrlsText(e.target.value); setAddError(''); setAddSuccess(''); }}
                placeholder={"https://example.com/new-page1\nhttps://example.com/new-page2"}
                rows={6}
                className="w-full border border-slate-700 bg-slate-800 text-white placeholder:text-slate-500 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500"
              />
              <label className="inline-flex items-center gap-1 text-sm text-cyan-400 hover:underline cursor-pointer mt-1">
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

            <div className="bg-slate-800 rounded-lg p-3 flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-300">
                  <span className="font-bold text-lg">{parsedUrls.length}</span> URL(s) to add
                </p>
                <p className="text-xs text-slate-500 mt-0.5">
                  Cost: {parsedUrls.length} credit(s) | Balance: {credits}
                </p>
              </div>
              {parsedUrls.length > credits && (
                <span className="text-xs text-rose-400 font-medium">Insufficient credits</span>
              )}
            </div>

            {addError && (
              <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm rounded-lg p-3">{addError}</div>
            )}
            {addSuccess && (
              <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm rounded-lg p-3">{addSuccess}</div>
            )}

            <button
              onClick={handleAddUrls}
              disabled={submitting || parsedUrls.length === 0 || parsedUrls.length > credits}
              className="w-full bg-cyan-500 text-slate-950 py-2.5 rounded-lg text-sm font-medium hover:bg-cyan-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {submitting ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  Submitting...
                </>
              ) : (
                `Add ${parsedUrls.length} URL(s) to project`
              )}
            </button>
          </div>
        )}
      </div>

      {/* Import from GSC */}
      <div className="bg-slate-900 rounded-xl border border-slate-800">
        <button
          onClick={() => setShowGscImport((v) => !v)}
          className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-800/50 transition-colors rounded-xl"
        >
          <div className="flex items-center gap-2">
            <Globe size={16} className="text-cyan-400" />
            <span className="text-sm font-medium text-white">Import from GSC</span>
          </div>
          {showGscImport ? <ChevronUp size={16} className="text-slate-500" /> : <ChevronDown size={16} className="text-slate-500" />}
        </button>

        {showGscImport && (
          <div className="px-5 pb-5 space-y-4 border-t border-slate-800/50 pt-4">
            {gscLoading ? (
              <div className="flex items-center gap-2 text-slate-400 text-sm">
                <Loader2 size={14} className="animate-spin" />
                Loading sitemaps from Search Console...
              </div>
            ) : gscSitemaps.length === 0 && !gscError ? (
              <p className="text-sm text-slate-500">No sitemaps found in Google Search Console.</p>
            ) : (
              <>
                <div className="space-y-2">
                  {gscSitemaps.map((sm) => (
                    <label
                      key={sm.path}
                      className={`flex items-center gap-3 p-3 rounded-lg transition-colors ${
                        sm.imported
                          ? 'bg-emerald-500/5 border border-emerald-500/20 opacity-60 cursor-default'
                          : 'bg-slate-800 hover:bg-slate-750 cursor-pointer'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={gscSelected.has(sm.path)}
                        onChange={() => !sm.imported && toggleGscSitemap(sm.path)}
                        disabled={sm.imported}
                        className="rounded border-slate-600 bg-slate-700 text-cyan-500 focus:ring-cyan-500/50 disabled:opacity-50"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-sm text-white truncate font-mono">{sm.path}</p>
                          {sm.imported && (
                            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-500/15 text-emerald-400 whitespace-nowrap">
                              Imported ({sm.imported_urls})
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-500 mt-0.5">
                          {sm.urls_count} URL{sm.urls_count !== 1 ? 's' : ''}
                          {sm.lastSubmitted && ` · Last submitted: ${new Date(sm.lastSubmitted).toLocaleDateString()}`}
                          {sm.imported_at && ` · Imported: ${new Date(sm.imported_at).toLocaleDateString()}`}
                          {sm.isPending && ' · Pending'}
                        </p>
                      </div>
                    </label>
                  ))}
                </div>

                {gscSelected.size > 0 && (
                  <div className="bg-slate-800 rounded-lg p-3">
                    <p className="text-sm text-slate-300">
                      <span className="font-bold text-lg">{gscSelected.size}</span> sitemap(s) selected
                    </p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Duplicates with existing project URLs will be skipped
                    </p>
                  </div>
                )}
              </>
            )}

            {gscError && (
              <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm rounded-lg p-3">{gscError}</div>
            )}
            {gscSuccess && (
              <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm rounded-lg p-3">{gscSuccess}</div>
            )}

            <button
              onClick={handleGscImport}
              disabled={gscImporting || gscSelected.size === 0}
              className="w-full bg-cyan-500 text-slate-950 py-2.5 rounded-lg text-sm font-medium hover:bg-cyan-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {gscImporting ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  Importing...
                </>
              ) : (
                `Import URLs from ${gscSelected.size} sitemap(s)`
              )}
            </button>
          </div>
        )}
      </div>

      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-slate-300">URLs ({status.total})</h3>
          <button
            onClick={() => exportProjectCsv(id!)}
            className="px-3 py-1.5 text-sm bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:bg-slate-700 transition-colors"
          >
            Export CSV
          </button>
        </div>

        {/* Server-side search & filter */}
        <div className="flex gap-3 mb-4">
          <input
            type="text"
            placeholder="Search URLs..."
            className="flex-1 border border-slate-700 bg-slate-800 text-white placeholder:text-slate-500 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500"
            value={urlSearch}
            onChange={(e) => {
              setUrlSearch(e.target.value);
              if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
              searchTimerRef.current = setTimeout(() => {
                setUrlSearchDebounced(e.target.value);
                setUrlPage(0);
                loadData({ page: 0, search: e.target.value });
              }, 400);
            }}
          />
          <select
            className="border border-slate-700 bg-slate-800 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500"
            value={urlStatusFilter}
            onChange={(e) => {
              setUrlStatusFilter(e.target.value);
              setUrlPage(0);
              loadData({ page: 0, statusF: e.target.value });
            }}
          >
            <option value="all">All statuses</option>
            <option value="pending">Pending</option>
            <option value="submitted">Submitted</option>
            <option value="indexing">Indexing</option>
            <option value="verifying">Verifying</option>
            <option value="indexed">Indexed</option>
            <option value="not_indexed">Not Indexed</option>
            <option value="recredited">Recredited</option>
          </select>
        </div>

        <URLStatusTable urls={status.urls} onRefresh={() => loadData()} serverFiltered />

        {/* Pagination */}
        {status.urls_total > PAGE_SIZE && (() => {
          const totalPages = Math.ceil(status.urls_total / PAGE_SIZE);
          return (
            <div className="flex items-center justify-between mt-4">
              <p className="text-xs text-slate-500">
                {status.offset + 1}–{Math.min(status.offset + status.limit, status.urls_total)} of {status.urls_total} URLs
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => { setUrlPage((p) => { const np = p - 1; loadData({ page: np }); return np; }); }}
                  disabled={urlPage === 0}
                  className="px-3 py-1.5 text-sm bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:bg-slate-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <span className="px-3 py-1.5 text-sm text-slate-400">
                  {urlPage + 1} / {totalPages}
                </span>
                <button
                  onClick={() => { setUrlPage((p) => { const np = p + 1; loadData({ page: np }); return np; }); }}
                  disabled={urlPage >= totalPages - 1}
                  className="px-3 py-1.5 text-sm bg-slate-800 border border-slate-700 text-slate-300 rounded-lg hover:bg-slate-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            </div>
          );
        })()}
      </div>
    </div>
  );
}
