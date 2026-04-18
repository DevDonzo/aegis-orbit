# PROJECT_BLUEPRINT

**Project:** On-Orbit Satellite Collision Predictor  
**Repository:** `DevDonzo/on-orbit-satellite-collision-predictor`  
**Blueprint Version:** 1.0  
**Last Updated:** 2026-04-18  
**Source Scope:** Full scan of `backend/` and `frontend/` (including source, config, scripts, tests, and tracked project metadata files)

---

## 1. Project Context & Objectives

### 1.1 The Builder
- **Builder:** Hamza  
- **Background:** Software Engineering student, University of Guelph  
- **Primary Dev Environment:** MacBook Air M4  
- **Primary IDE:** Zed  

### 1.2 The Project
- **System Name:** On-Orbit Satellite Collision Predictor  
- **Original Concept Origin:** Canadian Space Agency-oriented concept exploration  
- **Domain:** Space Situational Awareness (SSA), conjunction risk analysis, orbital visualization, predictive analytics

### 1.3 The Team
- Collaborative effort by **four university students**.

### 1.4 The End Goal
This system is a flagship portfolio product intended to demonstrate:
- Enterprise-grade software engineering maturity
- Strict architecture discipline and modular design
- Production-minded reliability/performance/security
- Advanced ML-assisted decision support in an aerospace context
- Readiness for Big Tech software engineering expectations

### 1.5 Engineering Rule of Operation
**No vibe-coding.**  
All implementation must be deliberate, typed, modular, testable, and architecturally justified.

---

## 2. Executive System Summary

The repository already implements a functional end-to-end baseline:
- A **FastAPI backend** that computes conjunction candidates from sample TLEs, performs ML prediction (with fallback), and serves REST endpoints.
- A **Next.js 14 frontend** with a Cesium 3D globe and tactical dashboard panels, polling backend data into a Zustand simulation store.
- A cohesive dark aerospace UI aesthetic with telemetry-focused typography and mission-control layout.

The repository also contains aspirational requirements (README + architecture direction) that are only partially implemented today. Critical production features (strict OAuth2/JWT protection and Redis caching) are declared but not yet enforced in live backend route behavior.

---

## 3. Repository Inventory (Scanned Surfaces)

## 3.1 Backend (`backend/`)
- `api/main.py`, `api/routes.py`
- `core/config.py`, `core/auth.py`, `core/cache.py`
- `ml/data_pipeline.py`, `ml/feature_engineering.py`, `ml/training.py`, `ml/predictor.py`, `ml/schemas.py`
- `train_model.py`, `test.py`, `requirements.txt`
- `tests/test_auth.py`, `tests/test_data_pipeline.py`, `tests/test_feature_engineering.py`
- `models/collision_model.meta.json` (+ serialized model artifact present in directory)
- status notes in `backend/AGENTS.md`

## 3.2 Frontend (`frontend/`)
- App shell and route: `src/app/layout.tsx`, `src/app/page.tsx`, `src/app/error.tsx`, `src/app/providers.tsx`, `src/app/globals.css`
- Cesium integration: `src/components/cesium/*`
- Dashboard modules: `src/components/dashboard/*`
- UI primitives: `src/components/ui/*`
- Data/state infra: `src/hooks/useSimulationPolling.ts`, `src/store/useSimulationStore.ts`, `src/services/*`, `src/lib/*`, `src/types/index.ts`
- Build/config: `package.json`, `package-lock.json`, `next.config.mjs`, `tailwind.config.ts`, `tsconfig.json`, `.eslintrc.json`, `postcss.config.mjs`, `scripts/copy-cesium-assets.mjs`
- design intent note in `frontend/AGENTS.md`

---

## 4. Current-State Architecture (As Implemented)

## 4.1 High-Level Runtime Topology
1. Backend computes satellite positions and pairwise conjunction candidates from configured sample TLEs.
2. Backend exposes summary and ML-assisted risk APIs over FastAPI.
3. Frontend polls satellites/collisions/predictions-derived outputs and renders:
   - 3D orbital scene in Cesium
   - Tactical panel telemetry, alerts, status, and timeline scrubber
