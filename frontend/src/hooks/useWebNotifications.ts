import { useEffect, useRef } from 'react';
import { getRecentNotifications, isAuthenticated } from '../api/client';

const STORAGE_KEY = 'indexai_web_notifs_enabled';
const POLL_INTERVAL = 15_000; // 15 seconds

export function isWebNotificationsEnabled(): boolean {
  return localStorage.getItem(STORAGE_KEY) === 'true';
}

export function setWebNotificationsEnabled(enabled: boolean) {
  localStorage.setItem(STORAGE_KEY, String(enabled));
}

export default function useWebNotifications() {
  const shownIds = useRef<Set<string>>(new Set());
  const lastCheck = useRef<string>(new Date().toISOString());

  useEffect(() => {
    if (!isWebNotificationsEnabled()) return;
    if (!isAuthenticated()) return;
    if (typeof Notification === 'undefined') return;

    const poll = async () => {
      if (!isWebNotificationsEnabled()) return;
      if (Notification.permission !== 'granted') return;

      try {
        const items = await getRecentNotifications(lastCheck.current);
        for (const item of items) {
          if (shownIds.current.has(item.id)) continue;
          shownIds.current.add(item.id);

          new Notification('URL indexed', {
            body: item.title || item.url,
            icon: '/favicon.ico',
            tag: item.id,
          });
        }
        lastCheck.current = new Date().toISOString();
      } catch {
        // silently ignore polling errors
      }
    };

    // Initial check after a short delay
    const timeout = setTimeout(poll, 3000);
    const interval = setInterval(poll, POLL_INTERVAL);

    return () => {
      clearTimeout(timeout);
      clearInterval(interval);
    };
  }, []);
}
