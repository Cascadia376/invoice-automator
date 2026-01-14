# Invoice Automator Roadmap

## Phase 1: Core Ingestion & Extraction (Weeks 1-2)
**Goal:** Reliable data extraction from PDF invoices.
- [ ] **Infrastructure Setup**:
    - [ ] Ensure Supabase Auth is working for multi-tenant (if needed) or single store.
    - [ ] S3 bucket for invoice storage.
- [ ] **Ingestion**:
    - [ ] Web UI for Drag & Drop PDF upload.
    - [ ] `/api/invoices/upload` endpoint optimization.
- [ ] **Parsers**:
    - [ ] Implement/Tune LLM prompts for Liquor Invoice structure.
    - [ ] Focus on critical fields: SKU, Qty, Cost, Total.
    - [ ] Add specific logic for splitting "Case" vs "Bottle" if needed (or just extract as is).

## Phase 2: Review & Validation Interface (Weeks 2-3)
**Goal:** Empower users to catch errors efficiently.
- [ ] **UI Development**:
    - [ ] Split-screen view: PDF on left, Extracted Data on right.
    - [ ] Editable grid for Line Items.
- [ ] **Validation Logic**:
    - [ ] Implement `math_check` (Qty * Cost == Total).
    - [ ] Implement `footing_check` (Sum(Lines) == Subtotal).
    - [ ] Highlight invalid fields in Red.

## Phase 3: Export & Integration (Weeks 3-4)
**Goal:** Get data OUT in a format the POS understands.
- [ ] **Export Engine**:
    - [ ] Create `CSVExportService`.
    - [ ] Define "Liquor Store Standard" CSV format (or configurable).
    - [ ] Add "Download CSV" button to Review page.
- [ ] **Error Tracking**:
    - [ ] Simple dashboard showing "Invoices Processed" vs "Invoices with Errors".

## Phase 4: Pilot Launch (Week 4+)
**Goal:** User testing with one store.
- [ ] **Deployment**:
    - [ ] Deploy to production (Render/Vercel/etc).
    - [ ] Onboard 1 user.
- [ ] **Feedback Loop**:
    - [ ] "Report Issue" button on the UI.
    - [ ] Weekly sync with the store manager.
