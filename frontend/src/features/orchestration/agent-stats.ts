/**
 * Per-agent execution stats.
 *
 * The backend has no history endpoint for past orchestration runs — each
 * `/orchestration/execute` call only returns the trace for *that* run.
 * Rather than show fabricated "execution count" / "success rate" numbers
 * on the Agent Inspector, this ingests the real `trace.timeline` from
 * every execution this browser makes and keeps a running per-capability
 * aggregate in localStorage. Every number here traces back to an actual
 * task that actually ran.
 */

import type { TaskTimelineEntryOut } from "@/types/orchestration";

export interface AgentStats {
  capability: string;
  executionCount: number;
  successCount: number;
  failCount: number;
  totalDurationMs: number;
  lastExecutedAt: string | null;
  lastStatus: string | null;
}

const STATS_KEY = "maara_agent_stats";
const STATS_EVENT = "maara-agent-stats-updated";

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

function isTerminal(status: string): boolean {
  return status === "succeeded" || status === "completed" || status === "failed";
}

function isSuccess(status: string): boolean {
  return status === "succeeded" || status === "completed";
}

export function getAgentStats(): Record<string, AgentStats> {
  if (!isBrowser()) return {};
  try {
    const raw = window.localStorage.getItem(STATS_KEY);
    return raw ? (JSON.parse(raw) as Record<string, AgentStats>) : {};
  } catch {
    return {};
  }
}

/** Folds a completed execution's timeline into the running per-capability aggregates. */
export function ingestExecutionTimeline(timeline: TaskTimelineEntryOut[]): void {
  if (!isBrowser()) return;
  const stats = getAgentStats();

  for (const task of timeline) {
    if (!isTerminal(task.status)) continue;
    const existing = stats[task.capability] ?? {
      capability: task.capability,
      executionCount: 0,
      successCount: 0,
      failCount: 0,
      totalDurationMs: 0,
      lastExecutedAt: null,
      lastStatus: null,
    };
    const success = isSuccess(task.status);
    stats[task.capability] = {
      capability: task.capability,
      executionCount: existing.executionCount + 1,
      successCount: existing.successCount + (success ? 1 : 0),
      failCount: existing.failCount + (success ? 0 : 1),
      totalDurationMs: existing.totalDurationMs + (task.duration_ms ?? 0),
      lastExecutedAt: task.completed_at ?? task.started_at ?? new Date().toISOString(),
      lastStatus: task.status,
    };
  }

  window.localStorage.setItem(STATS_KEY, JSON.stringify(stats));
  window.dispatchEvent(new Event(STATS_EVENT));
}

export function clearAgentStats(): void {
  if (!isBrowser()) return;
  window.localStorage.removeItem(STATS_KEY);
  window.dispatchEvent(new Event(STATS_EVENT));
}

export function subscribeToAgentStats(callback: () => void): () => void {
  if (!isBrowser()) return () => {};
  window.addEventListener(STATS_EVENT, callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener(STATS_EVENT, callback);
    window.removeEventListener("storage", callback);
  };
}
