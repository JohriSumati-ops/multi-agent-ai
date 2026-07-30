import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";

import { useLocalHistory } from "@/hooks/use-local-history";

interface Entry {
  query: string;
}

describe("useLocalHistory", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("hydrates as an empty list when nothing is stored", async () => {
    const { result } = renderHook(() => useLocalHistory<Entry>("test_history", 5, (e) => e.query));
    await waitFor(() => expect(result.current.hydrated).toBe(true));
    expect(result.current.items).toEqual([]);
  });

  it("adds items most-recent-first and persists them", async () => {
    const { result } = renderHook(() => useLocalHistory<Entry>("test_history", 5, (e) => e.query));
    await waitFor(() => expect(result.current.hydrated).toBe(true));

    act(() => result.current.add({ query: "first" }));
    act(() => result.current.add({ query: "second" }));

    expect(result.current.items).toEqual([{ query: "second" }, { query: "first" }]);
    expect(JSON.parse(window.localStorage.getItem("test_history")!)).toEqual([
      { query: "second" },
      { query: "first" },
    ]);
  });

  it("de-duplicates by key, moving the repeated item to the front", async () => {
    const { result } = renderHook(() => useLocalHistory<Entry>("test_history", 5, (e) => e.query));
    await waitFor(() => expect(result.current.hydrated).toBe(true));

    act(() => result.current.add({ query: "a" }));
    act(() => result.current.add({ query: "b" }));
    act(() => result.current.add({ query: "a" }));

    expect(result.current.items).toEqual([{ query: "a" }, { query: "b" }]);
  });

  it("caps the list at the given limit", async () => {
    const { result } = renderHook(() => useLocalHistory<Entry>("test_history", 2, (e) => e.query));
    await waitFor(() => expect(result.current.hydrated).toBe(true));

    act(() => result.current.add({ query: "a" }));
    act(() => result.current.add({ query: "b" }));
    act(() => result.current.add({ query: "c" }));

    expect(result.current.items).toEqual([{ query: "c" }, { query: "b" }]);
  });

  it("clear empties the list", async () => {
    const { result } = renderHook(() => useLocalHistory<Entry>("test_history", 5, (e) => e.query));
    await waitFor(() => expect(result.current.hydrated).toBe(true));

    act(() => result.current.add({ query: "a" }));
    act(() => result.current.clear());

    expect(result.current.items).toEqual([]);
  });
});
