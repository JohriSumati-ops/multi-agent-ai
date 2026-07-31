# Phase 9 — Research Workspace

Built on top of Phase 7 (frontend foundation) and Phase 8 (Settings, Analytics) without touching backend code, database models, or API contracts. As with Phase 8, real backend constraints shaped what was honestly buildable — documented per-section below rather than glossed over.

Delivered as four bundles, all selected by the user rather than attempted blind:

## A — Research Workspace

`/research` was a one-shot query form; it's now a full chat-style workspace.

- **Sessions are client-side** (`features/workspace/session-store.ts`, `localStorage`). The backend's `/research/*` endpoints are stateless single-shot request/response — no `session_id` exists anywhere in `backend/schemas/research.py` or `api/routes/research.py`. Every *turn* within a session still hits the real backend; only the grouping into a named, saved conversation is local. New/rename/pin/duplicate/delete/import/export all work against this store.
- **Chat UI** (`conversation-thread.tsx`, `query-composer.tsx`): auto-scrolling thread, a typing indicator while a request is in flight (explicitly *not* called "streaming" — the backend has no SSE/streaming endpoint, so the UI doesn't claim to stream), markdown rendering with syntax-highlighted code blocks (`react-markdown` + `remark-gfm` + `rehype-highlight`, themed to the app's own CSS variables rather than a bundled highlight.js theme).
- **Modes**: query / answer / summarize, each backed by the real `researchApi.query` / `.answer` / `.summarize` endpoints (the API client already supported all three; only `query` was wired to UI before).
- **Document scoping**: the composer's document selector is populated from real uploaded documents and passed as `document_id` to the request.
- **Export Center** (`features/workspace/export.ts`): Markdown, Text, and JSON are genuine full serializations of the session. "PDF" is the browser's native print-to-PDF against a dedicated print view (`/research/print/[sessionId]`) rather than a fabricated server-side PDF button — `Sidebar`/`Topbar` gained a `className` prop so they can be tagged `no-print` and hidden during printing.

## B — Reasoning & Orchestration Visualizers

- **Reasoning pipeline** (`features/research/components/reasoning-pipeline.tsx`): replaces the old raw-JSON dump in the Explainability panel with a real stage-by-stage visualization (Query → Retrieved Context → Memory Context → Prompt Construction → LLM Reasoning → Validation/Grounding → Citation Injection → Final Response). Built from the actual shape `ResearchService._persist` populates in `explainability_payload` (mirrored in `features/research/reasoning-payload.ts` from `reasoning/source_grounding.py` and `reasoning/research_synthesis.py`, parsed defensively since it crosses a loosely-typed `dict` boundary). Raw JSON is still available behind a "Show raw payload" toggle.
- **Orchestration workflow diagram** (`features/orchestration/components/orchestration-workflow-diagram.tsx`): a real Gantt-style rendering of `trace.timeline` — bar position and width are computed directly from each task's actual `started_at`/`completed_at`/`duration_ms`, not estimated or faked.

## C — Source Explorer & Citation Panel

- **Source Explorer** (`features/retrieval/components/source-explorer-results.tsx`): filter by document, filter by confidence (client-side, over the already-fetched top-K), sort by rank/score/document, expandable chunk viewer, and query-term highlighting (`features/retrieval/highlight.ts`).
- **Citation Panel** (`features/research/components/citation-panel.tsx`): reusable, grouped by source, with per-citation copy and Markdown/JSON export. Used in both the Research Workspace and available for reuse anywhere citations appear — not duplicated per surface.

## D — Agent Inspector, Search History, Command Palette

- **Agent Inspector** (`orchestration/components/agent-inspector-dialog.tsx`): real capability metadata + health from the backend, plus **real session-derived stats** (execution count, success rate, avg latency, last run) from a new `features/orchestration/agent-stats.ts` store that ingests the actual `trace.timeline` of every execution this browser runs. The backend has no execution-history endpoint, so — like the Analytics activity log from Phase 8 — these numbers are genuine but scoped to "this browser's session," stated as such in the UI.
- **Search history** (`features/retrieval/components/search-history-panel.tsx`): pin/unpin, delete individual entries, sort (recent/A–Z), built on an extended `useLocalHistory` (added a generic `update()` method).
- **Command Palette**: added a "Quick actions" group with real behavior beyond navigation — "Start a new research session" actually creates one via the session store; "Upload a document" deep-links to `#document-uploader`; plus a keyboard-shortcuts helper.

## Verification

- `npx tsc --noEmit` — clean
- `npx eslint .` — clean
- `npx vitest run` — 99/99 passing (73 pre-existing + 26 new: `session-store.test.ts`, `export.test.ts`, `agent-stats.test.ts`, `highlight.test.ts`, extended `use-local-history.test.tsx`)
- `npm run build` — clean, all 15 routes (14 static + 1 dynamic `/research/print/[sessionId]`)

## Known limitations (by design)

- Research sessions, search history, and agent stats are per-browser, not per-account — there's nowhere on the backend to persist them.
- No true response streaming — the backend has no SSE endpoint; the workspace shows a typing indicator while awaiting the real (non-streamed) response rather than faking a stream.
- Agent Inspector's execution stats reset if the browser's localStorage is cleared, same as Analytics' activity log.
- "Global Search" (spec item 11) was intentionally folded into the Command Palette rather than built as a separate UI — a second full-text search surface over the same client-loaded data (documents, modules) would have been pure duplication.
