**AI Invoice Processor — Technical Requirements Document (TRD)
Version: 0.1 (Draft)
 Owner: Product & Engineering
 Audience: Engineering, Security, Data, Ops, Design, Exec Stakeholders
 Scope: MVP → Phase 2

1. Purpose & Scope
This TRD defines the functional and non-functional requirements, architecture, data contracts, integrations, security/compliance posture, testing strategy, SLAs/SLOs, and rollout plan for an AI-powered invoice processing SaaS that ingests invoices from email/upload, extracts structured data, enables human review, and pushes into accounting systems (MVP: QuickBooks Online; Phase 2: Xero).
1.1 In-Scope (MVP)
Email ingestion (Gmail) and manual file upload


Native PDF parsing (text-based); no OCR in MVP


Field extraction: vendor, invoice_number, invoice_date, due_date, total_amount, currency, po_number (optional), tax_total (optional)


Review & correction UI (single-entity)


Push to QuickBooks Online (QBO) Bills API


Basic analytics (volumes, processing time) and audit logs


RBAC: Owner, Bookkeeper, Staff roles


Cost tracking per invoice


1.2 In-Scope (Phase 2)
OCR for scanned PDFs (managed service)


Xero integration


Confidence scoring; low-confidence queue


Duplicate detection; vendor routing rules; bulk review


Basic line-items (description, qty, unit_price, line_total) when reliably extractable


1.3 Out of Scope (Non-goals, MVP)
Mobile apps; vendor portal; receipts/expenses; PO matching; multi-entity; internationalization beyond currency display; SOC 2 certification (prepare but not certify).



2. Success Metrics & Acceptance Criteria
2.1 Product KPIs (MVP exit criteria)
Extraction accuracy (native PDF): ≥ 90% exact-match on core fields on a 500-invoice holdout set; line-items excluded from MVP metric.


Time saved: Median processing time per invoice ≤ 30s (from ingestion available → approved or pushed), excluding human review.


System reliability: 99.5% monthly availability (core APIs + UI) during MVP beta; error rate (5xx) < 0.5% of requests.


Push reliability: ≥ 99% successful push-to-QBO on first attempt; automated retry covers remaining.


Cost per native invoice: ≤ $0.02 infra cost (90th percentile) measured E2E pipeline.


2.2 Engineering Acceptance
All APIs versioned, with OpenAPI spec published.


Observability: tracing, structured logs, RED/USE dashboards, pager runbooks.


Security: data encrypted at rest (AES-256-GCM) and in transit (TLS 1.2+); per-tenant data isolation; least-privilege IAM; audit logs immutable for 1 year.



3. User Roles & Permissions (RBAC)
Owner: Full access to tenant configuration, billing, integrations, rules, and data.


Bookkeeper: Review/approve/edit, push to accounting, manage vendors, view analytics.


Staff: Upload, view own documents, suggest edits; no pushes or rules.


Support (internal): Break-glass read-only via JIT access; all access logged and time-bounded.


MVP Rules: Single-entity per tenant; Phase 2 introduces multi-entity with scoped role bindings per entity.

4. System Architecture
4.1 High-Level Components
Auth Service: OAuth 2.0 (product login), OIDC; provider: email+password + Google login; QBO/Xero OAuth for connectors.


Ingestion Service: Email listener (Gmail), IMAP fallback, file upload endpoint, attachment filtering, MIME validation, content-type detection.


Document Store: Encrypted object storage (e.g., S3) for originals and derivatives; lifecycle policies.


Parsing Service: Native PDF extraction (pdfminer/pdfplumber); layout heuristic layer.


Extraction Service: Rule+LLM hybrid for field extraction; schema & normalization; confidence scoring (Phase 2).


Review UI: React SPA; queue views; diff of extracted vs edited; side-by-side PDF viewer.


Accounting Integration Service: QBO Bill/Vendor APIs; mapping layer; retry & reconciliation.


Workflow Orchestrator: State machine (queued → parsed → extracted → needs_review/ready → pushed/failed); idempotency tokens.


