# Invoice Automator Roadmap

## Phase 1: Core Ingestion & Extraction (COMPLETED)
**Goal:** Reliable data extraction from PDF invoices.
- [x] **Infrastructure Setup**:
    - [x] Ensure Supabase Auth is working for multi-tenant (if needed) or single store.
    - [x] S3 bucket for invoice storage.
- [x] **Ingestion**:
    - [x] Web UI for Drag & Drop PDF upload.
    - [x] `/api/invoices/upload` endpoint optimization.
- [x] **Parsers**:
    - [x] Implement/Tune LLM prompts for Liquor Invoice structure.
    - [x] Focus on critical fields: SKU, Qty, Cost, Total.
    - [x] Add specific logic for splitting "Case" vs "Bottle" if needed (or just extract as is).

## Phase 2: Review & Validation Interface (COMPLETED)
**Goal:** Empower users to catch errors efficiently.
- [x] **UI Development**:
    - [x] Split-screen view: PDF on left, Extracted Data on right.
    - [x] Editable grid for Line Items.
- [x] **Validation Logic**:
    - [x] Implement `math_check` (Qty * Cost == Total).
    - [x] Implement `footing_check` (Sum(Lines) == Subtotal).
    - [x] Highlight invalid fields in Red.

## Phase 3: Export & Integration (COMPLETED)
**Goal:** Get data OUT in a format the POS understands.
- [x] **Export Engine**:
    - [x] Create `CSVExportService`.
    - [x] Define "Liquor Store Standard" CSV format (or configurable).
    - [x] Add "Download CSV" button to Review page.
    - [x] **Category Alignment**: Strict GL Categories (Beer, Wine, etc.)
- [x] **Error Tracking**:
    - [x] Simple dashboard showing "Invoices Processed" vs "Invoices with Errors".

## Phase 4: Pilot Launch (NOW)
**Goal:** User testing with one store.
- [ ] **Deployment**:
    - [ ] Deploy Backend (Render/Railway/Vercel).
    - [ ] Deploy Frontend (Vercel).
    - [ ] Configure Environment Variables (Supabase, OpenAI, AWS S3).
- [ ] **Onboarding**:
    - [ ] Create Pilot User Account.
    - [ ] Seed "GL Categories" for the new Organization.
- [ ] **Feedback Loop**:
    - [ ] Verify "Report Issue" flow.
    - [ ] Weekly sync with the store manager.
