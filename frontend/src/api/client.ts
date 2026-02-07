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
  failed_count: number;
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
  is_indexed: boolean;
  indexed_at: string | null;
  last_checked_at: string | null;
  check_count: number;
  check_method: string | null;
  indexed_title: string | null;
  indexed_snippet: string | null;
  credit_debited: boolean;
  credit_refunded: boolean;
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
  success_rate: number;
  urls: URLEntry[];
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

export const getProjectStatus = (id: string) =>
  request<ProjectStatus>(`/projects/${id}/status`);

export const createProject = (data: { name: string; urls: string[]; description?: string }) =>
  request<ProjectDetail>('/projects', { method: 'POST', body: JSON.stringify(data) });

export interface DailyStats {
  date: string;
  submitted: number;
  indexed: number;
}

export const getDailyStats = (days = 30) =>
  request<DailyStats[]>(`/projects/stats/daily?days=${days}`);

export const addUrls = (projectId: string, urls: string[]) =>
  request<{ added: number; total_urls: number; credits_debited: number }>(
    `/projects/${projectId}/urls`,
    { method: 'POST', body: JSON.stringify({ urls }) },
  );

// URLs
export const resubmitUrl = (urlId: string) =>
  request<{ message: string }>(`/urls/${urlId}/resubmit`, { method: 'POST' });

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
