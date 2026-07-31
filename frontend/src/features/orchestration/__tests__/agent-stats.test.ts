import { describe, it, expect, beforeEach } from "vitest";

import { getAgentStats, ingestExecutionTimeline, clearAgentStats } from "@/features/orchestration/agent-stats";
import type { TaskTimelineEntryOut } from "@/types/orchestration";

function task(overrides: Partial<TaskTimelineEntryOut>): TaskTimelineEntryOut {
  return {
    task_id: "t1",
    capability: "summarize",
    agent_name: "SummaryAgent",
    status: "succeeded",
    started_at: "2026-07-01T00:00:00.000Z",
    completed_at: "2026-07-01T00:00:01.000Z",
    duration_ms: 1000,
    confidence: 0.9,
    ...overrides,
  };
}

describe("agent-stats", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("starts empty", () => {
    expect(getAgentStats()).toEqual({});
  });

  it("ingests a successful task into per-capability stats", () => {
    ingestExecutionTimeline([task({})]);
    const stats = getAgentStats();
    expect(stats.summarize.executionCount).toBe(1);
    expect(stats.summarize.successCount).toBe(1);
    expect(stats.summarize.failCount).toBe(0);
    expect(stats.summarize.totalDurationMs).toBe(1000);
  });

  it("accumulates across multiple executions of the same capability", () => {
    ingestExecutionTimeline([task({ duration_ms: 1000 })]);
    ingestExecutionTimeline([task({ duration_ms: 2000 })]);
    const stats = getAgentStats();
    expect(stats.summarize.executionCount).toBe(2);
    expect(stats.summarize.totalDurationMs).toBe(3000);
  });

  it("counts failed tasks separately from successes", () => {
    ingestExecutionTimeline([task({ status: "failed", duration_ms: 500 })]);
    const stats = getAgentStats();
    expect(stats.summarize.successCount).toBe(0);
    expect(stats.summarize.failCount).toBe(1);
    expect(stats.summarize.lastStatus).toBe("failed");
  });

  it("ignores non-terminal (pending/running) tasks", () => {
    ingestExecutionTimeline([task({ status: "pending", duration_ms: null, completed_at: null })]);
    expect(getAgentStats()).toEqual({});
  });

  it("tracks separate capabilities independently", () => {
    ingestExecutionTimeline([task({ capability: "summarize" }), task({ capability: "retrieve", task_id: "t2" })]);
    const stats = getAgentStats();
    expect(Object.keys(stats).sort()).toEqual(["retrieve", "summarize"]);
  });

  it("clearAgentStats empties the store", () => {
    ingestExecutionTimeline([task({})]);
    clearAgentStats();
    expect(getAgentStats()).toEqual({});
  });
});