Analytics/Cost Service: Metrics, unit economics, per-invoice cost tracking.


Observability: Centralized logging, metrics, tracing; dead-letter queues.


4.2 Suggested Tech Stack
Frontend: React + TypeScript; Tailwind; component lib; PDF.js viewer.


Backend: Python FastAPI (extraction, parsing) + Node.js (integrations, auth) microservices; gRPC/HTTP internal.


Databases: PostgreSQL (OLTP), Redis (queues/cache), S3-compatible object store.


Async: Managed queue (e.g., SQS); scheduled workers.


Infra: AWS (ECS Fargate or Lambda for parsing/extraction); API Gateway; WAF; KMS for keys.


4.3 Data Flow (MVP)
Ingest: Email webhook/poll → filter invoices → fetch attachments → store object → create document record.


Parse: Detect native PDF → extract text/layout → persist extraction_raw artifact.


Extract: Apply templates/rules/LLM → produce invoice_candidate (core fields) → set confidence (Phase 2).


Review: UI displays fields + PDF preview → user edits → approve.


Push: Map to QBO entities → create/update Vendor if needed → create Bill → attach document link → mark pushed.


Audit/Analytics: Log events; update metrics; cost attribution.


4.4 Sequencing Guarantees & Idempotency
Every pipeline stage includes an idempotency key: tenant_id:source_msg_id:attachment_sha256.


Retries are safe; pushes to QBO guard against duplicate Bills using (vendor, invoice_number, date) and memo hash.



5. Functional Requirements
5.1 Ingestion
FR-ING-001: Connect Gmail account via OAuth; scopes limited to read-only for selected labels.
 FR-ING-002: User designates one or more labels (e.g., Invoices/ToProcess) for monitoring.
 FR-ING-003: Support manual upload of PDFs via UI (drag/drop), max 20 files per batch, max 20 MB/file.
 FR-ING-004: File-type detection distinguishes native PDF vs scanned PDF (image-based).
 FR-ING-005: Store email metadata (from, subject, send_time, message_id) and attachment hash; avoid duplicate ingest by attachment hash.
Validation: Reject non-PDF at MVP; provide error feedback.
5.2 Parsing & Extraction (MVP)
FR-EXT-001: Extract core fields from native PDFs: vendor, invoice_number, invoice_date, due_date, total_amount, currency, (optional) tax_total, po_number.
 FR-EXT-002: Normalize dates (ISO-8601), currency (ISO 4217), and numeric formatting (locale-agnostic).
 FR-EXT-003: Provide vendor resolution using heuristics (from email domain, header/footer patterns).
 FR-EXT-004: Persist extraction provenance: model version, ruleset version, artifact checksums.
 FR-EXT-005: Confidence score placeholder fields present but may be null in MVP.
5.3 Review & Correction UI
FR-REV-001: Present side-by-side PDF + extracted fields; editable inputs with validation.
 FR-REV-002: States: needs_review, ready_to_push, pushed, failed.
 FR-REV-003: Bulk actions (Phase 2): approve/reject/assign vendor; keyboard shortcuts.
 FR-REV-004: Change history per field (who, when, before/after).
 FR-REV-005: Surface potential duplicates and mismatches (Phase 2).
5.4 Accounting Integrations
FR-ACC-001: QBO OAuth (tenant-level) with refresh token management.
 FR-ACC-002: Vendor mapping: resolve to existing vendor; if not found, create vendor with minimal fields.
 FR-ACC-003: Create Bill with core fields; attach external document link; set due_date if provided.
 FR-ACC-004: Robust error handling with categorized error codes; auto-retry on 429/5xx with exponential backoff.
 FR-ACC-005: Status callback: show pushed/error with actionable message; allow manual retry.
5.5 Rules & Duplicates (Phase 2)
FR-RUL-001: Vendor-based auto-approval thresholds (e.g., if vendor=ABC & total<500 → auto-approve).
 FR-RUL-002: Duplicate detection using (vendor_id, invoice_number, invoice_date) and total hash.
 FR-RUL-003: Confidence-threshold routing to review queue.