4. Zustand acts as the simulation state authority inside the frontend runtime.

## 4.2 Current Backend Architecture (Python + FastAPI + ML)

### 4.2.1 Backend API Surface (Current Truth)
Implemented route handlers in `backend/api/routes.py`:

| Method | Route | Auth Required (Current) | Response Model | Notes |
|---|---|---:|---|---|
| GET | `/health` | No | `dict` | Liveness |
| GET | `/satellites` | No | `list[SatelliteSummary]` | Cached, uses current orbital state |
| GET | `/collisions` | No | `list[CollisionSummary]` | Cached, conjunction candidates |
| GET | `/ml/status` | No | `MLStatus` | Model availability + metadata |
| GET | `/predict` | No | `list[MLPrediction]` | ML model if present; fallback otherwise |

### 4.2.2 API Layer Characteristics
- Framework: FastAPI
- Validation/typing: Pydantic models in `ml/schemas.py`
- CORS configured for localhost frontend origins (`http://localhost:3000`, `http://127.0.0.1:3000`)
- Endpoint-level caching currently done with in-process `SimpleTTLCache`

### 4.2.3 Configuration and Domain Constants
From `core/config.py`:
- Time step: `TIME_STEP_SECONDS = 300`
- Prediction horizon: `PREDICTION_HOURS = 6`
- Risk thresholds:
  - danger `< 10 km`
  - warning `< 50 km`
  - safe `>= 50 km`
- Model paths:
  - `models/collision_model.joblib`
  - `models/collision_model.meta.json`
- Cache TTLs:
  - satellites: 20s
  - collisions: 20s
  - predictions: 30s
- Sample TLE catalog includes ISS, Hubble, NOAA-15, Terra, Aqua, Starlink-1007

Backend env knobs currently in code:
- `SAT_API_TOKEN` (read by `core/auth.py`; currently not route-enforced)

### 4.2.4 Orbital Data Pipeline (`ml/data_pipeline.py`)
- Uses Skyfield (`EarthSatellite`, `wgs84`, timescale) to derive:
  - geodetic lat/lon/alt
  - cartesian position (x, y, z)
  - velocity vector (vx, vy, vz)
- Computes:
  - current satellite positions with nearest-neighbor risk label
  - pairwise conjunction candidates over future sampled times
  - features for prediction row generation
  - synthetic training dataset via repeated future-window sampling
- Risk classification is threshold-based via distance bands.

### 4.2.5 Feature Engineering (`ml/feature_engineering.py`)
Feature columns:
1. `dx`, `dy`, `dz`
2. `dvx`, `dvy`, `dvz`
3. `current_distance_km`
4. `altitude_diff_km`
5. `relative_speed_km_s`
6. `relative_xy_distance_km`
7. `radial_closure_rate_km_s`

Includes utilities:
- `create_feature_dataframe`
- `fit_normalizer`
- `apply_normalization`

### 4.2.6 ML Training (`ml/training.py`)
- Current model: `RandomForestRegressor`
- Hyperparameters:
  - `n_estimators=450`
  - `max_depth=14`
  - `min_samples_leaf=2`
  - `random_state=42`
  - `n_jobs=-1`
- Train/test split: 80/20
- Metrics persisted to metadata:
  - RMSE (km), MAE (km), R²
- Metadata artifact currently present (`collision_model.meta.json`) with:
  - 180 samples
  - `test_r2 ~ 0.9286`

### 4.2.7 Runtime Predictor (`ml/predictor.py`)
- Loads joblib model if enabled and present.
- If model unavailable, `/predict` route falls back to heuristic distances from collision computation.
- Converts distance to:
  - risk band (`safe` / `warning` / `danger`)
  - collision probability proxy (`exp(-distance/65)`)

