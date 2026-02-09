import { resubmitUrl, checkUrl, deleteUrl } from '../api/client';
import type { URLEntry } from '../api/client';
import {
  RefreshCw, ExternalLink, Search, Zap, Radio, Bell, Archive, Link,
  Clock, Loader2, CheckCircle, XCircle, RotateCcw, SearchCheck, Trash2,
} from 'lucide-react';
import { useState, useCallback } from 'react';

const statusConfig: Record<string, {
  bg: string;
  text: string;
  icon: React.ReactNode;
  label: string;
  tooltip: string;
}> = {
  pending: {
    bg: 'bg-slate-700',
    text: 'text-slate-300',
    icon: <Clock size={12} />,
    label: 'Pending',
    tooltip: 'En attente de traitement',
  },
  submitted: {
    bg: 'bg-cyan-500/15',
    text: 'text-cyan-400',
    icon: <span className="inline-flex h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />,
    label: 'Submitted',
    tooltip: 'Soumise aux moteurs de recherche',
  },
  indexing: {
    bg: 'bg-amber-500/15',
    text: 'text-amber-400',
    icon: <Loader2 size={12} className="animate-spin" />,
    label: 'Indexing',
    tooltip: 'Soumission aux moteurs de recherche en cours',
  },
  verifying: {
    bg: 'bg-blue-500/15',
    text: 'text-blue-400',
    icon: <SearchCheck size={12} />,
    label: 'Verifying',
    tooltip: 'Vérification de l\'indexation en cours',
  },
  indexed: {
    bg: 'bg-slate-700/60',
    text: 'text-slate-300',
    icon: <CheckCircle size={12} />,
    label: 'Indexed',
    tooltip: 'Déjà indexée',
  },
  not_indexed: {
    bg: 'bg-rose-500/15',
    text: 'text-rose-400',
    icon: <XCircle size={12} />,
    label: 'Not Indexed',
    tooltip: 'Non indexée après vérification',
  },
  recredited: {
    bg: 'bg-violet-500/15',
    text: 'text-violet-400',
    icon: <RotateCcw size={12} />,
    label: 'Recredited',
    tooltip: 'Crédit remboursé (non indexée après 14j)',
  },
};

function StatusBadge({ status, indexedByService }: { status: string; indexedByService?: boolean }) {
  const config = statusConfig[status] || {
    bg: 'bg-slate-700', text: 'text-slate-300', icon: null, label: status, tooltip: status,
  };

  const isServiceIndexed = status === 'indexed' && indexedByService;

  if (isServiceIndexed) {
    return (
      <span className="relative group cursor-help">
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-400/40 shadow-[0_0_6px_rgba(16,185,129,0.15)]">
          <CheckCircle size={12} />
          Indexed
        </span>
        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1.5 bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
          Indexée grâce à IndexAI
        </span>
      </span>
    );
  }

  return (
    <span className="relative group cursor-help">
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
        {config.icon}
        {config.label}
      </span>
      <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1.5 bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
        {config.tooltip}
      </span>
    </span>
  );
}

const methodConfig: Record<string, {
  icon: React.ReactNode;
  label: string;
  color: string;      // text color when active
  bg: string;         // pill background when active
  dimBg: string;      // pill background when inactive
}> = {
  google_api: {
    icon: <Search size={12} strokeWidth={2.5} />,
    label: 'Google API',
    color: 'text-blue-400',
    bg: 'bg-blue-500/15',
    dimBg: 'bg-slate-800/60',
  },
  indexnow: {
    icon: <Zap size={12} strokeWidth={2.5} />,
    label: 'IndexNow',
    color: 'text-amber-400',
    bg: 'bg-amber-500/15',
    dimBg: 'bg-slate-800/60',
  },
  pingomatic: {
    icon: <Radio size={12} strokeWidth={2.5} />,
    label: 'Ping-O-Matic',
    color: 'text-violet-400',
    bg: 'bg-violet-500/15',
    dimBg: 'bg-slate-800/60',
  },
  websub: {
    icon: <Bell size={12} strokeWidth={2.5} />,
    label: 'WebSub',
    color: 'text-cyan-400',
    bg: 'bg-cyan-500/15',
    dimBg: 'bg-slate-800/60',
  },
  archive_org: {
    icon: <Archive size={12} strokeWidth={2.5} />,
    label: 'Archive.org',
    color: 'text-orange-400',
    bg: 'bg-orange-500/15',
    dimBg: 'bg-slate-800/60',
  },
  backlink_pings: {
    icon: <Link size={12} strokeWidth={2.5} />,
    label: 'Backlinks',
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/15',
    dimBg: 'bg-slate-800/60',
  },
};

