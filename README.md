## WhatsApp Web Clone (FastAPI + React)

A small full-stack app that ingests simulated WhatsApp webhook payloads into MongoDB and displays a WhatsApp Web–like UI. Supports storing new outbound messages (no external sending).

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB Atlas account (free tier OK)

### Environment Variables
Create a `.env` from `.env.example` at the repo root and fill values:
- `MONGODB_URI` (required): your Atlas connection string including db name `whatsapp`.
- `CORS_ORIGINS` (optional): comma-separated allowed origins for the backend.
- `VITE_API_BASE_URL` (frontend): URL of the deployed backend or `http://localhost:8000` for dev.

### Project Structure
- `backend/` — FastAPI app (APIs + optional WebSocket)
- `frontend/` — React (Vite) SPA
- `scripts/` — data ingestion and utility scripts
- `docs/` — extra notes/screenshots
- `whatsapp sample payloads/` — provided JSON payloads to seed the DB

### Local Quickstart
1) Backend
- `python -m venv backend/.venv && source backend/.venv/bin/activate`
- `pip install -r backend/requirements.txt`
- `uvicorn app.main:app --app-dir backend --reload`

2) Frontend
- `cd frontend && npm install`
- `VITE_API_BASE_URL=http://localhost:8000 npm run dev`

3) Ingest sample payloads (one-time)
- `source backend/.venv/bin/activate`
- `python scripts/ingest_payloads.py`

### Deployment

#### Backend on Render
- Use `render.yaml` (Blueprint) or create a Web Service:
  - Runtime: Python
  - Build Command: `pip install -r backend/requirements.txt`
  - Start Command: `uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT`
  - Env Vars:
    - `MONGODB_URI`: your Atlas URI
    - `CORS_ORIGINS`: your frontend origin (e.g., `https://<your-vercel-domain>`) or `*` for testing
- After first deploy, run `scripts/ingest_payloads.py` locally to seed Atlas (or add a one-off job).

#### Frontend on Vercel
- In `frontend/` run `npm run build` locally to verify.
- Push repo or import `frontend/` in Vercel.
- Framework Preset: Vite
- Build Command: `npm run build`
- Output Directory: `dist`
- Env Vars:
  - `VITE_API_BASE_URL`: your Render backend URL (e.g., `https://<render-app>.onrender.com`)

### Notes
- WebSocket endpoint: `/ws` (used for realtime updates)
- Polling fallback: 5s
- Status ticks: ✓ (sent), ✓✓ (delivered grey), ✓✓ blue (read)