# Strategic AI Nexus — Advanced Command Dashboard

Next.js dashboard for the Strategic AI Nexus geopolitical simulation backend.

## Run locally

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

Create `.env.local` from `.env.example`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

## Backend contract

- `POST /api/simulation/create`
- `POST /api/simulation/start/{sim_id}`
- `POST /api/simulation/pause/{sim_id}`
- `POST /api/simulation/resume/{sim_id}`
- `POST /api/simulation/stop/{sim_id}`
- `GET /api/simulation/status/{sim_id}`
- `GET /api/state/current/{sim_id}`
- `GET /api/state/history/{sim_id}`
- `GET /api/analytics/performance/{sim_id}`
- `WS /ws?room={sim_id}`

The dashboard consumes the engine's `environment` metrics and normalizes them into the UI state model. WebSocket connections automatically reconnect with exponential backoff.
