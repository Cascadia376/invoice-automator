# Invoice Automator

FastAPI + React app for ingesting invoices, extracting structured data (Textract + LLM/templates), reviewing edits, and exporting CSVs. Supabase JWT auth supported; auth can be disabled for local setup.

## Principles
- Security first: least-privilege AWS/IAM, no public buckets, and JWT-guarded APIs (bypass only for local dev).
- Simple ops: no Docker required; native builds on Render/Vercel with minimal env needed.
- Tenant isolation: every record keyed by `organization_id`; keep CORS scoped to your frontend in production.

## Stack
- Backend: FastAPI, SQLAlchemy, Pydantic, AWS S3/Textract, OpenAI
- Frontend: React (Vite/TS), shadcn UI, Tailwind
- Auth: Supabase JWT (optional bypass via `DISABLE_AUTH`/`VITE_DISABLE_AUTH`)

## Prereqs
- Python 3.10+
- Node 18+ / npm
- AWS creds for S3/Textract (or stub storage for local)
- Supabase project (URL, anon key, JWT secret) if enabling auth

## Backend setup
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate  # or source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Env (set in shell or `.env`):
- `DATABASE_URL` (sqlite default works)
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_BUCKET_NAME`, `AWS_REGION`
- `OPENAI_API_KEY`
- `SUPABASE_JWT_SECRET` (and `SUPABASE_JWT_AUD` if non-default)
- `SERVICE_API_KEY` (optional for scripts)
- `DISABLE_AUTH=true` to bypass auth locally

## Frontend setup
```bash
cd frontend
npm install
npm run dev
```
Env (`frontend/.env`):
- `VITE_API_BASE` (e.g., http://localhost:8000 or Render URL; defaults to same-origin `/api`)
- `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
- `VITE_DISABLE_AUTH=true` to bypass auth locally

## Deploy targets
- Frontend: Vercel (root `frontend`, build `npm run build`, output `dist`)
- Backend: Render web service (root `backend`, build `./build.sh`, start `uvicorn main:app --host 0.0.0.0 --port $PORT`)

## Notes
- QBO/Stripe integrations removed.
- CSV export available at `/api/invoices/{id}/export/csv` with optional column mapping.
- Demo data: `POST /api/seed/demo` (auth required unless bypass enabled).
