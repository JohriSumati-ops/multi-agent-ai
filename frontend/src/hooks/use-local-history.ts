"use client";

import * as React from "react";

/**
 * Small localStorage-backed list, capped at `limit`, most-recent-first,
 * with de-duplication by `key`. Used for client-only history/saved-item
 * features that have no backend endpoint (search history, saved
 * searches) — scoped to this browser, not synced across devices or
 * accounts. See docs/Phase8.md §2.
 */
export function useLocalHistory<T>(storageKey: string, limit = 20, itemKey: (item: T) => string) {
  const [items, setItems] = React.useState<T[]>([]);
  const [hydrated, setHydrated] = React.useState(false);

  React.useEffect(() => {
    try {
      const raw = window.localStorage.getItem(storageKey);
      // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time sync from localStorage, an SSR-unavailable external source; can't be computed during render.
      setItems(raw ? (JSON.parse(raw) as T[]) : []);
    } catch {
      setItems([]);
    } finally {
      setHydrated(true);
    }
  }, [storageKey]);

  const persist = React.useCallback(
    (next: T[]) => {
      setItems(next);
      try {
        window.localStorage.setItem(storageKey, JSON.stringify(next));
      } catch {
        // Storage full or unavailable (private browsing) — fail silently,
        // history is a convenience feature, not critical data.
      }
    },
    [storageKey]
  );

  const add = React.useCallback(
    (item: T) => {
      const withoutDupe = items.filter((existing) => itemKey(existing) !== itemKey(item));
      persist([item, ...withoutDupe].slice(0, limit));
    },
    [items, itemKey, limit, persist]
  );

  const remove = React.useCallback(
    (key: string) => {
      persist(items.filter((existing) => itemKey(existing) !== key));
    },
    [items, itemKey, persist]
  );

  const update = React.useCallback(
    (key: string, patch: Partial<T>) => {
      persist(items.map((existing) => (itemKey(existing) === key ? { ...existing, ...patch } : existing)));
    },
    [items, itemKey, persist]
  );

  const clear = React.useCallback(() => persist([]), [persist]);

  return { items, hydrated, add, remove, update, clear };
}