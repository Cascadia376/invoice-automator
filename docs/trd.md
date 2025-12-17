Technical Requirements Document (Updated)

Scope
- Invoice ingestion, extraction, review/edit, validation, CSV export, vendor/GL management.
- No third-party accounting push (QuickBooks/Xero) and no Stripe/billing flows.

Architecture
- Backend: FastAPI, SQLAlchemy ORM, Pydantic schemas, uvicorn. Auth via Supabase JWT middleware in `backend/auth.py`.
- Storage: S3 for PDFs (upload, download, presigned URLs). Local `/uploads` mount for dev/demo.
- Parsing: invoice2data templates from DB + local templates; fallback to OpenAI (text or vision) and AWS Textract for scanned docs.
- DB: Postgres (Render) or SQLite local; models in `backend/models.py`; migrations via simple scripts (`migrate.py`, `migrate_line_items.py`).
- Frontend: React + Vite + TypeScript + shadcn UI; state via `InvoiceContext`; routing with React Router; authentication wrapper currently expects a JWT provider (Clerk/Supabase pluggable).

Key Services/Flows
- Upload: `/api/invoices/upload` accepts PDF, stores temp file, uploads to S3, extracts, writes Invoice + LineItems, returns presigned URL for file_url when needed.
- Extraction: `services/parser.py` tries templates → Textract (if S3 info) → OpenAI vision/text; saves generated templates back to DB.
- Validation: `/api/invoices/{id}/validate` compares against vendor history for spikes/anomalies.
- Highlights: `/api/invoices/{id}/highlights` searches PDF for extracted values using PyMuPDF.
- Export: `/api/invoices/{id}/export/csv` with optional column map in query.
- Vendors/GL: CRUD endpoints for vendors, GL categories, SKU→GL lookup; vendor corrections recorded via feedback.
- Demo: `/api/seed/demo` seeds a Stark Industries sample invoice.

- Auth & Security
- Supabase JWT bearer required on main APIs; service API key path optional for scripts (`SERVICE_API_KEY` header).
- Multi-tenancy enforced via `organization_id` filters; ensure all queries include org scope (notably vendor stats).
- CORS currently `*` for MVP; lock to frontend domain for production.
- Upload validation to be tightened (size/type) and temp file handling hardened.

- Environment / Config
- Required: `DATABASE_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_BUCKET_NAME`, `AWS_REGION`, `OPENAI_API_KEY`, `SUPABASE_JWT_SECRET` (+ `SUPABASE_JWT_AUD` if customized), `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` for frontend.
- Optional: `SERVICE_API_KEY`, auth provider issuer/keys for JWT validation.
- Render deploy uses `backend/build.sh` (installs deps, runs simple migrations).

Testing / Verification
- Manual: upload → review → edit → export CSV → view highlights/validation.
- Scripts: `verify_backend.py` installs deps and tries to start API (update to include auth token or health endpoint for full automation).

Risks / Follow-ups
- Concurrency: template temp dir reuse in `parser.get_templates_from_db` can race; move to per-request temp dirs.
- Data leakage: vendor stats queries must always scope by organization_id.
- Logging: avoid dumping LLM responses containing sensitive invoice data.
- CORS/upload: restrict origins and file types; add size limits.

Out of Scope (removed)
- QuickBooks/Xero connectors, webhook/token storage, and push endpoints.
- Stripe checkout/webhooks and subscription state on organizations.
