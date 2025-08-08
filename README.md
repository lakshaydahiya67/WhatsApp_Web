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

### Quickstart (Local)
1) Setup env
- Duplicate `.env.example` → `.env` and set `MONGODB_URI`.

2) Backend
- Create venv, install deps, run FastAPI (to be added in step 2.x tasks).

3) Frontend
- `npm install` then `npm run dev` (to be added in step 5.x tasks).

4) Ingest sample payloads
- Run `scripts/ingest_payloads.py` once (will be added in step 3.x tasks).

### Deployment
- Backend: Render/Railway/Heroku/Fly with `MONGODB_URI` set; enable CORS for frontend origin.
- Frontend: Vercel/Netlify; set `VITE_API_BASE_URL` pointing to backend.

See `requirements.md` and `tasks.md` for detailed specs and execution plan.