### 4.2.8 Backend Security Posture (Current)
- `core/auth.py` currently provides simple env-token helpers (`SAT_API_TOKEN`) but is **not wired into route protection**.
- No OAuth2 password flow, JWT issue/verify pipeline, refresh/token revocation, or protected-route dependencies are active in current route layer.
- Frontend has auth client code for `/auth/token` and `/auth/register`, but backend does not currently implement those endpoints.

### 4.2.9 Backend Caching Posture (Current)
- Caching is in-memory (`SimpleTTLCache`) and process-local.
- No Redis client integration in active code path.
- Current behavior is acceptable for local demo but not horizontally scalable.

### 4.2.10 Backend Tests (Current)
- Auth unit tests validate simple token helper logic.
- Data pipeline tests validate non-empty satellites/events/training frame.
- Feature engineering tests validate finite transformed output and expected column count.

---

## 4.3 Current Frontend Architecture (Next.js 14 + TS + Cesium + Zustand)

### 4.3.1 Framework and Build
- Next.js `^14.2.14` with App Router
- React 18
- TypeScript strict mode enabled (`"strict": true`, `"allowJs": false`)
- ESLint with `next/core-web-vitals` and `next/typescript`

### 4.3.2 Rendering Layout
- Main page (`src/app/page.tsx`) composes:
  - full-screen Cesium canvas
  - tactical overlays: Telemetry, Alerts, System Status, Timeline
- Mission-control visual hierarchy:
  - 3D scene as primary canvas
  - overlay panels as operational controls

### 4.3.3 Cesium Integration
- Dynamic import in `CesiumWrapper.tsx`:
  - `dynamic(() => import(...), { ssr: false })` (already correct for hydration safety)
- Asset strategy:
  - `scripts/copy-cesium-assets.mjs` copies Workers/Assets/ThirdParty/Widgets to `public/cesium`
  - `CESIUM_BASE_URL` set at runtime
- Viewer lifecycle:
  - initialize once in effect
  - configure imagery provider selection (ArcGIS / Cesium Ion / OSM)
  - optional world terrain when Ion token exists
  - subscribe to `clock.onTick` and `scene.postRender`
  - dispose listeners and viewer on unmount

### 4.3.4 Scene/Data Update Separation
- `useSceneManager` handles entity synchronization against store snapshots.
- Cesium entity updates occur through Cesium property updates, minimizing full React rerender dependency.
- Metrics and simulation time are pushed to Zustand via event callbacks.

### 4.3.5 State Management
- Zustand store (`useSimulationStore`) holds:
  - `currentTimeIso`
  - `satellites` map
  - `collisionEvents`
  - `selectedEntityId`
  - `connectionState`
  - `metrics` (fps, latency, tracked count)
- Middleware: `devtools`, `subscribeWithSelector`

### 4.3.6 Data Acquisition
- `useSimulationPolling` uses TanStack Query:
  - telemetry poll every 12s
  - collisions poll every 10s
  - ML status poll every 30s (in `SystemStatus`)
- `simulationService.ts` composes backend responses into frontend domain models.
- Fallback to mock data only for specific backend availability conditions (404/503).

### 4.3.7 UI/Design Layer (Current)
- Tailwind CSS + custom UI primitives modeled after shadcn patterns.
- Dark aerospace style system in `globals.css`:
  - deep void palette
  - translucent blurred panels
  - 1px panel strokes
  - rounded-sm corners
  - mono telemetry formatting
- Typography:
  - current UI sans: **Outfit**
  - current mono: **JetBrains Mono**

### 4.3.8 Frontend Auth Readiness (Current)
- Auth token storage utility in `lib/auth.ts`.
- `authService.ts` has login/register client calls expecting:
  - `/auth/token`
  - `/auth/register`
- These backend endpoints are not present in current backend route definitions.

### 4.3.9 Frontend Environment Contract (Current)
From `frontend/.env.example` and `src/lib/env.ts`:
- `NEXT_PUBLIC_BACKEND_API_URL` (default local backend URL)
- `NEXT_PUBLIC_GLOBE_IMAGERY_MODE` = `arcgis | cesium-ion | osm`
- `NEXT_PUBLIC_ARCGIS_TOKEN` (optional, recommended for ArcGIS mode)
- `NEXT_PUBLIC_CESIUM_ION_TOKEN` (optional/required for Ion terrain + imagery mode)

