import { describe, it, expect } from "vitest";

import { queryKeys } from "@/lib/api/query-keys";

describe("queryKeys", () => {
  it("scopes document detail keys by id", () => {
    expect(queryKeys.documents.detail("a")).not.toEqual(queryKeys.documents.detail("b"));
  });

  it("nests all specific keys under their module's 'all' key", () => {
    expect(queryKeys.documents.list().slice(0, 1)).toEqual(queryKeys.documents.all);
    expect(queryKeys.memory.statistics().slice(0, 1)).toEqual(queryKeys.memory.all);
  });

  it("produces stable, deterministic keys for identical input", () => {
    expect(queryKeys.retrieval.search("query", "doc-1")).toEqual(queryKeys.retrieval.search("query", "doc-1"));
  });

  it("distinguishes a scoped search from an unscoped one", () => {
    expect(queryKeys.retrieval.search("query", "doc-1")).not.toEqual(queryKeys.retrieval.search("query"));
  });
});
