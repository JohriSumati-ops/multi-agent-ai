import { describe, it, expect, beforeEach } from "vitest";

import {
  getSessions,
  createSession,
  addTurn,
  renameSession,
  togglePinSession,
  deleteSession,
  duplicateSession,
  getActiveSessionId,
  setActiveSessionId,
  exportSessionJson,
  importSessionJson,
  titleFromQuery,
} from "@/features/workspace/session-store";
import type { ResearchAnswerOut } from "@/types/research";

const mockAnswer: ResearchAnswerOut = {
  used_llm: true,
  answer: "The answer.",
  sources_used: [],
  citations: [],
  confidence: 0.9,
  reasoning_summary: null,
  memory_references: [],
  retrieved_chunk_ids: [],
  is_grounded: true,
  prompt_tokens: 10,
  completion_tokens: 20,
  latency_ms: 500,
  fallback_reason: null,
  response_id: "resp-1",
};

describe("workspace session-store", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("starts with no sessions", () => {
    expect(getSessions()).toEqual([]);
  });

  it("creates a session, sets it active, and prepends it to the list", () => {
    const session = createSession("My session");
    expect(getSessions()).toHaveLength(1);
    expect(getSessions()[0].title).toBe("My session");
    expect(getActiveSessionId()).toBe(session.id);
  });

  it("titles an untitled session from its first query", () => {
    const session = createSession();
    expect(session.title).toBe("New session");
    addTurn(session.id, { mode: "query", query: "What is RAG?", documentId: null, result: mockAnswer });
    expect(getSessions()[0].title).toBe("What is RAG?");
  });

  it("does not overwrite a title the user already set", () => {
    const session = createSession("Custom title");
    addTurn(session.id, { mode: "query", query: "Anything", documentId: null, result: mockAnswer });
    expect(getSessions()[0].title).toBe("Custom title");
  });

  it("appends turns in order and updates updatedAt", () => {
    const session = createSession("S");
    addTurn(session.id, { mode: "query", query: "Q1", documentId: null, result: mockAnswer });
    addTurn(session.id, { mode: "answer", query: "Q2", documentId: null, result: mockAnswer });
    const turns = getSessions()[0].turns;
    expect(turns).toHaveLength(2);
    expect(turns[0].query).toBe("Q1");
    expect(turns[1].query).toBe("Q2");
  });

  it("renames a session", () => {
    const session = createSession("Old");
    renameSession(session.id, "New");
    expect(getSessions()[0].title).toBe("New");
  });

  it("toggles pinned state", () => {
    const session = createSession("S");
    expect(getSessions()[0].pinned).toBe(false);
    togglePinSession(session.id);
    expect(getSessions()[0].pinned).toBe(true);
    togglePinSession(session.id);
    expect(getSessions()[0].pinned).toBe(false);
  });

  it("deletes a session and clears the active id if it was active", () => {
    const session = createSession("S");
    expect(getActiveSessionId()).toBe(session.id);
    deleteSession(session.id);
    expect(getSessions()).toEqual([]);
    expect(getActiveSessionId()).toBeNull();
  });

  it("duplicates a session with a fresh id and turn ids", () => {
    const session = createSession("Original");
    addTurn(session.id, { mode: "query", query: "Q1", documentId: null, result: mockAnswer });
    const copy = duplicateSession(session.id);
    expect(copy?.id).not.toBe(session.id);
    expect(copy?.title).toBe("Original (copy)");
    expect(copy?.turns[0].id).not.toBe(getSessions().find((s) => s.id === session.id)?.turns[0].id);
    expect(getSessions()).toHaveLength(2);
  });

  it("round-trips through export/import JSON with a fresh id", () => {
    const session = createSession("Exportable");
    addTurn(session.id, { mode: "query", query: "Q1", documentId: null, result: mockAnswer });
    const json = exportSessionJson(getSessions()[0]);

    window.localStorage.clear();
    const imported = importSessionJson(json);
    expect(imported.title).toBe("Exportable (imported)");
    expect(imported.turns).toHaveLength(1);
    expect(imported.id).not.toBe(session.id);
  });

  it("rejects import of JSON that isn't a session", () => {
    expect(() => importSessionJson(JSON.stringify({ hello: "world" }))).toThrow();
  });

  it("setActiveSessionId(null) clears the active session", () => {
    const session = createSession("S");
    expect(getActiveSessionId()).toBe(session.id);
    setActiveSessionId(null);
    expect(getActiveSessionId()).toBeNull();
  });
});

describe("titleFromQuery", () => {
  it("truncates long queries", () => {
    const long = "a".repeat(100);
    expect(titleFromQuery(long).length).toBeLessThanOrEqual(60);
    expect(titleFromQuery(long).endsWith("…")).toBe(true);
  });

  it("falls back to a default for empty input", () => {
    expect(titleFromQuery("   ")).toBe("Untitled session");
  });
});
