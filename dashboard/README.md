# Dashboard (Next.js)

Review UI for the Job Application Multi-Agent System. Reads from the FastAPI
backend (see [`../api/README.md`](../api/README.md)); it never talks to the
database directly.

## Install

```bash
pnpm install
```

> This project uses **pnpm** (v11+). Do not use `npm`/`npx`.

## Run

```bash
pnpm dev
```

Open <http://localhost:3000>. The landing page lists the configured users;
pick one to reach `/<username>/drafts`.

The API must be running too (default <http://localhost:8000>) — start it from
the repo root with `uv run uvicorn api.main:app --reload`.

## Environment

| Variable             | Default                 | Purpose                          |
| -------------------- | ----------------------- | -------------------------------- |
| `NEXT_PUBLIC_API_URL`| `http://localhost:8000` | Base URL of the FastAPI backend. |

For local dev the default is fine. For a deployed dashboard (e.g. Vercel), set
`NEXT_PUBLIC_API_URL` to the public API URL. Create `dashboard/.env.local` to
override locally:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Scripts

| Command       | Description                       |
| ------------- | --------------------------------- |
| `pnpm dev`    | Start the dev server (port 3000). |
| `pnpm build`  | Production build.                 |
| `pnpm start`  | Serve the production build.       |
| `pnpm lint`   | Run ESLint.                       |
