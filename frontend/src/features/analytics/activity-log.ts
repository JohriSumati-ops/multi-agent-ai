/**
 * Session activity log.
 *
 * The backend has no history/audit-log endpoints (no way to list past
 * `/orchestration/execute` runs, `/research/query` calls, or searches —
 * see `docs/Phase7.md` §5). Rather than fabricate an activity trend from
 * nothing, the Analytics page logs the *real* actions this browser takes
 * against the real API — each entry is written at the moment an actual
 * mutation resolves, using real response data (e.g. `latency_ms` from the
 * research endpoint) where the backend provides it, or a client-measured
 * wall-clock duration otherwise.
 *
 * This is intentionally scoped as "activity since it started being
 * recorded in this browser", not "all-time history" — that distinction is
 * surfaced in the Analytics UI copy, not hidden.
 */

export type ActivityType = "upload" | "search" | "research" | "orchestration" | "memory";

export interface ActivityEntry {
  id: string;
  type: ActivityType;
  label: string;
  success: boolean;
  latencyMs: number | null;
  /** True if latencyMs came straight from the backend response rather than being measured client-side. */
  latencySource: "server" | "client" | null;
  timestamp: string;
}

const ACTIVITY_LOG_KEY = "maara_activity_log";
const ACTIVITY_LOG_EVENT = "maara-activity-log-updated";
const MAX_ENTRIES = 300;

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export function getActivityLog(): ActivityEntry[] {
  if (!isBrowser()) return [];
  try {
    const raw = window.localStorage.getItem(ACTIVITY_LOG_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ActivityEntry[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function logActivity(entry: Omit<ActivityEntry, "id" | "timestamp">): void {
  if (!isBrowser()) return;
  const next: ActivityEntry = {
    ...entry,
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    timestamp: new Date().toISOString(),
  };
  const existing = getActivityLog();
  const trimmed = [next, ...existing].slice(0, MAX_ENTRIES);
  window.localStorage.setItem(ACTIVITY_LOG_KEY, JSON.stringify(trimmed));
  window.dispatchEvent(new Event(ACTIVITY_LOG_EVENT));
}

export function clearActivityLog(): void {
  if (!isBrowser()) return;
  window.localStorage.removeItem(ACTIVITY_LOG_KEY);
  window.dispatchEvent(new Event(ACTIVITY_LOG_EVENT));
}

export function subscribeToActivityLog(callback: () => void): () => void {
  if (!isBrowser()) return () => {};
  window.addEventListener(ACTIVITY_LOG_EVENT, callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener(ACTIVITY_LOG_EVENT, callback);
    window.removeEventListener("storage", callback);
  };
}
