import { describe, it, expect, beforeEach } from "vitest";

import { getActivityLog, logActivity, clearActivityLog } from "@/features/analytics/activity-log";

describe("activity-log", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("starts empty", () => {
    expect(getActivityLog()).toEqual([]);
  });

  it("logs an entry with a generated id and timestamp, newest first", () => {
    logActivity({ type: "search", label: "first", success: true, latencyMs: 100, latencySource: "client" });
    logActivity({ type: "research", label: "second", success: true, latencyMs: 200, latencySource: "server" });

    const entries = getActivityLog();
    expect(entries).toHaveLength(2);
    expect(entries[0].label).toBe("second");
    expect(entries[1].label).toBe("first");
    expect(entries[0].id).toBeTruthy();
    expect(entries[0].timestamp).toBeTruthy();
  });

  it("caps the log at 300 entries, dropping the oldest", () => {
    for (let i = 0; i < 305; i += 1) {
      logActivity({ type: "search", label: `entry-${i}`, success: true, latencyMs: 1, latencySource: "client" });
    }
    const entries = getActivityLog();
    expect(entries).toHaveLength(300);
    expect(entries[0].label).toBe("entry-304");
    expect(entries[299].label).toBe("entry-5");
  });

  it("clearActivityLog empties the log", () => {
    logActivity({ type: "upload", label: "doc", success: true, latencyMs: null, latencySource: null });
    clearActivityLog();
    expect(getActivityLog()).toEqual([]);
  });

  it("gracefully handles corrupt stored JSON by returning an empty log", () => {
    window.localStorage.setItem("maara_activity_log", "{not-json");
    expect(getActivityLog()).toEqual([]);
  });
});
