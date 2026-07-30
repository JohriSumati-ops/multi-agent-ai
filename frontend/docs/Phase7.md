# Phase 7 — Frontend Development

> Note on process: the standard workflow for this project writes this document
> *before* implementation. For this phase, the docs-first step was explicitly
> skipped on request, so this is a documentation of what was built, written
> immediately after implementation and verification — not a spec written in
> advance.

## 1. Scope

A production-quality Next.js frontend for the Multi-Agent AI Research
Assistant, consuming the Phase 0–6 backend (cloned from
`JohriSumati-ops/multi-agent-ai`) with no backend changes. Six modules:
Auth, Dashboard, Documents, Retrieval, Memory, Orchestration, Research,
System.

## 2. Tech stack (as specified)

Next.js 16 (App Router) · React 19 · TypeScript · Tailwind CSS v4 ·
hand-authored shadcn-style primitives · TanStack Query v5 · Axios ·
React Hook Form + Zod · Framer Motion · Lucide · Recharts · Vitest +
React Testing Library.

Two substitutions were necessary because this sandbox's network egress
only allows `npmjs.org`/`github.com`/etc., not `ui.shadcn.com` or Google
Fonts:

- **shadcn/ui**: components were hand-authored in `src/components/ui/`
  matching shadcn's exact API and file conventions (Radix primitives +
  `cva` + `cn()`), rather than pulled via the CLI. Functionally
  identical; just sourced locally instead of fetched.
- **Fonts**: Inter and IBM Plex Mono are self-hosted via `@fontsource/*`
  packages instead of `next/font/google`, since the latter fetches from
  `fonts.gstatic.com` at build time.

## 3. Design system — "Fiery Ocean"

All color tokens in `src/app/globals.css` derive from the five supplied
hex values and nothing else:

| Token | Hex | Usage |
|---|---|---|
| Deep red | `#780000` | destructive/critical (light theme) |
| Vivid red | `#C1121F` | primary brand/action |
| Cream | `#FDF0D5` | light-theme surface / dark-theme foreground |
| Navy | `#003049` | dark-theme surface / light-theme foreground |
| Steel blue | `#669BBC` | secondary accent, info, links, chart series |

Tints/shades (hover states, muted surfaces, chart series 3–5) are all
`color-mix()` derivations of these five values — no additional hues were
introduced. The app defaults to **dark theme**, matching the named
reference products (LangSmith, Vertex AI Studio, Anthropic Console are
all dark-first); light theme is fully implemented and toggleable.

Two typefaces carry a real distinction rather than being decorative:
**Inter** for UI chrome, **IBM Plex Mono** for anything that is raw
system data — IDs, token counts, timestamps, similarity scores, JSON
payloads. This mirrors how the reference products visually separate
"the interface" from "the data the interface is showing you."

**Signature element**: a dotted-connector, status-colored node motif
appears three times — ambient on the auth screens, and functionally in
the Orchestration execution trace and (implicitly, via the same badge
language) the Research citations/confidence display. It's meant to read
as one visual idea: an AI system's decision path made visible.

## 4. Architecture

```
src/
  app/                    # routes (App Router)
    (app)/                # protected shell: dashboard, documents, retrieval,
                           # memory, orchestration, research, system, profile
    login/ register/      # public auth routes
  components/ui/          # hand-authored shadcn-style primitives
  components/layout/      # Sidebar, Topbar, MobileNav, ProtectedRoute
  context/                # AuthProvider, ThemeProvider, QueryProvider
  features/<module>/      # feature-based: components/, hooks/, schemas
  lib/api/                # axios client, one service file per backend router,
                           # query-keys factory, token/jwt/profile-cache helpers
  types/                  # TS interfaces mirroring backend Pydantic schemas 1:1
```

Each `lib/api/*-api.ts` file maps directly onto one backend router file
(`documents-api.ts` ↔ `api/routes/documents.py`, etc.) — no endpoint
exists in the frontend that doesn't exist in the backend, and no backend
endpoint was changed to fit the frontend.

### Axios client (`lib/api/client.ts`)
- Request interceptor attaches `Authorization: Bearer <token>`.
- Response interceptor retries `502/503/504` up to twice with backoff;
  does not retry 4xx (retrying "not found" wastes a round trip).
- Unwraps the backend's `APIResponse<T>{success,data,error}` envelope
  into either the typed `data` or a thrown `ApiError{code,message,details,status}`,
  so every hook/component catches one consistent error shape.

### React Query
- Central key factory (`lib/api/query-keys.ts`) — no ad-hoc key arrays.
- Global retry policy skips retrying `ApiError`s in the 4xx range (see
  `context/query-provider.tsx`).

## 5. Known backend gaps

Found during integration, not introduced by the frontend:

1. **No `GET /auth/me`.** `/auth/login` returns only `{access_token,
   token_type}` — no profile data. The frontend works around this with
   a local profile cache (`lib/api/profile-cache.ts`) keyed by the JWT's
   `sub`, populated from the `/auth/register` response and the login
   form's typed email. This is clearly commented in code and on the
   Profile page — it is a client-side cache, not a verified server
   profile, and should be replaced once a `/auth/me` endpoint exists.
2. **No profile update endpoint.** The Profile page is read-only.
3. **No workflow/research history list endpoints.** Only single-shot
   `/orchestration/execute` and `/research/query` exist — there's no way
   to list past executions or past research answers, so the Dashboard
   shows live state (recent documents, memory stats, agent health)
   rather than fabricated history.
4. **No config/usage/model-info/logs endpoints** under `/system` — only
   `/health` and `/version` exist. The System page shows exactly those
   two, with an explicit note about what's not yet available rather than
   inventing placeholder data.
5. **No session enumeration endpoint** for working/session memory — only
   `GET /memory/session?session_id=`. The Memory page's Session tab is a
   manual lookup-by-ID rather than a live list.

None of these are treated as bugs to "fix" by changing the backend —
they're documented gaps, consistent with the "no backend changes" rule.

## 6. Verification performed

- `npx tsc --noEmit` — clean, run after every module (documents,
  retrieval, memory, orchestration, research, dashboard).
- `npm run build` (Next.js production build via Turbopack) — clean,
  all 12 routes prerendered as static shells.
- `npx eslint .` — clean (two `react-hooks/set-state-in-effect` warnings
  from legitimate one-time localStorage hydration effects were
  suppressed with inline justification comments, not silenced globally).
- `npx vitest run` — **49 tests passing across 9 files**: utility/client
  logic (`cn`, envelope unwrapping, JWT decode/expiry, query-key
  scoping), component behavior (Button variants/disabled state, Badge
  variants), domain logic (document status→badge mapping completeness
  against the full enum), and one integration test (LoginForm:
  validation errors, successful submit calling `useAuth().login` with
  the right payload, and API error surfacing).

  This is a representative slice, not exhaustive coverage — the highest
  novel-logic areas (typed API layer, auth flow, status mappings) are
  tested; presentational components for Retrieval/Memory/Orchestration/
  Research/System are not individually unit-tested yet. Given the size
  of this phase, that's a reasonable line to draw for now; expanding
  coverage to those components would be the next increment.

## 7. Running it

```bash
# backend (separate terminal, from the cloned repo)
cd multi-agent-ai/backend && uvicorn main:app --reload   # http://localhost:8000

# frontend
cd frontend
cp .env.local.example .env.local   # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
npm install
npm run dev      # http://localhost:3000
npm run build    # production build
npm run lint
npm run test
```