5.6 Analytics & Reporting
FR-ANL-001: Tenant dashboard: invoices ingested, processed, pushed; average processing time; estimated time saved.
 FR-ANL-002: Accuracy dashboard (internal): precision/recall on labeled set; drift over time.
 FR-ANL-003: Cost dashboard (internal): cost per stage per invoice; alarms on thresholds.

6. External Interfaces (APIs & Connectors)
6.1 Public REST API (MVP subset)
Auth: OAuth2 Authorization Code + PKCE.


Base URL: /api/v1


Endpoints
POST /documents:upload — multipart PDF upload; returns document_id.


GET /documents/{document_id} — fetch document metadata + extraction status.


GET /invoices/{invoice_id} — fetch extracted invoice (read-only for MVP).


POST /invoices/{invoice_id}/approve — mark ready to push.


POST /invoices/{invoice_id}/push — initiate push to QBO.


Common Response Fields
{
  "id": "uuid",
  "tenant_id": "uuid",
  "state": "needs_review|ready_to_push|pushed|failed",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601"
}

6.2 Gmail Connector
OAuth scopes: https://www.googleapis.com/auth/gmail.readonly


Strategy: label-based polling every 5 minutes (MVP); push notifications optional later.


Failure handling: incremental sync via historyId; resume on errors.


6.3 QuickBooks Online Connector
OAuth 2.0; token refresh; tenant realmId stored encrypted.


APIs used: Vendors, Bills, Attachments (or external link).


Rate limit handling: backoff with jitter; idempotency via DocNumber and custom memo fingerprint.


6.4 Xero Connector (Phase 2)
Similar OAuth; organization selection; Bills endpoint equivalent; attachment link if supported.



7. Data Model (Core Schemas)
7.1 Entities (simplified JSON)
Tenant
{
  "id": "uuid",
  "name": "string",
  "plan": "basic|advanced|legacy_ltd",
  "entity_mode": "single|multi",
  "created_at": "ISO",
  "settings": {
    "email_labels": ["Invoices/ToProcess"],
    "currency": "USD",
    "qbo_realm_id": "string|null"
  }
}

User
{
  "id": "uuid",
  "tenant_id": "uuid",
  "role": "owner|bookkeeper|staff|support",
  "email": "string",
  "status": "active|invited|disabled"
}

Document
{
  "id": "uuid",
  "tenant_id": "uuid",
  "source": "email|upload",
  "source_meta": {"gmail_message_id": "...", "sender": "..."},
  "content_type": "application/pdf",
  "storage_key": "s3://...",
  "sha256": "hex",
  "is_scanned": false,
  "state": "ingested|parsed|extracted|needs_review|ready_to_push|pushed|failed"
}

Invoice
{
  "id": "uuid",
  "tenant_id": "uuid",
  "document_id": "uuid",
  "vendor_id": "uuid|null",
  "fields": {
    "vendor_name": "string",
    "invoice_number": "string",
    "invoice_date": "YYYY-MM-DD",
    "due_date": "YYYY-MM-DD|null",
    "currency": "USD",
    "total_amount": 123.45,
    "tax_total": 0.0,
    "po_number": "string|null"
  },
  "line_items": [],
  "confidence": null,  // number in Phase 2
  "push": {
    "target": "qbo|xero|null",
    "status": "pending|pushed|error",
    "external_id": "string|null",
    "last_error": "string|null"
  }
}

Vendor
{
  "id": "uuid",
  "tenant_id": "uuid",
  "name": "string",
  "email_domain": "string|null",
  "qbo_vendor_id": "string|null",
  "canonical_aliases": ["ABC Supplies", "A.B.C. Supplies"]
}

Rule (Phase 2)
{
  "id": "uuid",
  "tenant_id": "uuid",
  "type": "auto_approve|route|flag_duplicate",
  "predicate": {"vendor_id": "uuid", "total_lt": 500},
  "action": {"set_state": "ready_to_push"}
}

