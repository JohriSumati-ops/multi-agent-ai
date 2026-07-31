import { describe, it, expect } from "vitest";

import { splitForHighlight } from "@/features/retrieval/highlight";

describe("splitForHighlight", () => {
  it("returns the whole text unmatched when the query has no significant terms", () => {
    expect(splitForHighlight("some text", "an of")).toEqual([{ text: "some text", match: false }]);
  });

  it("marks segments matching a query term as matches", () => {
    const result = splitForHighlight("The quick brown fox", "quick fox");
    const matched = result.filter((s) => s.match).map((s) => s.text.toLowerCase());
    expect(matched).toContain("quick");
    expect(matched).toContain("fox");
  });

  it("is case-insensitive", () => {
    const result = splitForHighlight("PYTHON is great", "python");
    expect(result.some((s) => s.match && s.text === "PYTHON")).toBe(true);
  });

  it("reassembles to the original text", () => {
    const text = "Neural networks learn from data";
    const result = splitForHighlight(text, "neural data");
    expect(result.map((s) => s.text).join("")).toBe(text);
  });
});
