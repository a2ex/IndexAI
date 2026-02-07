import { resubmitUrl } from '../api/client';
import type { URLEntry } from '../api/client';
import { RefreshCw, ExternalLink, Search, Rss, Share2, Link2 } from 'lucide-react';
import { useState } from 'react';

const statusColors: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-700',
  submitted: 'bg-blue-100 text-blue-700',
  indexing: 'bg-yellow-100 text-yellow-700',
  indexed: 'bg-green-100 text-green-700',
  not_indexed: 'bg-red-100 text-red-700',
  recredited: 'bg-purple-100 text-purple-700',
};

interface Props {
  urls: URLEntry[];
  onRefresh?: () => void;
}

export default function URLStatusTable({ urls, onRefresh }: Props) {
  const [filter, setFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const filtered = urls.filter((u) => {
    const matchUrl = u.url.toLowerCase().includes(filter.toLowerCase());
    const matchStatus = statusFilter === 'all' || u.status === statusFilter;
    return matchUrl && matchStatus;
  });

  const handleResubmit = async (urlId: string) => {
    await resubmitUrl(urlId);
    onRefresh?.();
  };

  return (
    <div>
      <div className="flex gap-3 mb-4">
        <input
          type="text"
          placeholder="Search URLs..."
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        <select
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="all">All statuses</option>
          <option value="pending">Pending</option>
          <option value="submitted">Submitted</option>
          <option value="indexing">Indexing</option>
          <option value="indexed">Indexed</option>
          <option value="not_indexed">Not Indexed</option>
          <option value="recredited">Recredited</option>
        </select>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">URL</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
              <th className="text-center px-4 py-3 font-medium text-gray-600">Methods</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Last Check</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Proof</th>
              <th className="text-center px-4 py-3 font-medium text-gray-600">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filtered.map((u) => (
              <tr key={u.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 max-w-xs">
                  <a
                    href={u.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline truncate block"
                    title={u.url}
                  >
                    {u.url.length > 60 ? u.url.slice(0, 60) + '...' : u.url}
                    <ExternalLink size={12} className="inline ml-1" />
                  </a>
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[u.status] || 'bg-gray-100'}`}>
                    {u.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <div className="flex justify-center gap-1.5">
                    {u.google_api_attempts > 0 && (
                      <span className="relative group cursor-help">
                        <Search size={14} className="text-blue-500" />
                        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1.5 bg-gray-900 text-white text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                          Google Indexing API — {u.google_api_attempts} request(s) sent to Google to index this URL
                        </span>
                      </span>
                    )}
                    {u.indexnow_attempts > 0 && (
                      <span className="relative group cursor-help">
                        <Rss size={14} className="text-orange-500" />
                        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1.5 bg-gray-900 text-white text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                          IndexNow — {u.indexnow_attempts} ping(s) sent to Bing & Yandex
                        </span>
                      </span>
                    )}
                    {u.sitemap_ping_attempts > 0 && (
                      <span className="relative group cursor-help">
                        <Share2 size={14} className="text-green-500" />
                        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1.5 bg-gray-900 text-white text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                          Sitemap Ping — {u.sitemap_ping_attempts} sitemap ping(s) via PubSubHubbub
                        </span>
                      </span>
                    )}
                    {u.social_signal_attempts > 0 && (
                      <span className="relative group cursor-help">
                        <Link2 size={14} className="text-purple-500" />
                        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1.5 bg-gray-900 text-white text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                          Social Signals — {u.social_signal_attempts} social ping(s) to generate crawl signals
                        </span>
                      </span>
                    )}
                    {u.backlink_ping_attempts > 0 && (
                      <span className="relative group cursor-help">
                        <ExternalLink size={14} className="text-red-500" />
                        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1.5 bg-gray-900 text-white text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                          Backlink Pings — {u.backlink_ping_attempts} ping(s) to Ping-O-Matic & directories
                        </span>
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs">
                  {u.last_checked_at ? new Date(u.last_checked_at).toLocaleDateString() : '-'}
                </td>
                <td className="px-4 py-3 text-xs text-gray-600 max-w-xs">
                  {u.indexed_title ? (
                    <div>
                      <div className="font-medium truncate">{u.indexed_title}</div>
                      {u.indexed_snippet && <div className="text-gray-400 truncate">{u.indexed_snippet}</div>}
                    </div>
                  ) : '-'}
                </td>
                <td className="px-4 py-3 text-center">
                  {u.status !== 'indexed' && (
                    <button
                      onClick={() => handleResubmit(u.id)}
                      className="text-blue-600 hover:text-blue-800 p-1"
                      title="Resubmit"
                    >
                      <RefreshCw size={14} />
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                  No URLs found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-gray-400 mt-2">{filtered.length} URLs shown</p>
    </div>
  );
}