AuditLog
{
  "id": "uuid",
  "tenant_id": "uuid",
  "actor_type": "user|system",
  "actor_id": "uuid|null",
  "entity_type": "invoice|document|vendor|integration",
  "entity_id": "uuid",
  "event": "created|updated|approved|pushed|error",
  "diff": {"field": ["before", "after"]},
  "ts": "ISO"
}


8. Algorithms & Extraction Logic
8.1 Native PDF Extraction (MVP)
Text layer: pdfplumber parsing; retain positional blocks; segment into header/body/footer.


Heuristics:


Vendor: max-weight match among header tokens (dictionary + sender domain + known vendor aliases).


Invoice number/date: regex + proximity to keywords ("Invoice", "Invoice #", "Date").


Due date: nearest future date token following keywords.


Currency: symbol detection (",$", "€") + ISO mapping; fallback to tenant currency.


Total: bold/boxed numeric near keywords ("Total", "Amount Due").


Normalization: date parser (day-first vs month-first), strip thousands separators, decimal normalization.


8.2 Confidence (Phase 2)
Feature vector per field (regex score, keyword proximity, font weight, position, historical vendor template) → calibrated probability via logistic regression or lightGBM; threshold to route to review.


8.3 Duplicate Detection (Phase 2)
Blocking key (vendor_id, invoice_number); soft match on numbers with punctuation normalization; cross-check abs(total_amount - existing.total) < $0.01.



9. Non-Functional Requirements
9.1 Security & Privacy
Encryption: At rest AES-256-GCM (SSE-KMS); in transit TLS 1.2+; key rotation 90 days.


Secrets: Stored in secrets manager; no secrets in code or env files.


PII: Minimal collection; data classification inventory; restrict access by tenant; field-level encryption for vendor names optional.


Email Scopes & Consent: Narrow Gmail scopes; explicit consent screen lists label access; ability to revoke and delete data.


Data Retention: Originals retained 90 days by default; derivatives 12 months; audit logs 12 months; configurable per tenant.


Right to Erasure: Tenant-level purge tooling with tombstoning; 30-day backup lag.


Logging Hygiene: No raw tokens; redact PII in logs; separate secure log sink.


Compliance Path: GDPR-ready; SOC 2 readiness tasks (asset inventory, access reviews, change management) tracked; pen-test before GA.


9.2 Reliability & Performance
Availability (Beta): 99.5% monthly; GA: 99.9%.


Latency Targets:


Upload → parsed: p95 ≤ 10s (native PDF ≤ 2 MB)


Approve → pushed: p95 ≤ 5s (excluding external API latency)


Scalability: 1M invoices/month initial capacity; horizontal worker autoscaling on queue depth.


Backpressure: Rate limit inbound ingestion; DLQ on persistent failures; circuit breaker when QBO limits hit.


9.3 Observability
Metrics (RED/USE): request_rate, error_rate, duration; worker throughput; queue depth; OCR usage (Phase 2); push success rate; cost per invoice.


Tracing: Distributed traces with correlation id x-trace-id; spans across parse/extract/push.


Logging: JSON structured logs; PII redaction; event IDs.


Alerts:


Error rate >1% 5m


Push success <98% 15m


Cost >$0.03 native p90 1h


Queue delay >2m p95 10m



10. UI/UX Requirements (MVP)
Navigation: Dashboard → Invoices → Review → Integrations → Settings.


Invoice Review:


PDF preview left; fields panel right.


Inline validation (date formats, currency codes, numeric ranges).


Hotkeys (save Cmd/Ctrl+S, next J, previous K).


Status chips; error banners with actionable messages.


Integrations Page: Connect QBO (OAuth), select company; test connectivity; last sync status.


Accessibility: WCAG 2.1 AA for form fields, focus states, contrast.



11. Testing & Quality Plan
11.1 Test Data & Benchmarks
Corpus: ≥ 1,000 native PDFs across 50+ vendors; stratified by layout; redacted set for CI.


Ground Truth: Labeled JSON for core fields; annotation tool & guidelines.


Benchmark Runs: PR-level regression on 200-doc subset; nightly on full set.


