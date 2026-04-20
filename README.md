# On-Orbit Satellite Collision Predictor

A mission-control style platform for **space situational awareness (SSA)**: conjunction analysis, collision risk scoring, ML-assisted prediction, and 3D orbital visualization.

This project is designed to evolve from portfolio demo to production-grade engineering system with strict contracts, typed boundaries, CI/CD discipline, and operational reliability.

**Repository:** `DevDonzo/aegis-orbit`  
**Primary branch:** `main`

---

## System overview

### Core components

- **Backend (`backend/`)** — FastAPI service for satellite snapshots, conjunction detection, and prediction APIs.
- **Frontend (`frontend/`)** — Next.js 14 dashboard with Cesium globe, telemetry overlays, alerts, and operational status panels.
- **ML pipeline (`backend/ml/`)** — Optional trained model path with heuristic fallback for resilient prediction behavior.

### Runtime flow

1. Backend computes a dashboard snapshot from orbital samples and exposes API endpoints.
2. Frontend polls `/dashboard` (with `/satellites` + `/collisions` fallback), then merges into Zustand state.
3. Cesium scene renders tracks, vectors, and risk data from normalized frontend types.
4. Prediction/status overlays read `/predict` and `/ml/status`; WebSocket status can supplement polling.

---

## Repository layout

```text
.
├── backend/
│   ├── api/                # FastAPI entrypoint and routes
│   ├── core/               # Auth, config, cache adapters
│   ├── ml/                 # Data pipeline, feature engineering, predictor
│   ├── models/             # Trained model/user store artifacts
│   └── tests/              # Backend test suite
├── frontend/
│   ├── public/cesium/      # Cesium static assets copied at install/build
│   ├── src/app/            # Next.js app router shell
│   ├── src/components/     # Cesium + dashboard UI
│   ├── src/services/       # API client + data normalization
│   └── src/store/          # Global simulation state (Zustand)
└── render.yaml             # Render Blueprint for live deployment
```

---

## Local development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend defaults:

- API base: `http://127.0.0.1:8000`
- Docs: `http://127.0.0.1:8000/docs`
- Auth toggle: `SAT_AUTH_REQUIRED` (default `false`)

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend defaults:

- App URL: `http://localhost:3000`
- Backend URL source: `NEXT_PUBLIC_BACKEND_API_URL`
- Cesium assets copied via `postinstall` and `npm run build`

---

## Configuration

### Frontend environment variables

Create `frontend/.env.local` (or copy `frontend/.env.example`):

```bash
NEXT_PUBLIC_BACKEND_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_GLOBE_IMAGERY_MODE=cesium-ion
NEXT_PUBLIC_ARCGIS_TOKEN=
NEXT_PUBLIC_CESIUM_ION_TOKEN=
```

`NEXT_PUBLIC_GLOBE_IMAGERY_MODE`:

- `cesium-ion` (highest quality when Ion token is present)
- `arcgis`
- `osm`

### Backend environment variables (selected)

- `SAT_ENVIRONMENT` (`development|staging|production`)
- `SAT_AUTH_REQUIRED` (`true|false`)
- `SAT_JWT_SECRET` (required for secure auth in production)
- `SAT_FRONTEND_ORIGINS` (comma-separated CORS allowlist)

---

## API surface (frontend-relevant)

- `GET /dashboard` — primary mission snapshot
- `GET /satellites` — fallback satellite feed
- `GET /collisions` — fallback conjunction feed
- `GET /predict` — prediction overlay
- `GET /ml/status` — model/runtime status
- `WS /ws/system-status` — runtime heartbeat

When auth is enforced, protected routes require bearer token access.

---

## Quality gates

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

---

## Team operating model (how you and your friend should work)

`main` is production and protected. **Never push directly to `main`.**

### Required delivery flow

1. Create a branch from `main`: `feature/<name>` or `fix/<name>`
2. Implement only scoped changes on that branch
3. Open PR to `main`
4. CI must pass:
   - `Frontend lint + build`
   - `Backend tests`
   - `Backend runtime smoke`
5. Wait for required approval before merge
6. Merge PR (human or agent) only after all required checks are green and approval is present

This is the production-safe workflow used by strong engineering teams (small and large).

### PR review policy (strict)

- Use an AI reviewer (Copilot code review / automated review agent) on every PR for fast first-pass feedback.
- Human approval is mandatory before merge.
- CI checks are mandatory before merge.
- Branch protection applies to all users, including admins/agents (no bypass merges).

The canonical contributor rules are in `CONTRIBUTING.md` and `AGENTS.md`.

---

## CI/CD and live deployment

### GitHub Actions

- CI workflow: `.github/workflows/ci.yml`
- Deploy hook workflow: `.github/workflows/deploy-hooks.yml` (skips safely when hook secrets are absent)

### Render Blueprint

`render.yaml` provisions:

- `scp-backend` (FastAPI, health check: `/health`)
- `scp-frontend` (Next.js)

Deploy behavior:

- Auto-deploy on `main` with `checksPass`
- Hobby-compatible configuration (no Preview Environments requirement)

If service names or domains change, update:

- Frontend: `NEXT_PUBLIC_BACKEND_API_URL`
- Backend: `SAT_FRONTEND_ORIGINS`

---

## Reliability posture (current)

- Snapshot path resilience with split-endpoint fallback
- Controlled degradation behavior for optional/auth-limited data
- Guarded timestamp/timeline rendering to avoid runtime crashes
- Stable initial selection behavior after data arrival
- URL normalization safeguards for backend API overrides

---

## Productionization roadmap (recommended next steps)

To make this a true real-world tool, prioritize:

1. **Security hardening**: enforce JWT auth in production, tighten route access, rotate secrets, remove demo defaults.
2. **Data/cache hardening**: move cache path to Redis for multi-instance reliability.
3. **Operational maturity**: add observability (structured logs, latency/error dashboards, alerting).
4. **Scientific accuracy**: expand propagation fidelity and benchmark precision thresholds.
5. **Scale readiness**: support larger catalogs and deterministic compute windows.

---

## Engineering principle

**No vibe-coding in production paths.**  
Every change should be typed, testable, reviewable, and architecturally justified.
