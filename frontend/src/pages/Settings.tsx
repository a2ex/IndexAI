import { useEffect, useState } from 'react';
import { getAccessToken } from '../api/client';
import { Shield, Trash2, PlayCircle, Upload, CheckCircle, XCircle, AlertCircle, Bell } from 'lucide-react';
import { isWebNotificationsEnabled, setWebNotificationsEnabled } from '../hooks/useWebNotifications';

const API_BASE = '/api';
const authHeaders = () => ({
  'Authorization': `Bearer ${getAccessToken()}`,
});

interface ServiceAccount {
  id: string;
  name: string;
  email: string;
  daily_quota: number;
  used_today: number;
  is_active: boolean;
  created_at: string;
}

interface GoogleSettings {
  google_custom_search_api_key: string;
  google_cse_id: string;
  credentials_dir: string;
  base_url: string;
}

interface TestResult {
  success: boolean;
  status_code?: number;
  message?: string;
  error?: string;
}

export default function Settings() {
  const [accounts, setAccounts] = useState<ServiceAccount[]>([]);
  const [googleSettings, setGoogleSettings] = useState<GoogleSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({});

  // Upload form
  const [saName, setSaName] = useState('');
  const [saFile, setSaFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState('');

  // Google API settings form
  const [cseApiKey, setCseApiKey] = useState('');
  const [cseId, setCseId] = useState('');
  const [savingSettings, setSavingSettings] = useState(false);

  // Web notifications
  const [webNotifsEnabled, setWebNotifsEnabled] = useState(isWebNotificationsEnabled());
  const [notifPermission, setNotifPermission] = useState(
    typeof Notification !== 'undefined' ? Notification.permission : 'default'
  );

  const loadData = async () => {
    try {
      const [saRes, settingsRes] = await Promise.all([
        fetch(`${API_BASE}/admin/service-accounts`, { headers: authHeaders() }),
        fetch(`${API_BASE}/admin/settings`, { headers: authHeaders() }),
      ]);
      setAccounts(await saRes.json());
      setGoogleSettings(await settingsRes.json());
    } catch {
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const handleUpload = async () => {
    if (!saName || !saFile) return;
    setUploading(true);
    setUploadMsg('');

    const formData = new FormData();
    formData.append('name', saName);
    formData.append('json_key', saFile);
    formData.append('daily_quota', '200');

    try {
      const res = await fetch(`${API_BASE}/admin/service-accounts`, {
        method: 'POST',
        headers: authHeaders(),
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        setUploadMsg(`Added: ${data.email}`);
        setSaName('');
        setSaFile(null);
        loadData();
      } else {
        setUploadMsg(`Error: ${data.detail}`);
      }
    } catch (e: any) {
      setUploadMsg(`Error: ${e.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleTest = async (saId: string) => {
    setTestResults((prev) => ({ ...prev, [saId]: { success: false, message: 'Testing...' } }));
    try {
      const res = await fetch(`${API_BASE}/admin/service-accounts/${saId}/test`, {
        method: 'POST',
        headers: authHeaders(),
      });
      const data = await res.json();
      setTestResults((prev) => ({ ...prev, [saId]: data }));
    } catch (e: any) {
      setTestResults((prev) => ({ ...prev, [saId]: { success: false, error: e.message } }));
    }
  };

  const handleDelete = async (saId: string) => {
    if (!confirm('Delete this service account?')) return;
    await fetch(`${API_BASE}/admin/service-accounts/${saId}`, {
      method: 'DELETE',
      headers: authHeaders(),
    });
    loadData();
  };

  const handleSaveSettings = async () => {
    setSavingSettings(true);
    const formData = new FormData();
    if (cseApiKey) formData.append('google_custom_search_api_key', cseApiKey);
    if (cseId) formData.append('google_cse_id', cseId);

    await fetch(`${API_BASE}/admin/settings`, {
      method: 'POST',
      headers: authHeaders(),
      body: formData,
    });
    setCseApiKey('');
    setCseId('');
    loadData();
    setSavingSettings(false);
  };

  const handleToggleWebNotifs = async (enabled: boolean) => {
    if (enabled && typeof Notification !== 'undefined' && Notification.permission === 'default') {
      const permission = await Notification.requestPermission();
      setNotifPermission(permission);
      if (permission !== 'granted') return;
    }
    setWebNotifsEnabled(enabled);
    setWebNotificationsEnabled(enabled);
  };

  if (loading) return <div className="text-gray-400">Loading...</div>;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Settings</h2>
        <p className="text-sm text-gray-500 mt-1">Google API configuration</p>
      </div>

      {/* Google Custom Search Settings */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-sm font-medium text-gray-900 mb-4">Google Custom Search API</h3>
        <p className="text-xs text-gray-500 mb-4">Used to verify if URLs are indexed in Google.</p>

        {googleSettings && (
          <div className="bg-gray-50 rounded-lg p-3 mb-4 text-xs text-gray-600 space-y-1">
            <p>API Key: <span className="font-mono">{googleSettings.google_custom_search_api_key}</span></p>
            <p>CSE ID: <span className="font-mono">{googleSettings.google_cse_id}</span></p>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Custom Search API Key</label>
            <input
              type="text"
              value={cseApiKey}
              onChange={(e) => setCseApiKey(e.target.value)}
              placeholder="AIza..."
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Search Engine ID (cx)</label>
            <input
              type="text"
              value={cseId}
              onChange={(e) => setCseId(e.target.value)}
              placeholder="a1b2c3d4e5f..."
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
        <button
          onClick={handleSaveSettings}
          disabled={savingSettings || (!cseApiKey && !cseId)}
          className="mt-3 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          {savingSettings ? 'Saving...' : 'Save Settings'}
        </button>
      </div>

      {/* Notifications */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Bell size={18} className="text-gray-700" />
          <h3 className="text-sm font-medium text-gray-900">Notifications</h3>
        </div>

        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={webNotifsEnabled}
            onChange={(e) => handleToggleWebNotifs(e.target.checked)}
            className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
          />
          <div>
            <span className="text-sm font-medium text-gray-900">Notifications web</span>
            <p className="text-xs text-gray-500">Receive a browser notification when a URL is indexed</p>
          </div>
        </label>

        {webNotifsEnabled && notifPermission === 'denied' && (
          <p className="mt-3 text-xs text-red-500">
            Notifications are blocked by your browser. Allow them in your browser settings for this site.
          </p>
        )}
        {webNotifsEnabled && notifPermission === 'granted' && (
          <p className="mt-3 text-xs text-green-600">
            Notifications are active. You will be notified when a URL is indexed.
          </p>
        )}
      </div>

      {/* Service Accounts */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-sm font-medium text-gray-900 mb-4">Google Service Accounts</h3>
        <p className="text-xs text-gray-500 mb-4">
          Service accounts for Google Indexing API. Each account has a 200 URLs/day quota.
        </p>

        {/* Upload form */}
        <div className="bg-gray-50 rounded-lg p-4 mb-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Account Name</label>
              <input
                type="text"
                value={saName}
                onChange={(e) => setSaName(e.target.value)}
                placeholder="indexai-sa-1"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">JSON Key File</label>
              <label className="flex items-center gap-2 border border-gray-300 rounded-lg px-3 py-2 text-sm cursor-pointer hover:bg-white transition-colors">
                <Upload size={14} />
                <span className="truncate">{saFile ? saFile.name : 'Choose file...'}</span>
                <input
                  type="file"
                  accept=".json"
                  onChange={(e) => setSaFile(e.target.files?.[0] || null)}
                  className="hidden"
                />
              </label>
            </div>
            <button
              onClick={handleUpload}
              disabled={uploading || !saName || !saFile}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {uploading ? 'Uploading...' : 'Add Account'}
            </button>
          </div>
          {uploadMsg && (
            <p className={`text-xs mt-2 ${uploadMsg.startsWith('Error') ? 'text-red-500' : 'text-green-600'}`}>
              {uploadMsg}
            </p>
          )}
        </div>

        {/* Accounts list */}
        {accounts.length === 0 ? (
          <div className="text-center py-6 text-gray-400 text-sm">
            No service accounts registered yet
          </div>
        ) : (
          <div className="space-y-3">
            {accounts.map((sa) => (
              <div key={sa.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Shield size={18} className={sa.is_active ? 'text-green-500' : 'text-gray-400'} />
                    <div>
                      <p className="text-sm font-medium text-gray-900">{sa.name}</p>
                      <p className="text-xs text-gray-500 font-mono">{sa.email}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="text-sm font-medium text-gray-700">
                        {sa.used_today}/{sa.daily_quota}
                      </p>
                      <p className="text-xs text-gray-400">used today</p>
                    </div>
                    <button
                      onClick={() => handleTest(sa.id)}
                      className="text-blue-600 hover:text-blue-800 p-1"
                      title="Test connection"
                    >
                      <PlayCircle size={18} />
                    </button>
                    <button
                      onClick={() => handleDelete(sa.id)}
                      className="text-red-500 hover:text-red-700 p-1"
                      title="Delete"
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                </div>

                {testResults[sa.id] && (
                  <div className={`mt-2 flex items-center gap-2 text-xs ${testResults[sa.id].success ? 'text-green-600' : 'text-red-500'}`}>
                    {testResults[sa.id].success ? <CheckCircle size={14} /> : testResults[sa.id].error ? <XCircle size={14} /> : <AlertCircle size={14} />}
                    {testResults[sa.id].message || testResults[sa.id].error || 'Unknown'}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