11.2 Automated Tests
Unit tests (≥80% for extraction/parsing libs); property-based tests for date/money parsers.


Contract tests against QBO sandbox.


E2E flows (Cypress/Playwright): upload → review → push.


Load tests: 50 RPS document ingestion; 500 concurrent review sessions.


11.3 Manual QA
Exploratory testing scripts per feature; accessibility checks; cross-browser matrix.


11.4 Security Testing
Static analysis (SAST), dependency scanning; secrets scanning; external pen-test pre-GA.



12. Deployment, Environments, & Feature Flags
Envs: dev, staging, prod; isolated resources; separate KMS keys.


CI/CD: trunk-based; automated build/test/deploy; infra as code (Terraform/CDK).


Feature Flags: OCR, Xero, bulk review, confidence scoring, rules; percentage rollouts.


Migrations: Alembic (Postgres); backfill jobs idempotent.



13. Cost Model & Budgets (MVP)
Parsing/Extraction: target ≤ $0.01/invoice native.


Storage: ≤ $0.002/invoice/month (90-day retention for originals).


Networking & Misc: ≤ $0.003/invoice.


Total Target: p90 ≤ $0.02/invoice native.
 Alarms: breach for 3 consecutive hours triggers on-call + rollback to cheaper path (e.g., rules-only extraction).



14. Rollout Plan
Phase A (Private Beta, 3–5 tenants):


Success: ≥90% accuracy, ≥95% push success, <24h onboarding.


Phase B (Public Beta, up to 100 tenants):


Enable LTD codes (legacy_ltd plan), rate-limit ingestion to guarantee SLOs.


GA:


Open self-serve signups; introduce multi-entity (feature-flagged), rules, and OCR.


Kill/Pivot Criteria: after 2 pilot cycles, if accuracy <85% or <30% of invoices are native PDFs for target vertical, revisit OCR priority and pricing.

15. Risk Register & Mitigations
R1 Extraction accuracy below threshold → Expand vendor templates; add human-in-loop queue; active learning.


R2 QBO/Xero API changes/outages → Circuit breakers; cached vendor mapping; offline queue; status page comms.


R3 Cost creep (OCR in Phase 2) → Pre-flight native/scan detection; OCR only on demand; compress images; renegotiate OCR pricing.


R4 Data privacy incident → Zero-trust access; JIT support access; audit trail; incident response playbooks.


R5 Abuse (spam email ingestion) → Domain allowlist; sender reputation checks; size/type quotas.



16. Open Questions
Do we support non-PDF formats (e.g., HTML invoices) in MVP? (Recommend: no.)


Attachments as QBO file vs external link: storage + privacy trade-offs? (Recommend: external link at MVP, file later.)


Minimum vendor metadata to create in QBO when absent (address, tax_id)?


Do we block approval if due_date missing? (Recommend: allow, warn.)


Are LTD plan limits enforced on invoice count per rolling 30 days or calendar month? (Recommend: rolling window.)



17. Appendices
17.1 Sequence Outline (Textual)
Email → Ingest: Gmail label poll → new message ids → fetch attachments → create Document → enqueue Parse.


Parse → Extract: Detect native → parse text → run rules & models → create Invoice candidate → set state.


Review → Push: User edits → approve → push to QBO → update status and audit.


17.2 Monitoring Dashboards (MVP)
Pipeline: ingest rate, parse latency, extract latency, review queue depth, push success.


Quality: extraction precision/recall (by field), vendor coverage, error taxonomy.


Cost: per-stage cost breakdown; top vendors by cost; anomalies.


17.3 QBO Mapping (MVP)
Vendor: by DisplayName exact/alias match; create if not found.


Bill: VendorRef, TxnDate (invoice_date), DueDate, DocNumber (invoice_number), CurrencyRef, PrivateNote (po_number), Line (summary line only in MVP), Attachment link.




