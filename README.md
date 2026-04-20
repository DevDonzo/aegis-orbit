# On-Orbit Satellite Collision Predictor

Mission-control style platform for conjunction analysis, collision risk scoring, and 3D orbital visualization.

## What this project includes

- **Backend (`backend/`)**: FastAPI service that produces satellite/collision snapshots and ML predictions.
- **Frontend (`frontend/`)**: Next.js 14 dashboard with Cesium globe rendering, live telemetry panels, and alert workflows.
- **ML pipeline (`backend/ml/`)**: Optional model-backed distance prediction with heuristic fallback.

## Architecture at a glance

1. Backend builds a cached dashboard snapshot from orbital samples.
2. Frontend polls snapshot and prediction endpoints, then merges data into Zustand state.
3. Cesium scene renders tracks, conjunction vectors, and risk volumes from normalized frontend types.
4. WebSocket status channel supplements polling for runtime health.

## Repository layout

```text
.
├── backend/
│   ├── api/                # FastAPI entrypoint and routes
│   ├── core/               # Auth, config, cache adapters
│   ├── ml/                 # Data pipeline, schemas, optional predictor
│   └── models/             # Trained model/user store artifacts
└── frontend/
    ├── public/cesium/      # Cesium static assets copied at install/build
    ├── src/app/            # Next.js app router, layout, providers
    ├── src/components/     # Cesium + dashboard UI components
    ├── src/services/       # API client + mission normalization
    └── src/store/          # Simulation state (Zustand)
```

## Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend defaults:

- API base: `http://127.0.0.1:8000`
- OpenAPI docs: `http://127.0.0.1:8000/docs`
- Auth toggle: `SAT_AUTH_REQUIRED` (default `false`)
- Demo credentials when auth is enabled:
  - username: `operator`
  - password: `orbit-demo-2026`

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Frontend defaults:

- App URL: `http://localhost:3000`
- Backend URL env: `NEXT_PUBLIC_BACKEND_API_URL`
- Cesium assets are auto-copied via `postinstall` and `npm run build`

### Frontend environment variables

Create `frontend/.env.local` (or copy from `.env.example`):

```bash
NEXT_PUBLIC_BACKEND_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_GLOBE_IMAGERY_MODE=arcgis
NEXT_PUBLIC_ARCGIS_TOKEN=
NEXT_PUBLIC_CESIUM_ION_TOKEN=
```

Imagery mode options:

- `arcgis` (default)
- `cesium-ion` (requires `NEXT_PUBLIC_CESIUM_ION_TOKEN`)
- `osm`

## API endpoints used by the frontend

- `GET /dashboard` (primary mission snapshot)
- `GET /satellites` + `GET /collisions` (automatic frontend fallback path)
- `GET /predict` (prediction overlay)
- `GET /ml/status` (model/runtime status)
- `WS /ws/system-status` (runtime heartbeat)

When backend auth is enabled, `/predict`, `/ml/status`, and WebSocket routes require a bearer token. Frontend degrades gracefully when optional auth data is unavailable.

## Quality commands

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

Backend:

```bash
cd backend
pytest
```

## Team workflow + continuous deployment

Use this workflow so production stays stable while both contributors ship changes quickly:

1. Create a branch from `main` for each task (`feature/...`, `fix/...`).
2. Open a pull request into `main`.
3. Let GitHub Actions run CI (`.github/workflows/ci.yml`).
4. Merge only when CI is green.
5. Merges to `main` trigger deployment hooks (`.github/workflows/deploy-hooks.yml`).

Recommended repository settings:

- Protect `main` (Settings -> Branches): require pull requests and require status checks (`Frontend lint + build`, `Backend tests`).
- Disable direct pushes to `main`.

Deployment hook secrets expected by this repository:

- `FRONTEND_DEPLOY_HOOK_URL` (Netlify/Vercel deploy hook URL)
- `BACKEND_DEPLOY_HOOK_URL` (Render/Railway/Fly deploy hook URL)

If a secret is not configured, that deploy job is skipped.

## One-path live deployment (Render Blueprint)

This repository now includes `render.yaml` so both apps can be launched together with CI-gated auto deploys:

- `scp-backend` (FastAPI) with `/health` checks
- `scp-frontend` (Next.js) preconfigured to call `https://scp-backend.onrender.com`
- Deploy trigger mode set to `checksPass` (only deploy after CI passes)

Render setup:

1. In Render, create a new **Blueprint** and connect this GitHub repository.
2. Select the repo root so Render reads `render.yaml`.
3. Confirm any prompted secret values (optional imagery tokens).
4. Deploy.

After that, every merge to `main` updates live services automatically.

If you rename services or use custom domains, update these Render environment variables:

- Frontend: `NEXT_PUBLIC_BACKEND_API_URL`
- Backend: `SAT_FRONTEND_ORIGINS`

For production safety, keep GitHub `main` protected with required checks and PR-only merges.

## Current frontend reliability guarantees

- Resilient API pathing: snapshot uses `/dashboard` with automatic fallback to `/satellites` + `/collisions`.
- Safer connectivity state handling: avoids false degraded state during normal background refetches.
- Safer rendering for timestamps and timeline values: guards invalid/missing time data to prevent runtime crashes.
- More stable initial UX: auto-selects an initial asset/collision when data arrives.
- Robust backend URL normalization: invalid local overrides no longer break all requests.