---

## 5. Strict Architecture Standards (Mandated Target)

This section defines non-negotiable target standards moving forward.

## 5.1 Backend & ML Standards (Python/FastAPI)

### 5.1.1 ML Core
- scikit-learn must include:
  - RandomForest baseline
  - GradientBoosting model path (for comparison and/or ensemble strategy)
- Training/evaluation must preserve reproducible metadata:
  - feature schema hash
  - train/test split seed
  - data timestamp range
  - model registry metadata

### 5.1.2 API Layer
- FastAPI REST endpoints with strict Pydantic validation for:
  - telemetry ingest
  - conjunction candidate payloads
  - prediction requests/responses
- OpenAPI must represent auth and schema constraints accurately.

### 5.1.3 Security & Auth
- **Required:** OAuth2 JWT Bearer token authentication.
- Required implementation characteristics:
  - `/auth/token` issue endpoint
  - bearer dependency on protected routes
  - signed JWT with expiration
  - password hashing (bcrypt/argon2)
  - token verification + role/claims model where applicable
- Current unauthenticated prediction routes must be gated for production profile.

### 5.1.4 Data & Performance
- **Required:** Redis-backed caching layer for high-frequency trajectory/prediction reads.
- Cache keying must include query dimensions and TTL policy by endpoint/data volatility.
- In-memory cache may remain for local-dev fallback only.

---

## 5.2 Frontend Standards (Next.js/TypeScript/Cesium)

### 5.2.1 Core
- Next.js 14+ App Router (already in place)
- Strict TypeScript (already in place)
- No `any` types in committed code (enforced standard)

### 5.2.2 Cesium 3D Engine
- Cesium modules must be imported via dynamic client-only boundary:
  - `ssr: false` required
- React render cycles must remain decoupled from Cesium frame updates:
  - imperative scene manager hook pattern
  - event-driven updates to shared store

### 5.2.3 State Management
- Zustand remains global simulation source for:
  - time-scrubbing
  - satellite arrays/maps
  - conjunction alerts
  - operational metrics

### 5.2.4 Styling
- Tailwind CSS + shadcn/ui style primitives remain standard approach.

---

## 5.3 Strict UI/UX Design System (Aerospace Dark Mode)

These rules are mandatory and exact:

1. **Backgrounds:** Deep void colors (e.g., `#0B0E14`).  
   - No pure black  
   - No default gray surfaces

2. **Layout:** Floating tactical panels over full-bleed 3D canvas.

3. **Panel Material:** Translucent surfaces (`bg-white/5`) + strong backdrop blur.

4. **Edges:** Crisp 1px solid borders (`border-white/10`), sharp corners (`rounded-sm`).  
   - No pill-shaped controls.

5. **Typography:**  
   - UI text: **Inter/Geist**  
   - Coordinates/telemetry/live values: **JetBrains Mono** (or equivalent monospace)

### 5.3.1 Current vs Mandated Typography Note
- Current layout uses **Outfit** for sans text.
- Mandated standard requires migration to **Inter or Geist** for UI text continuity.

---

## 6. Current-State vs Target-State Gap Analysis

| Domain | Current State | Target Standard | Gap Severity | Required Action |
|---|---|---|---|---|
| Auth | No protected backend routes; simple token helper only | OAuth2 JWT bearer across protected endpoints | Critical | Implement full auth module + route dependencies |
| Cache | In-process TTL dict | Redis distributed caching | High | Add Redis client + replace endpoint cache plumbing |
| ML model family | RandomForest only | RF + GradientBoosting strategy | Medium | Add GB training/eval + selection/ensemble policy |
| API contract consistency | Frontend expects `/auth/*`; backend lacks routes | Full auth endpoints + schema parity | Critical | Add backend auth routes and sync API docs/types |
| Physics fidelity | Skyfield pipeline with sampled future states | High-accuracy SGP4-centric propagation architecture | Medium | Introduce explicit SGP4 propagation abstraction and validation |
| Real-time eventing | Polling only | WebSocket push for conjunction alerts | Medium | Add pub/sub + WS channel |
| Scale target | Small sample TLE set | Thousands of debris objects | High | Build ingestion/indexing/parallel compute architecture |
| UI typography standard | Outfit + JetBrains Mono | Inter/Geist + JetBrains Mono | Low | Swap sans font and verify UI consistency |

