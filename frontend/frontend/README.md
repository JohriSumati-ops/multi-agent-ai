# Multi-Agent AI Research Assistant — Frontend

Phase 7 of the Multi-Agent AI Research Assistant: a Next.js console for the
Phase 0–6 backend (retrieval, memory, orchestration, research reasoning).

See [`docs/Phase7.md`](./docs/Phase7.md) for architecture, design-system
decisions, the full API-integration map, known backend gaps, and what's
been verified.

## Quick start

```bash
# 1. Run the backend (in the backend repo)
uvicorn main:app --reload   # http://localhost:8000

# 2. Configure and run the frontend
c
npm install
npm run dev                 # http://localhost:3000
```

## Scripts

| Command | Purpose |
|---|---|
| `npm run dev` | Local dev server |
| `npm run build` | Production build |
| `npm run lint` | ESLint |
| `npm run test` | Run the Vitest suite once |
| `npm run test:watch` | Vitest in watch mode |

## Environment variables

See `.env.local.example`:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

## Modules

Auth · Dashboard · Documents · Retrieval · Memory · Orchestration ·
Research · System — one folder per module under `src/features/`, one
route group under `src/app/(app)/`, one typed API service per backend
router under `src/lib/api/`.
