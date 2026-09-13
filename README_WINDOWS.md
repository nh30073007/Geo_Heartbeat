# Strategic AI Nexus — Functional Windows Build

This build connects the GeoPolis dashboard to the FastAPI simulation engine instead of using frozen UI-only demo values.

## What was fixed

- Real-time simulation mode now yields between rounds so 500 rounds do not finish instantly.
- REST state + WebSocket telemetry are wired to the same runtime.
- Manual `End Turn` advances exactly one round while paused.
- Pause / Resume / Reset work against the backend.
- Scenario selector loads real predefined scenarios and starts a fresh simulation.
- Quick Actions apply controlled state changes through the backend event layer.
- Checkpoints and state export are functional.
- JSON/CSV reports are downloadable from the Reports panel.
- Agents, conflicts, economy, technology, resources, treaties, world and analytics navigation is wired.
- Settings, notifications/event stream and Commander panels are functional.
- Backend dependency list now includes the packages actually imported by the project.
- WebSocket simulation-completion payloads are normalized to JSON-safe keys.
- Duplicate simulation IDs are avoided with microsecond + UUID suffixes.
- The engine no longer applies the environment transition twice per round.

## Run on Windows

### First time

Double-click `SETUP_WINDOWS.bat`.

Or manually:

```bat
cd backend
python -m pip install -r requirements.txt
cd ..\frontend
npm install
```

### Start

Double-click `START_WINDOWS.bat`.

Or use two terminals:

```bat
cd C:\path\to\strategic-ai-nexus\backend
python run.py
```

and:

```bat
cd C:\path\to\strategic-ai-nexus\frontend
npm run dev
```

Open `http://localhost:3000`.

## Backend endpoints

- `GET /health`
- `GET /docs`
- `GET /api/simulation/scenarios`
- `POST /api/simulation/create`
- `POST /api/simulation/start/{sim_id}`
- `POST /api/simulation/pause/{sim_id}`
- `POST /api/simulation/resume/{sim_id}`
- `POST /api/simulation/step/{sim_id}`
- `POST /api/simulation/reset/{sim_id}`
- `POST /api/simulation/action/{sim_id}`
- `POST /api/simulation/checkpoint/{sim_id}`
- `GET /api/state/current/{sim_id}`
- `GET /api/state/history/{sim_id}`
- `GET /api/analytics/forecast/{sim_id}`
- `GET /api/analytics/report/{sim_id}?format=json|csv`
- `GET /api/dashboard/overview/{sim_id}` — aggregated live dashboard payload
- `GET /api/dashboard/search/{sim_id}?q=...` — backend search/filter
- `GET /api/dashboard/events/{sim_id}` — live event history/recovery
- `GET /api/dashboard/calendar/{sim_id}` — backend forecast milestones
- `WS /ws?room={sim_id}` — realtime state/event stream

## Important

Do not run `npm run dev` before `npm install`; the original `next is not recognized` error simply meant the frontend dependencies were not installed.

The current UI uses a 0.75-second realtime round interval by default. Change `realtime_interval_seconds` in the frontend create request if you want a faster/slower visualization.

## Frontend data flow

The dashboard hydrates from the dashboard REST aggregation endpoint, then keeps the UI current from the simulation WebSocket. Search queries are sent to FastAPI with a small debounce; the result list navigates to the matching dashboard entity. Charts use the simulation history returned by the engine rather than seeded demo values.

The build intentionally does not include `node_modules`; `SETUP_WINDOWS.bat` installs it automatically when missing.


## 2026-09-09 Stability/RL Update

- WorldMap country selection now supports every marker in the map without 404s; missing demo datasets receive deterministic fallback records.
- CountryCard now matches the backend `/api/country/{country_id}` response contract and safely handles missing fields.
- Dashboard no longer probes a stale persisted simulation ID on boot; it creates and persists a fresh simulation ID.
- Added bounded, optional DQN backend (`RL_BACKEND=dqn`). Default remains `q_learning` for compatibility. DQN uses replay memory, a target network and gradient clipping.
- Added optional semantic reward shaping driven by public sentiment. It has a deterministic local fallback and an optional HTTP LLM scorer (`REWARD_LLM_URL`).
- Forecasting now prefers a lightweight multivariate ridge autoregression for realtime stability; the existing linear model remains the fallback for insufficient history.
- Frontend TypeScript check passes with `npx tsc --noEmit` after a normal `npm install`.

### Windows quick start

Backend:
```bat
cd backend
python -m pip install -r requirements.txt
copy .env.example .env
python run.py
```

Frontend (use a fresh install rather than the bundled OS-specific `node_modules`):
```bat
cd frontend
npm install
npm run dev
```

Optional neural RL:
```bat
set RL_BACKEND=dqn
python run.py
```

## Simulation dynamics calibration (V2)

The environment now includes stability controls to prevent runaway saturation at `economic_stability=0` / `strategic_tension=100`:
- damped strategy effects and bounded adaptive payoff modifiers
- soft mean-reversion toward a healthy equilibrium
- tension relaxation and conflict-fatigue at elevated tension
- nonlinear boundary damping and per-step effect caps
- potential-based normalized RL rewards in `[-1, 1]`

Optional `.env` controls:
```env
TRANSITION_NOISE_SCALE=0.35
TRANSITION_RECOVERY_RATE=0.12
TRANSITION_TENSION_RELAXATION=0.30
TRANSITION_MAX_EFFECT=7.5
```
These are simulation calibration parameters, not live geopolitical measurements.