---

## 7. Detailed Component Blueprint

## 7.1 Backend Module Responsibilities
- `api/main.py`: FastAPI app factory + CORS + router registration
- `api/routes.py`: operational endpoints and endpoint-level caching integration
- `core/config.py`: global constants, thresholds, model/cache settings, sample TLE seed data
- `core/auth.py`: env token helper (placeholder security layer)
- `core/cache.py`: simple TTL cache utility
- `ml/data_pipeline.py`: orbital state derivation, conjunction simulation, training frame generation
- `ml/feature_engineering.py`: ML feature transforms and normalization tools
- `ml/training.py`: model training, evaluation, artifact + metadata persistence
- `ml/predictor.py`: model loading, inference, risk/probability conversion, fallback behavior
- `ml/schemas.py`: API/domain schema contracts
- `tests/*`: auth/pipeline/feature baseline tests

## 7.2 Frontend Module Responsibilities
- `app/layout.tsx`: global fonts/providers/Cesium CSS inclusion
- `app/page.tsx`: mission control layout composition
- `app/error.tsx`: global error boundary UX
- `components/cesium/*`: client-only scene bootstrap + entity synchronization
- `components/dashboard/*`: telemetry list, alerts, status panel, timeline control
- `components/ui/*`: reusable design-system primitives
- `hooks/useSimulationPolling.ts`: query-driven periodic data sync
- `services/apiClient.ts`: fetch wrapper + error typing + auth header plumbing
- `services/simulationService.ts`: backend-to-frontend model mapping and fallback logic
- `store/useSimulationStore.ts`: global simulation state/actions
- `types/index.ts`: shared frontend domain/API type contracts

---

## 8. Operational Data Flow (Current)

1. Frontend boots and mounts mission control page.
2. Cesium viewer initializes client-side only.
3. Polling hook requests `/satellites` and `/collisions`.
4. Collision service also requests `/predict` and `/satellites` for enrichment.
5. Data normalized into frontend `OrbitData` and `CollisionRisk`.
6. Zustand updates trigger dashboard and scene sync.
7. Scene manager updates/creates/removes Cesium entities.
8. Time scrubbing modifies `currentTimeIso`, reflected in Cesium clock.

---

## 9. Engineering Governance Rules (Project-wide)

1. Every non-trivial module must have clear typed interfaces.
2. Every architecture decision should be traceable to reliability, accuracy, security, or scale.
3. All production-sensitive routes must be authenticated and observable.
4. No hidden side effects in UI state transitions.
5. No weakly typed payload transformations in API clients.
6. No merge of major features without tests + documented acceptance criteria.
7. No “temporary” hacks that bypass architecture boundaries.

---

## 10. The “Amazing” Expansion Roadmap

## 10.1 Vision Statement
Evolve this from a strong demo into a mission-grade SSA intelligence platform that combines accurate orbital mechanics, predictive ML, agentic operations support, and real-time decision workflows.

## 10.2 Roadmap Pillar A: Multi-Agent AI Integration (LangGraph / MCP)

### Goal
Deploy autonomous AI operations agents to monitor high-value orbital assets (e.g., ISS), detect escalations, and draft maneuver recommendations.

### Architecture Direction
- **Agent Orchestrator:** LangGraph workflow graph (monitor → analyze → recommend → explain → handoff)
- **Tooling Protocol:** MCP tools for:
  - conjunction query access
  - orbital propagation service access
  - policy/rulebook retrieval
  - notification dispatch
