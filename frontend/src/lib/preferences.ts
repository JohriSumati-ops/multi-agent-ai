/**
 * Client-side user preferences.
 *
 * The backend exposes no settings/preferences/notification endpoints (see
 * `docs/Phase7.md` §5 and `docs/Phase8.md`) — there is no server-side place
 * to persist these, so — consistent with how theme is already handled in
 * `context/theme-provider.tsx` — everything here lives in `localStorage`
 * only. It's per-browser, not per-account, and is documented as such on the
 * Settings page rather than presented as a synced server preference.
 */

export interface RetrievalPreferences {
  defaultTopK: number;
  defaultSimilarityThreshold: number;
}

export interface MemoryPreferences {
  defaultPruneKeepTopN: number;
}

export interface NotificationPreferences {
  documents: boolean;
  memory: boolean;
  research: boolean;
  orchestration: boolean;
}

export interface Preferences {
  retrieval: RetrievalPreferences;
  memory: MemoryPreferences;
  notifications: NotificationPreferences;
  /**
   * Optional override for the API base URL, for pointing this browser at a
   * different backend instance (e.g. a local vs. staging deployment)
   * without rebuilding the app. Empty string / null means "use
   * NEXT_PUBLIC_API_BASE_URL as built".
   */
  apiBaseUrlOverride: string | null;
}

export const DEFAULT_PREFERENCES: Preferences = {
  retrieval: {
    defaultTopK: 5,
    defaultSimilarityThreshold: 0.3,
  },
  memory: {
    defaultPruneKeepTopN: 1000,
  },
  notifications: {
    documents: true,
    memory: true,
    research: true,
    orchestration: true,
  },
  apiBaseUrlOverride: null,
};

const PREFERENCES_KEY = "maara_preferences";
const PREFERENCES_EVENT = "maara-preferences-updated";

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

/** Shallow-merges stored preferences over defaults so new fields added later degrade gracefully. */
function mergeWithDefaults(partial: Partial<Preferences> | null): Preferences {
  if (!partial) return DEFAULT_PREFERENCES;
  return {
    retrieval: { ...DEFAULT_PREFERENCES.retrieval, ...partial.retrieval },
    memory: { ...DEFAULT_PREFERENCES.memory, ...partial.memory },
    notifications: { ...DEFAULT_PREFERENCES.notifications, ...partial.notifications },
    apiBaseUrlOverride: partial.apiBaseUrlOverride ?? DEFAULT_PREFERENCES.apiBaseUrlOverride,
  };
}

export function getPreferences(): Preferences {
  if (!isBrowser()) return DEFAULT_PREFERENCES;
  try {
    const raw = window.localStorage.getItem(PREFERENCES_KEY);
    if (!raw) return DEFAULT_PREFERENCES;
    return mergeWithDefaults(JSON.parse(raw) as Partial<Preferences>);
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

export function setPreferences(next: Preferences): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(PREFERENCES_KEY, JSON.stringify(next));
  window.dispatchEvent(new Event(PREFERENCES_EVENT));
}

export function resetPreferences(): void {
  setPreferences(DEFAULT_PREFERENCES);
}

/** Subscribes to preference changes made anywhere in this tab (or other tabs, via `storage`). */
export function subscribeToPreferences(callback: () => void): () => void {
  if (!isBrowser()) return () => {};
  window.addEventListener(PREFERENCES_EVENT, callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener(PREFERENCES_EVENT, callback);
    window.removeEventListener("storage", callback);
  };
}

/** Reads the current notification preference for a given module without needing React context — safe to call from mutation callbacks in hooks. */
export function isNotifyEnabled(module: keyof NotificationPreferences): boolean {
  return getPreferences().notifications[module];
}

/** Resolves the effective API base URL: the user's override if set, otherwise the build-time default. */
export function resolveApiBaseUrl(buildTimeDefault: string): string {
  const override = getPreferences().apiBaseUrlOverride;
  return override && override.trim().length > 0 ? override.trim() : buildTimeDefault;
}
