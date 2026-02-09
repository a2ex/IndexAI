const API_BASE = '/api';

let accessToken = '';
let refreshPromise: Promise<boolean> | null = null;

export function setAccessToken(token: string) {
  accessToken = token;
}

export function getAccessToken(): string {
  return accessToken;
}

export function clearAccessToken() {
  accessToken = '';
}

export function isAuthenticated(): boolean {
  return !!accessToken;
}

// Auth API

export async function login(email: string, password: string): Promise<void> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }
  const data = await res.json();
  accessToken = data.access_token;
}

export async function register(email: string, password: string): Promise<void> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }
  const data = await res.json();
  accessToken = data.access_token;
}

export async function refreshToken(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    });
    if (!res.ok) {
      accessToken = '';
      return false;
    }
    const data = await res.json();
    accessToken = data.access_token;
    return true;
  } catch {
    accessToken = '';
    return false;
  }
}

export async function logout(): Promise<void> {
  await fetch(`${API_BASE}/auth/logout`, {
    method: 'POST',
    credentials: 'include',
  }).catch(() => {});
  accessToken = '';
}

// Generic request with auto-refresh

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }

  let res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: 'include',
  });

  // If 401, try to refresh the token once and retry
  if (res.status === 401 && accessToken) {
    if (!refreshPromise) {
      refreshPromise = refreshToken();
    }
    const refreshed = await refreshPromise;
    refreshPromise = null;

    if (refreshed) {
      headers['Authorization'] = `Bearer ${accessToken}`;
      res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
        credentials: 'include',
      });
    }
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

export interface UserProfile {
  id: string;
  email: string;
  credit_balance: number;
  is_admin: boolean;
  created_at: string;
}

export const getMe = () => request<UserProfile>('/auth/me');

export interface User {
  id: string;
  email: string;
  api_key: string;
  credit_balance: number;
  created_at: string;
}

export interface ProjectSummary {
  id: string;
  name: string;
  status: string;
  total_urls: number;
  indexed_count: number;
  not_indexed_count: number;
  recredited_count: number;
  pending_count: number;
  main_domain: string | null;
  created_at: string;
}

export interface URLEntry {
  id: string;
  url: string;
  status: string;
  google_api_attempts: number;
  indexnow_attempts: number;
  sitemap_ping_attempts: number;
  social_signal_attempts: number;
  backlink_ping_attempts: number;
  google_api_last_status: string | null;
  indexnow_last_status: string | null;
  is_indexed: boolean;
  indexed_at: string | null;
  last_checked_at: string | null;
  check_count: number;
  check_method: string | null;
  indexed_title: string | null;
  indexed_snippet: string | null;
  credit_debited: boolean;
  credit_refunded: boolean;
  pre_indexed: boolean;
  verified_not_indexed: boolean;
  submitted_at: string | null;
  created_at: string;
}

export interface ProjectDetail {
  id: string;
  name: string;
  description: string | null;
  status: string;
  total_urls: number;
  indexed_count: number;
  failed_count: number;
  main_domain: string | null;
  gsc_service_account_id: string | null;
  created_at: string;
  updated_at: string;
  urls: URLEntry[];
}

export interface ProjectStatus {
  total: number;
  indexed: number;
  pending: number;
  not_indexed: number;
  recredited: number;
  verifying: number;
  indexed_by_service: number;
  success_rate: number;
  urls: URLEntry[];
  urls_total: number;
  limit: number;
  offset: number;
}

export interface CreditBalance {
  balance: number;
  user_id: string;
}

export interface CreditTransaction {
  id: string;
  amount: number;
  type: string;
  description: string | null;
  url_id: string | null;
  created_at: string;
}

// Users
export const createUser = (email: string) =>
  request<User>('/users', { method: 'POST', body: JSON.stringify({ email }) });

// Projects
export const listProjects = () =>
  request<ProjectSummary[]>('/projects');

export const getProject = (id: string) =>
  request<ProjectDetail>(`/projects/${id}`);

export const getProjectStatus = (
  id: string,
  opts?: { limit?: number; offset?: number; status?: string; search?: string },
) => {
  const params = new URLSearchParams();
  if (opts?.limit) params.set('limit', String(opts.limit));
  if (opts?.offset) params.set('offset', String(opts.offset));
  if (opts?.status && opts.status !== 'all') params.set('status', opts.status);
  if (opts?.search) params.set('search', opts.search);
  const qs = params.toString();
  return request<ProjectStatus>(`/projects/${id}/status${qs ? `?${qs}` : ''}`);
};

