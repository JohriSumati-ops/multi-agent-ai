import { describe, it, expect, beforeEach } from "vitest";

import {
  DEFAULT_PREFERENCES,
  getPreferences,
  setPreferences,
  resetPreferences,
  isNotifyEnabled,
  resolveApiBaseUrl,
} from "@/lib/preferences";

describe("preferences", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("returns defaults when nothing is stored", () => {
    expect(getPreferences()).toEqual(DEFAULT_PREFERENCES);
  });

  it("persists and reads back a full preferences object", () => {
    const next = {
      ...DEFAULT_PREFERENCES,
      retrieval: { defaultTopK: 10, defaultSimilarityThreshold: 0.5 },
    };
    setPreferences(next);
    expect(getPreferences().retrieval).toEqual({ defaultTopK: 10, defaultSimilarityThreshold: 0.5 });
  });

  it("merges stored partial data over defaults so newer fields degrade gracefully", () => {
    window.localStorage.setItem("maara_preferences", JSON.stringify({ retrieval: { defaultTopK: 20 } }));
    const prefs = getPreferences();
    expect(prefs.retrieval.defaultTopK).toBe(20);
    // Field not present in the stored blob still falls back to the default.
    expect(prefs.retrieval.defaultSimilarityThreshold).toBe(DEFAULT_PREFERENCES.retrieval.defaultSimilarityThreshold);
    expect(prefs.notifications).toEqual(DEFAULT_PREFERENCES.notifications);
  });

  it("falls back to defaults if stored JSON is corrupt", () => {
    window.localStorage.setItem("maara_preferences", "{not-json");
    expect(getPreferences()).toEqual(DEFAULT_PREFERENCES);
  });

  it("resetPreferences restores defaults", () => {
    setPreferences({ ...DEFAULT_PREFERENCES, apiBaseUrlOverride: "http://example.com" });
    resetPreferences();
    expect(getPreferences()).toEqual(DEFAULT_PREFERENCES);
  });

  describe("isNotifyEnabled", () => {
    it("reflects a stored notification toggle", () => {
      setPreferences({
        ...DEFAULT_PREFERENCES,
        notifications: { ...DEFAULT_PREFERENCES.notifications, documents: false },
      });
      expect(isNotifyEnabled("documents")).toBe(false);
      expect(isNotifyEnabled("memory")).toBe(true);
    });
  });

  describe("resolveApiBaseUrl", () => {
    it("returns the build-time default when no override is set", () => {
      expect(resolveApiBaseUrl("http://build-default/api")).toBe("http://build-default/api");
    });

    it("returns the override when one is set", () => {
      setPreferences({ ...DEFAULT_PREFERENCES, apiBaseUrlOverride: "http://staging/api" });
      expect(resolveApiBaseUrl("http://build-default/api")).toBe("http://staging/api");
    });

    it("ignores a blank override", () => {
      setPreferences({ ...DEFAULT_PREFERENCES, apiBaseUrlOverride: "   " });
      expect(resolveApiBaseUrl("http://build-default/api")).toBe("http://build-default/api");
    });
  });
});