function MethodPill({ method, attempts, lastStatus }: {
  method: string;
  attempts: number;
  lastStatus?: string | null;
}) {
  const config = methodConfig[method];
  if (!config) return null;

  const active = attempts > 0;
  const isError = active && lastStatus === 'error';

  const pillBg = isError ? 'bg-rose-500/10' : active ? config.bg : config.dimBg;
  const iconColor = isError ? 'text-rose-400' : active ? config.color : 'text-slate-600';
  const countColor = isError ? 'text-rose-400/80' : active ? config.color : '';

  const statusText = isError ? 'Erreur' : lastStatus === 'success' ? 'OK' : '';

  return (
    <span className="relative group cursor-help">
      <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md ${pillBg} transition-colors`}>
        <span className={iconColor}>{config.icon}</span>
        {active && (
          <span className={`text-[10px] font-semibold leading-none tabular-nums ${countColor}`}>
            {attempts}
          </span>
        )}
      </span>
      <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1.5 bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
        <span className="font-medium">{config.label}</span>
        {active ? (
          <span className="text-slate-400"> — {attempts}x{statusText ? ` · ${statusText}` : ''}</span>
        ) : (
          <span className="text-slate-500"> — en attente</span>
        )}
      </span>
    </span>
  );
}

interface Props {
  urls: URLEntry[];
  onRefresh?: () => void;
  serverFiltered?: boolean;
}

export default function URLStatusTable({ urls, onRefresh, serverFiltered }: Props) {
  const [filter, setFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [resubmittingId, setResubmittingId] = useState<string | null>(null);
  const [resubmittedId, setResubmittedId] = useState<string | null>(null);
  const [checkingId, setCheckingId] = useState<string | null>(null);
  const [checkedId, setCheckedId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const filtered = serverFiltered ? urls : urls.filter((u) => {
    const matchUrl = u.url.toLowerCase().includes(filter.toLowerCase());
    const matchStatus = statusFilter === 'all' || u.status === statusFilter;
    return matchUrl && matchStatus;
  });

  const handleResubmit = useCallback(async (urlId: string) => {
    setResubmittingId(urlId);
    setActionError(null);
    try {
      await resubmitUrl(urlId);
      setResubmittedId(urlId);
      setTimeout(() => setResubmittedId(null), 1500);
      onRefresh?.();
    } catch (e: any) {
      setActionError(e.message || 'Resubmit failed');
      setTimeout(() => setActionError(null), 3000);
    } finally {
      setResubmittingId(null);
    }
  }, [onRefresh]);

  const handleCheck = useCallback(async (urlId: string) => {
    setCheckingId(urlId);
    setActionError(null);
    try {
      await checkUrl(urlId);
      setCheckedId(urlId);
      setTimeout(() => setCheckedId(null), 1500);
      onRefresh?.();
    } catch (e: any) {
      setActionError(e.message || 'Check failed');
      setTimeout(() => setActionError(null), 3000);
    } finally {
      setCheckingId(null);
    }
  }, [onRefresh]);

  const handleDelete = useCallback(async (urlId: string) => {
    setDeletingId(urlId);
    setActionError(null);
    try {
      await deleteUrl(urlId);
      setConfirmDeleteId(null);
      onRefresh?.();
    } catch (e: any) {
      setActionError(e.message || 'Delete failed');
      setTimeout(() => setActionError(null), 3000);
    } finally {
      setDeletingId(null);
    }
  }, [onRefresh]);

  const isRowActive = (status: string) => status === 'submitted' || status === 'indexing' || status === 'verifying';
  const isIndexedByService = (u: URLEntry) => u.status === 'indexed' && u.verified_not_indexed;

  return (
    <div>
      {actionError && (
        <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm rounded-lg p-3 mb-3">{actionError}</div>
      )}
      {!serverFiltered && (
        <div className="flex gap-3 mb-4">
          <input
            type="text"
            placeholder="Search URLs..."
            className="flex-1 border border-slate-700 bg-slate-800 text-white placeholder:text-slate-500 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          <select
            className="border border-slate-700 bg-slate-800 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
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
      )}

      <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-800/50 border-b border-slate-800">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-slate-400">URL</th>
              <th className="text-left px-4 py-3 font-medium text-slate-400">Status</th>
              <th className="text-center px-4 py-3 font-medium text-slate-400">Methods</th>
              <th className="text-left px-4 py-3 font-medium text-slate-400">Last Check</th>
              <th className="text-left px-4 py-3 font-medium text-slate-400">Proof</th>
              <th className="text-center px-4 py-3 font-medium text-slate-400">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {filtered.map((u) => (
              <tr
                key={u.id}
                className={`hover:bg-slate-800/50 transition-colors ${
                  isRowActive(u.status) ? 'bg-cyan-500/5' : ''
                }`}
              >
                <td className="px-4 py-3 max-w-xs">
                  <a
                    href={u.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-cyan-400 hover:underline truncate block"
                    title={u.url}
                  >
                    {u.url.length > 60 ? u.url.slice(0, 60) + '...' : u.url}
                    <ExternalLink size={12} className="inline ml-1" />
                  </a>
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={u.status} indexedByService={isIndexedByService(u)} />
                </td>
                <td className="px-4 py-3 text-center">
                  <div className="flex justify-center gap-1">
                    <MethodPill method="google_api" attempts={u.google_api_attempts} lastStatus={u.google_api_last_status} />
                    <MethodPill method="indexnow" attempts={u.indexnow_attempts} lastStatus={u.indexnow_last_status} />
                    <MethodPill method="pingomatic" attempts={u.social_signal_attempts} />
                    <MethodPill method="websub" attempts={u.social_signal_attempts} />
                    <MethodPill method="archive_org" attempts={u.social_signal_attempts} />
                    <MethodPill method="backlink_pings" attempts={u.backlink_ping_attempts} />
                  </div>
                </td>
                <td className="px-4 py-3 text-slate-500 text-xs">
                  {u.last_checked_at ? (
                    <span title={new Date(u.last_checked_at).toLocaleString()}>
                      {new Date(u.last_checked_at).toLocaleDateString()}
                    </span>
                  ) : (
                    <span className="text-slate-600 italic" title="Aucune vérification effectuée pour le moment">
                      Pas encore vérifié
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-xs text-slate-400 max-w-xs">
                  {u.indexed_title ? (
                    <div>
                      <div className="font-medium truncate">{u.indexed_title}</div>
                      {u.indexed_snippet && <div className="text-slate-500 truncate">{u.indexed_snippet}</div>}
                    </div>
                  ) : '-'}
                </td>
                <td className="px-4 py-3 text-center">
                  <div className="flex items-center justify-center gap-1">
                    {u.status !== 'indexed' && (
                      <span className="relative group">
                        <button
                          onClick={() => handleResubmit(u.id)}
                          disabled={resubmittingId === u.id}
                          className="text-cyan-400 hover:text-cyan-300 p-1 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                          {resubmittingId === u.id ? (
                            <Loader2 size={14} className="animate-spin" />
                          ) : resubmittedId === u.id ? (
                            <CheckCircle size={14} className="text-emerald-400" />
                          ) : (
                            <RefreshCw size={14} />
                          )}
                        </button>
                        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1.5 bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                          Resoumettre cette URL pour indexation
                        </span>
                      </span>
                    )}
                    <span className="relative group">
                      <button
                        onClick={() => handleCheck(u.id)}
                        disabled={checkingId === u.id}
                        className="text-amber-400 hover:text-amber-300 p-1 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        {checkingId === u.id ? (
                          <Loader2 size={14} className="animate-spin" />
                        ) : checkedId === u.id ? (
                          <CheckCircle size={14} className="text-emerald-400" />
                        ) : (
                          <SearchCheck size={14} />
                        )}
                      </button>
                      <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1.5 bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                        Vérifier si cette URL est indexée
                      </span>
                    </span>
                    <span className="relative group">
                      {confirmDeleteId === u.id ? (
                        <span className="inline-flex items-center gap-1">
                          <button
                            onClick={() => handleDelete(u.id)}
                            disabled={deletingId === u.id}
                            className="text-rose-400 hover:text-rose-300 text-xs font-medium px-1.5 py-0.5 bg-rose-500/10 rounded disabled:opacity-50 transition-colors"
                          >
                            {deletingId === u.id ? <Loader2 size={12} className="animate-spin" /> : 'Oui'}
                          </button>
                          <button
                            onClick={() => setConfirmDeleteId(null)}
                            className="text-slate-400 hover:text-slate-300 text-xs px-1.5 py-0.5 transition-colors"
                          >
                            Non
                          </button>
                        </span>
                      ) : (
                        <>
                          <button
                            onClick={() => setConfirmDeleteId(u.id)}
                            className="text-slate-500 hover:text-rose-400 p-1 transition-colors"
                          >
                            <Trash2 size={14} />
                          </button>
                          <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1.5 bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                            Supprimer cette URL
                          </span>
                        </>
                      )}
                    </span>
                  </div>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                  No URLs found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-500 mt-2">{filtered.length} URLs shown</p>
    </div>
  );
}
