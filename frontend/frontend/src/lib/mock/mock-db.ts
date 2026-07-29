/**
 * Mock persistence layer for Phase 9 features that have no backend
 * endpoint yet (projects, comments, annotations, notifications,
 * presence — see docs/Phase9.md §2). Every mock service in
 * `src/features/<feature>/services/mock-<name>.ts` is built on this file.
 *
 * Design intent: components and hooks call these mock services through
 * the exact same async, Promise-based shape as `src/lib/api/*-api.ts`
 * (real backend services). When a real endpoint exists later, only the
 * service file's internals change — no component, hook, or type import
 * path changes.
 */

const NAMESPACE = "maara_mock_db";

function readCollection<T>(collection: string): T[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(`${NAMESPACE}:${collection}`);
    return raw ? (JSON.parse(raw) as T[]) : [];
  } catch {
    return [];
  }
}

function writeCollection<T>(collection: string, items: T[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(`${NAMESPACE}:${collection}`, JSON.stringify(items));
    window.localStorage.setItem(`${NAMESPACE}:${collection}:__touched`, "true");
  } catch {
    // Storage full/unavailable — mock data is non-critical, fail silently.
  }
}

function isTouched(collection: string): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(`${NAMESPACE}:${collection}:__touched`) === "true";
}

/** Simulates realistic network latency so loading states are exercised honestly in dev, not just in tests. */
function simulateLatency(ms = 250 + Math.random() * 250): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export const mockDb = {
  /**
   * Seeds a collection only if it has never been written to by any
   * operation (seed, create, update, remove, replaceAll) — tracked via
   * a separate "touched" flag, not by checking current emptiness. This
   * matters because a deliberate `clearAll()` (which calls
   * `replaceAll(collection, [])`) leaves the collection empty on
   * purpose; without the touched flag, the next `list()` call would
   * silently re-seed it, undoing the clear.
   */
  async seedIfEmpty<T>(collection: string, seed: T[]): Promise<void> {
    if (isTouched(collection)) return;
    writeCollection(collection, seed);
  },

  async list<T>(collection: string): Promise<T[]> {
    await simulateLatency();
    return readCollection<T>(collection);
  },

  async get<T extends { id: string }>(collection: string, id: string): Promise<T | null> {
    await simulateLatency();
    return readCollection<T>(collection).find((item) => item.id === id) ?? null;
  },

  async create<T extends { id: string }>(collection: string, item: T): Promise<T> {
    await simulateLatency();
    const items = readCollection<T>(collection);
    writeCollection(collection, [item, ...items]);
    return item;
  },

  async update<T extends { id: string }>(collection: string, id: string, patch: Partial<T>): Promise<T> {
    await simulateLatency();
    const items = readCollection<T>(collection);
    const index = items.findIndex((item) => item.id === id);
    if (index === -1) throw new Error(`Mock record not found: ${collection}/${id}`);
    const updated = { ...items[index], ...patch };
    items[index] = updated;
    writeCollection(collection, items);
    return updated;
  },

  async remove(collection: string, id: string): Promise<void> {
    await simulateLatency();
    const items = readCollection<{ id: string }>(collection);
    writeCollection(
      collection,
      items.filter((item) => item.id !== id)
    );
  },

  /** Escape hatch for bulk replace (used by "mark all read", "clear all", etc.). */
  async replaceAll<T>(collection: string, items: T[]): Promise<T[]> {
    await simulateLatency();
    writeCollection(collection, items);
    return items;
  },
};

export function generateMockId(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}