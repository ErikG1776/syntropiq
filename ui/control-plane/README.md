# Syntropiq Control Plane UI

Enterprise-grade governance control plane for Syntropiq.

## Stack

- React + TypeScript + Vite
- TailwindCSS
- Recharts
- React Router

## Run

```bash
cd ui/control-plane
npm install
npm run dev
```

Open `http://localhost:5173`.

## Build

```bash
npm run build
npm run preview
```

## Environment Variables

Create `.env` in `ui/control-plane`:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_ENVIRONMENT=DEMO
VITE_ROUTING_MODE=deterministic
```

Allowed values:

- `VITE_ENVIRONMENT`: `DEMO | STAGING | PROD`
- `VITE_ROUTING_MODE`: `deterministic | competitive`

## LIVE / REPLAY Modes

Top bar includes `Mode: LIVE | REPLAY` toggle.

- `LIVE`: Polls FastAPI every 2s
- `REPLAY`: Plays uploaded Lending demo timeline over 25 seconds

REPLAY is default.

## Replay Loader

Use top-right **Replay Loader** (or Settings tab) and upload `demo_results.json` produced by:

```bash
python -m syntropiq.demo.lending.run --real-data --cycles 50 --batch-size 15 --output demo_results.json
```

Replay controls:

- Play
- Pause
- Jump to Suppression
- Cycle timeline scrubber

## API Endpoints

When in LIVE mode, UI calls:

- `GET /api/v1/statistics`
- `GET /api/v1/agents`
- `GET /api/v1/mutation/history`
- `GET /api/v1/reflections`

If API is unavailable, UI falls back to mock data for LIVE mode. REPLAY mode remains deterministic from uploaded JSON (or built-in fallback replay).

## Routes

- `/` Overview
- `/agents`
- `/governance-cycles`
- `/events`
- `/mutation`
- `/reflections`
- `/settings`