export const createProject = (data: { name: string; urls: string[]; description?: string }) =>
  request<ProjectDetail>('/projects', { method: 'POST', body: JSON.stringify(data) });

export interface DailyStats {
  date: string;
  submitted: number;
  indexed: number;
}

export const getDailyStats = (days = 30) =>
  request<DailyStats[]>(`/projects/stats/daily?days=${days}`);

export interface IndexingSpeedStats {
  indexed_24h: number;
  indexed_48h: number;
  indexed_72h: number;
  indexed_7d: number;
  total_submitted: number;
  pct_24h: number;
  pct_48h: number;
  pct_72h: number;
  pct_7d: number;
}

export interface MethodStats {
  total_attempts: number;
  success: number;
  error: number;
  rate: number;
}

export interface IndexingStats {
  speed: IndexingSpeedStats;
  methods: Record<string, MethodStats>;
  indexed_by_service: number;
}

export const getIndexingStats = () =>
  request<IndexingStats>(`/projects/stats/indexing`);

export const addUrls = (projectId: string, urls: string[]) =>
  request<{ added: number; total_urls: number; credits_debited: number }>(
    `/projects/${projectId}/urls`,
    { method: 'POST', body: JSON.stringify({ urls }) },
  );

export const updateProject = (id: string, data: { gsc_service_account_id: string | null }) =>
  request<{ ok: boolean; gsc_service_account_id: string | null }>(
    `/projects/${id}`,
    { method: 'PATCH', body: JSON.stringify(data) },
  );

// Service Accounts
export interface ServiceAccountSummary {
  id: string;
  name: string;
  email: string;
}

export const listServiceAccounts = () =>
  request<ServiceAccountSummary[]>('/service-accounts');

// URLs
export const resubmitUrl = (urlId: string) =>
  request<{ message: string }>(`/urls/${urlId}/resubmit`, { method: 'POST' });

export const checkUrl = (urlId: string) =>
  request<{ message: string }>(`/urls/${urlId}/check`, { method: 'POST' });

export const deleteUrl = (urlId: string) =>
  request<{ message: string; credit_refunded: boolean }>(`/urls/${urlId}`, { method: 'DELETE' });

export const triggerVerification = (projectId: string) =>
  request<{ queued: number }>(`/projects/${projectId}/verify-now`, { method: 'POST' });

// Credits
export const getCredits = () =>
  request<CreditBalance>('/credits');

export const getCreditHistory = (limit = 50, offset = 0) =>
  request<CreditTransaction[]>(`/credits/history?limit=${limit}&offset=${offset}`);

export const addCredits = (amount: number) =>
  request<{ balance: number; added: number }>(`/credits/add?amount=${amount}`, { method: 'POST' });

// Notifications
export interface RecentNotification {
  id: string;
  url: string;
  indexed_at: string | null;
  title: string | null;
}

export const getRecentNotifications = (since?: string) =>
  request<RecentNotification[]>(`/notifications/recent${since ? `?since=${encodeURIComponent(since)}` : ''}`);

// GSC Sitemaps
export interface GscSitemap {
  path: string;
  lastSubmitted: string;
  urls_count: number;
  isPending: boolean;
  imported: boolean;
  imported_urls: number;
  imported_at: string | null;
}

export interface GscImportResult {
  added: number;
  duplicates_skipped: number;
  credits_debited: number;
}

export const getGscSitemaps = (projectId: string) =>
  request<GscSitemap[]>(`/projects/${projectId}/gsc-sitemaps`);

export const importGscUrls = (projectId: string, sitemapUrls: string[]) =>
  request<GscImportResult>(
    `/projects/${projectId}/import-gsc`,
    { method: 'POST', body: JSON.stringify({ sitemap_urls: sitemapUrls }) },
  );

// Export
export async function exportProjectCsv(projectId: string): Promise<void> {
  const headers: Record<string, string> = {};
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }
  const res = await fetch(`${API_BASE}/projects/${projectId}/export/csv`, {
    headers,
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Export failed');
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `project_${projectId}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