18. Engineering Roadmap & Delivery Plan
18.1 Execution Waves
Wave
Calendar
Primary Goals
Major Deliverables
Dependencies & Enablers
Exit Criteria
Wave 0 — Foundations
Weeks 0–4
Set up core platform, environments, and guardrails for closed beta.
• IaC for dev/staging/prod with networking, secrets, CI/CD
• Multi-tenant data model + Postgres/S3 provisioning
• Gmail ingestion pipeline (poller, dedupe, storage)
• Baseline React app shell with auth & RBAC scaffolding
• Observability bootstrap (logging, metrics collectors)
Infra, Platform, Security approvals
• End-to-end ingest → store smoke test
• Access reviews & secrets rotation automated
Wave 1 — MVP Pipeline
Weeks 5–10
Deliver ingest→extract→review→push flow with QBO integration.
• Native PDF parsing service (FastAPI) + vendor heuristics
• Extraction service + schema normalization
• Review UI with edit/approve/audit log
• QBO connector (sandbox + retry/backoff)
• Automated regression suite (unit + contract)
Wave 0 complete; labeled invoice corpus ready
• ≥85% extraction accuracy on labeled set
• Push success ≥95% in sandbox
Wave 2 — Reliability & Beta Hardening
Weeks 11–16
Improve accuracy, resilience, and operational readiness for private beta scale.
• Vendor template tuning + active learning loop
• Cost telemetry + per-invoice cost dashboards
• Alerting playbooks, runbooks, on-call rota
• Security controls: encryption verification, audit log immutability
• Billing/plan limits enforcement (basic plan)
Wave 1 exit criteria met; GTM beta plan approved
• Accuracy ≥90%, cost ≤$0.02 native p90
• Pager coverage with tested incident drill
Wave 3 — Public Launch Enablement
Weeks 17–24
Enable self-serve, support workflows, and pricing packaging for GA.
• Self-serve onboarding & invitations
• Support tooling (JIT access, redaction tools)
• Usage-based limits & throttling
• Analytics dashboard (tenant + internal)
• Documentation & status page integration
Wave 2 complete; legal review of TOS/PP
• Public beta NPS ≥30; churn <10%
• GA checklist signed by Product/Security
Wave 4 — Phase 2 Feature Set
Months 7–9
Expand to OCR, Xero, and automation rules.
• OCR service integration + routing decisioning
• Confidence scoring pipeline + low-confidence queue
• Xero connector + reconciliation tests
• Duplicate detection + vendor routing rules
• Bulk review experience & keyboard shortcuts
Wave 3 complete; OCR vendor contract executed
• OCR accuracy ≥80% on scanned docs
• Auto-approval rate >50% for trusted vendors
Wave 5 — Scale & Ecosystem
Months 10–12
Harden for multi-entity, marketplace, and partnerships.
• Multi-entity tenancy model + scoped RBAC
• Vendor portal prototype + API surface review
• Receipts/expenses ingestion experiment
• Marketplace listing requirements (QBO/Xero) met
• Partner enablement playbooks & telemetry
Wave 4 complete; compliance gap assessment done
• ARR run-rate ≥$1.2M
• Marketplace approvals secured

18.2 Cross-Functional Alignment
Discipline
Key Responsibilities per Wave
Product Management
Prioritize backlog, define beta cohorts, coordinate pricing/packaging experiments, track KPI gates.
Engineering Leads
Wave planning, resource allocation, architecture governance, risk tracking, delivery reporting.
ML/Data
Labeling operations, model evaluation, accuracy tuning, cost analytics ownership.
Security & Compliance
IAM reviews, data retention policies, incident response readiness, vendor risk assessments.
Customer Success & Support
Beta tenant onboarding, feedback loops, support workflows, knowledge base.
Finance & Ops
Monitor unit economics, approve infrastructure budget, billing reconciliation, ARR tracking.

18.3 Decision & Review Cadence
• Bi-weekly architecture council: review service designs, debt, and upcoming integrations.
• Monthly roadmap checkpoint: reassess wave exit criteria, re-sequence based on KPI performance.
• Quarterly exec readout: summarize delivery status, risks, and financial impact; greenlight next wave.
• Post-wave retrospectives feeding into risk register updates and tooling investments.