- **Agent Types:**
  - Watch Agent (continuous monitoring)
  - Risk Analyst Agent (contextual threat scoring)
  - Maneuver Drafting Agent (delta-v option generation)
  - Comms Agent (human-readable incident briefing)

### Required Deliverables
- Agent execution audit trail
- Human approval gates before any recommended action is operationalized
- Explainability artifacts for every recommendation

---

## 10.3 Roadmap Pillar B: Advanced Physics (SGP4-Centric Propagation)

### Goal
Move from simplified/sampled propagation assumptions toward high-accuracy SGP4-derived trajectory prediction pipeline.

### Architecture Direction
- Introduce explicit propagation abstraction:
  - `Propagator` interface
  - `SkyfieldPropagator` (current baseline)
  - `SGP4Propagator` (high-accuracy mode)
- Add precision validation suite:
  - benchmark test vectors
  - tolerance thresholds per orbit class
- Persist propagated ephemeris slices for downstream inference and rendering.

### Expected Outcomes
- Improved conjunction timing accuracy
- Better miss-distance reliability under high relative velocity scenarios

---

## 10.4 Roadmap Pillar C: Real-Time Notification System (WebSockets)

### Goal
Eliminate polling-only alert latency by pushing conjunction events instantly to clients.

### Architecture Direction
- FastAPI WebSocket channel(s):
  - `/ws/alerts`
  - `/ws/system-status`
- Event producer from conjunction engine + prediction updates
- Optional Redis pub/sub bridge for multi-instance scaling
- Frontend subscription layer updates Zustand directly

### UX Outcomes
- Immediate tactical alerting
- Reduced stale-state windows during critical conjunction windows

---

## 10.5 Roadmap Pillar D: Debris Tracking Expansion at Scale

### Goal
Scale from handfuls of sample objects to thousands of tracked satellites/debris objects.

### Architecture Direction
- Build ingestion pipeline for large TLE/debris catalogs
- Parallelize conjunction candidate generation
- Apply spatial/time-window pruning before pairwise computations
- Introduce persistence/indexing strategy:
  - object metadata index
  - ephemeris snapshots
  - conjunction event index for fast retrieval

### Performance Requirements
- Deterministic batch windows
- Backpressure-aware ingestion
- Profiling + observability around compute hotspots

---

## 10.6 Suggested Phased Execution Plan

### Phase 1 — Foundation Hardening
- Implement JWT auth and protect sensitive routes
- Replace in-memory cache with Redis
- Align frontend/backend auth contract
- Add CI checks for lint/type/tests

### Phase 2 — Scientific & ML Upgrade
- Add GradientBoosting model path
- Implement model comparison/selection framework
- Establish SGP4 propagation layer and precision benchmarks

### Phase 3 — Real-Time Ops
- Add WebSocket channels and frontend live subscription
- Add event severity routing and operator notification UX

### Phase 4 — Intelligent Operations
- Integrate LangGraph/MCP multi-agent system for autonomous monitoring + recommendations
- Add explainability reports and human approval workflow

### Phase 5 — Scale & Productization
- Debris-scale ingestion/indexing/parallel processing
- SLOs, observability, resilience testing
- Portfolio-grade demo scripts + architecture case study assets

---

## 11. Quality Gates and Definition of Done

Any feature is “done” only when:
1. Architectural boundary is respected (no cross-layer leakage).
2. Typed contracts are complete and synchronized across backend/frontend.
3. Security implications are addressed explicitly.
4. Performance implications are measured for critical paths.
5. Tests cover critical behavior and failure modes.
6. Operational UX states (loading/error/degraded/online) are handled.
7. Blueprint documentation is updated with behavior changes.

---

## 12. Immediate Priority Backlog (Highest Value)

