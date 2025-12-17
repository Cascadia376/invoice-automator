AI Invoice Processor — PRD (Updated)

Scope
- Current product: ingest invoices (upload/email-ready), extract with hybrid parser (templates + LLM/vision + Textract fallback), human review/edit, CSV export, and vendor/GL management. No billing/subscription flows and no third‑party accounting push (QuickBooks/Stripe removed).

Problem & Opportunity
- SMB finance teams waste hours re‑keying invoice data into spreadsheets/accounting tools; errors create reconciliation risk.
- Opportunity: fast, accurate extraction with a tight review loop and export-ready data to drop into any stack.

Goals & KPIs
- Time saved: ≥70% vs manual entry (target: ≤2.4h/week from 8h).
- Extraction accuracy: ≥90% native PDFs, ≥80% scanned.
- Review throughput: ≥10 invoices/day in pilot; >50% invoices auto-approve once confidence improves.
- Churn proxy: N/A (no billing live); measure weekly active reviewers and exports.

Users & Jobs
- SMB operators/bookkeepers: upload/review/export clean invoice data.
- Agencies/outsourced bookkeeping: multi-tenant handling with org scoping, GL categories, vendor normalization.

Core Workflow (MVP)
1) Upload PDF (native preferred; Textract + vision fallback for scans).
2) Extract: vendor, invoice number, dates, totals, line items with confidence.
3) Review & edit: validation hints, highlights, optimistic save.
4) Export: CSV with configurable columns/headers; presigned PDF access.

Out of Scope (removed)
- QuickBooks/Xero push flows.
- Stripe billing/checkout, subscription states on Organization.

Functional Requirements (current)
- Auth: Supabase JWT via backend `auth.py` (service API key path remains for scripts).
- Ingestion: `/api/invoices/upload` accepts PDF → stores in S3 → parses → persists invoice + line items.
- Review: list, detail, update, validation service for anomalies, feedback endpoint to refine templates.
- Vendors/GL: CRUD for vendors and GL categories; SKU→GL lookup.
- Export: `/api/invoices/{id}/export/csv` with selectable headers.
- Demo: `/api/seed/demo` generates a sample invoice.

Non‑Functional
- Multi-tenant isolation by `organization_id`.
- Storage: S3 for PDFs; presigned URLs for access.
- DB: Postgres/SQLite via SQLAlchemy; tables auto-created.
- Security: JWT auth required on APIs; CORS configurable (currently permissive for MVP).

Roadmap (near-term)
- Harden auth guard UX (Supabase) and session handling in frontend.
- Tighten CORS and upload validation (size/type).
- Improve template concurrency (per-request temp dirs).
- Add duplicate detection and better validation heuristics.
- Optional future: reintroduce accounting connectors behind feature flags.

Success Criteria (pilot)
- ≥90% accuracy on native PDFs across top vendors.
- Review-to-export cycle <2 minutes for typical invoice.
- Zero cross-org data leaks in vendor stats/queries.
