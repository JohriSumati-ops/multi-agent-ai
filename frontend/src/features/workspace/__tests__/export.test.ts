import { describe, it, expect } from "vitest";

import { sessionToMarkdown, sessionToText, sessionToJson, exportSession } from "@/features/workspace/export";
import type { WorkspaceSession } from "@/features/workspace/session-store";
import type { ResearchAnswerOut } from "@/types/research";

const answer: ResearchAnswerOut = {
  used_llm: true,
  answer: "Photosynthesis converts light into chemical energy.",
  sources_used: [{ chunk_id: "c1", document_title: "Biology 101", relevance: "high" }],
  citations: [
    { chunk_id: "c1", citation_text: "light into chemical energy", document_title: "Biology 101", page_number: 4, is_memory: false },
  ],
  confidence: 0.87,
  reasoning_summary: null,
  memory_references: [],
  retrieved_chunk_ids: ["c1"],
  is_grounded: true,
  prompt_tokens: 120,
  completion_tokens: 40,
  latency_ms: 812,
  fallback_reason: null,
  response_id: "resp-1",
};

const session: WorkspaceSession = {
  id: "s1",
  title: "Photosynthesis basics",
  pinned: false,
  createdAt: "2026-07-01T00:00:00.000Z",
  updatedAt: "2026-07-01T00:05:00.000Z",
  turns: [
    {
      id: "t1",
      mode: "query",
      query: "What is photosynthesis?",
      documentId: null,
      result: answer,
      timestamp: "2026-07-01T00:01:00.000Z",
    },
  ],
};

describe("session export", () => {
  it("markdown export includes the question, answer, and citations", () => {
    const md = sessionToMarkdown(session);
    expect(md).toContain("What is photosynthesis?");
    expect(md).toContain("Photosynthesis converts light into chemical energy.");
    expect(md).toContain("Biology 101");
    expect(md).toContain("p.4");
  });

  it("text export includes Q/A pairs", () => {
    const text = sessionToText(session);
    expect(text).toContain("Q: What is photosynthesis?");
    expect(text).toContain("A: Photosynthesis converts light into chemical energy.");
  });

  it("json export round-trips the full session structure", () => {
    const json = sessionToJson(session);
    const parsed = JSON.parse(json);
    expect(parsed.id).toBe("s1");
    expect(parsed.turns[0].result.citations).toHaveLength(1);
  });

  it("exportSession picks the right filename and mime per format", () => {
    expect(exportSession(session, "markdown").filename).toBe("photosynthesis-basics.md");
    expect(exportSession(session, "markdown").mime).toBe("text/markdown");
    expect(exportSession(session, "text").filename).toBe("photosynthesis-basics.txt");
    expect(exportSession(session, "json").mime).toBe("application/json");
  });

  it("handles a session with no turns without throwing", () => {
    const empty: WorkspaceSession = { ...session, turns: [] };
    expect(() => sessionToMarkdown(empty)).not.toThrow();
    expect(() => sessionToText(empty)).not.toThrow();
  });
});