1. Implement backend OAuth2/JWT auth and protect non-public endpoints.
2. Introduce Redis cache layer and swap endpoint cache backend.
3. Add backend `/auth/register` + `/auth/token` to match frontend service contracts.
4. Add GradientBoosting training path and comparative evaluation output.
5. Migrate frontend UI sans font to Inter/Geist standard.
6. Introduce WebSocket alert feed scaffolding.
7. Start SGP4 propagation abstraction and benchmark harness.

---

## 13. Source-of-Truth Notes

- This blueprint intentionally separates:
  - **Current implementation truth** (what code currently does),
  - **Strict target standards** (what architecture must become),
  - **Roadmap evolution** (how to get there).
- Where README claims exceed current implementation (e.g., OAuth2/JWT + Redis active hardening), this document records the implementation gap explicitly as the governing truth for planning.

---

## 14. Exhaustive File Coverage Reference

The following project files under `backend/` and `frontend/` were scanned for this blueprint.

### 14.1 Backend Scanned Files
- `backend/AGENTS.md`
- `backend/api/__init__.py`
- `backend/api/main.py`
- `backend/api/routes.py`
- `backend/core/__init__.py`
- `backend/core/auth.py`
- `backend/core/cache.py`
- `backend/core/config.py`
- `backend/ml/__init__.py`
- `backend/ml/data_pipeline.py`
- `backend/ml/feature_engineering.py`
- `backend/ml/predictor.py`
- `backend/ml/schemas.py`
- `backend/ml/training.py`
- `backend/models/.gitkeep`
- `backend/models/collision_model.meta.json`
- `backend/requirements.txt`
- `backend/test.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_data_pipeline.py`
- `backend/tests/test_feature_engineering.py`
- `backend/train_model.py`

### 14.2 Frontend Scanned Files
- `frontend/AGENTS.md`
- `frontend/.env.example`
- `frontend/.eslintrc.json`
- `frontend/next-env.d.ts`
- `frontend/next.config.mjs`
- `frontend/package.json`
- `frontend/package-lock.json` (dependency lock surface sampled for root constraints and dependency graph anchor)
- `frontend/postcss.config.mjs`
- `frontend/scripts/copy-cesium-assets.mjs`
- `frontend/src/app/error.tsx`
- `frontend/src/app/globals.css`
- `frontend/src/app/layout.tsx`
- `frontend/src/app/page.tsx`
- `frontend/src/app/providers.tsx`
- `frontend/src/components/cesium/CesiumViewer.tsx`
- `frontend/src/components/cesium/CesiumWrapper.tsx`
- `frontend/src/components/cesium/useSceneManager.ts`
- `frontend/src/components/dashboard/CollisionAlerts.tsx`
- `frontend/src/components/dashboard/SystemStatus.tsx`
- `frontend/src/components/dashboard/TelemetryPanel.tsx`
- `frontend/src/components/dashboard/TimelineScrubber.tsx`
- `frontend/src/components/ui/badge.tsx`
- `frontend/src/components/ui/button.tsx`
- `frontend/src/components/ui/card.tsx`
- `frontend/src/components/ui/input.tsx`
- `frontend/src/hooks/useSimulationPolling.ts`
- `frontend/src/lib/auth.ts`
- `frontend/src/lib/cesiumCoordinates.ts`
- `frontend/src/lib/env.ts`
- `frontend/src/lib/math.ts`
- `frontend/src/lib/tleParser.ts`
- `frontend/src/lib/utils.ts`
- `frontend/src/services/apiClient.ts`
- `frontend/src/services/authService.ts`
- `frontend/src/services/mockData.ts`
- `frontend/src/services/simulationService.ts`
- `frontend/src/store/useSimulationStore.ts`
- `frontend/src/types/index.ts`
- `frontend/tailwind.config.ts`
- `frontend/tsconfig.json`

### 14.3 Non-Source Artifacts
- Binary artifacts (e.g., `*.joblib`) are treated as opaque model payloads and represented via their companion metadata for architecture documentation.

---

## 15. Final Principle

This project should read like a mission system, not a class demo: explicit contracts, deterministic behavior, measurable quality, and disciplined architecture decisions.  
**No vibe-coding.**
