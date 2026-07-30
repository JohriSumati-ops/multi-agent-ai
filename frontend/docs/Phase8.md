# Phase 8 — Settings & Analytics

Built on top of the Phase 7 frontend without modifying any backend code, database models, or API contracts. Nothing from Phase 7 was removed or re-architected — this phase adds two new modules and wires a handful of existing hooks to feed them real data.

## What's new

### 1. Settings (`/settings`)

Client-side preferences, following the exact pattern already established for theme in `context/theme-provider.tsx` — there is no backend endpoint for user settings (confirmed against `backend/api/routes`: only `auth`, `documents`, `health`, `memory`, `orchestration`, `research`, `retrieval`, `version` exist), so everything here is `localStorage`-backed via `lib/preferences.ts` + `context/preferences-context.tsx`. This is stated plainly on the page itself rather than presented as an account-level setting.

- **Appearance** — theme (reuses the existing theme provider).
- **Research & retrieval defaults** — default top-K / similarity threshold, which now actually seed the Retrieval search form (`features/retrieval/components/retrieval-search.tsx`) instead of hardcoded `5` / `0.3`.
- **Memory limits** — default "keep top N" for the Prune action on the Memory page; the Prune button on `/memory` now reads and displays this value instead of a hardcoded `1000`.
- **Notifications** — per-module toggles (documents / memory / research / orchestration) that gate the `sonner` toast calls already used by each feature's mutation hooks. Previously these toasts always fired unconditionally.
- **API configuration** — shows the build-time `NEXT_PUBLIC_API_BASE_URL` and lets a user override which backend *this browser* talks to (stored locally, resolved per-request in `lib/api/client.ts`). Useful for pointing at a local vs. staging backend without a rebuild.

### 2. Analytics (`/analytics`)

The backend has no history/audit-log endpoints — no way to list past searches, research queries, or orchestration executions (same gap Phase 7 already documented for Memory/Orchestration history). Rather than fabricate trend data, Analytics is built from two genuinely real sources:

- **Snapshot data straight from the API** — reuses `DocumentStatusChart`, `MemoryCompositionChart`, and `AgentHealthChart` from the dashboard feature (no duplication), plus a new `UploadActivityChart` that buckets real document `created_at` timestamps into a 14-day trend.
- **A new client-side session activity log** (`features/analytics/activity-log.ts`) — every real search, research query, orchestration execution, memory search, and document upload now calls `logActivity()` at the moment its mutation resolves. Latency is the backend's own `latency_ms` for research (where the API reports it) and a client-measured wall-clock duration everywhere else. This powers `ActivityFrequencyChart`, `LatencyChart`, and `RecentActivityTable`.

The page states plainly, up front, that "activity" here means *since logging started in this browser*, not all-time server history — that distinction is real and worth being honest about rather than glossing over.

### 3. Search history & suggestions (Retrieval)

Added `hooks/use-local-history.ts`, a small generic localStorage-backed history hook, and wired it into `RetrievalSearch`: recent queries appear as clickable chips (re-runs the search with its original top-K/threshold) and as native `<datalist>` suggestions while typing. Same "this browser only" scoping as everything else in this phase — there's no backend search-history endpoint either.

## Incidental fixes

Two pre-existing issues were blocking a clean build and were fixed as part of getting this phase's own verification (`tsc`, `eslint`, `vitest`, `next build`) to actually pass:

- `cmdk` was imported by the Phase 7 command palette (`components/ui/command.tsx`) but was never added to `package.json` — added as a direct dependency.
- `components/ui/tooltip.tsx` had a genuine syntax bug (missing `<...>` generic type arguments on `React.forwardRef`), which cascaded into unrelated type errors in `features/presence/components/presence-avatar-stack.tsx`. Fixed the syntax; no behavior change.
- `hooks/use-local-history.ts` (present in the repo, unused) had one lint violation (`react-hooks/set-state-in-effect`); fixed with the same inline-justification pattern used elsewhere in the codebase, then actually wired it up for search history.

## Verification

- `npx tsc --noEmit` — clean
- `npx eslint .` — clean
- `npx vitest run` — 68/68 passing (61 pre-existing + 7 new: `preferences.test.ts`, `activity-log.test.ts`, `use-local-history.test.tsx`)
- `npm run build` — clean, all 14 routes prerender, including `/settings` and `/analytics`

## Known limitations (by design, not oversight)

- Settings and search history are per-browser, not per-account. There's nowhere on the backend to persist them yet.
- Analytics "activity" and "latency" reflect this browser's session going forward, not all-time history, for the same reason.
- Memory growth on the Analytics page is a live snapshot (current composition), not a growth-over-time chart — the backend has no memory-statistics history endpoint to chart against.
