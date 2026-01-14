AI Invoice Processor — PRD (Liquor Retail Internal Tool)

Scope
- Internal tool for liquor retail environment. Use case: "User Testing with one store".
- Focus: Speed up invoice entry into POS and accounting systems.
- Key Value: Eliminate manual entry, robust error checking (price changes, new items), and formatted exports.

Problem & Opportunity
- Current State: Manual entry of liquor invoices is time-consuming and prone to errors (wrong costs, missed new items, fat-finger qty).
- Opportunity: Automate extraction from PDF/scans, validate against rules, and produce import-ready files.

Goals & KPIs
- Speed: Reduce invoice processing time by 75% (Target: < 2 mins per invoice).
- Data Integrity: 100% capture of Invoice Number, Date, Total, and Line Item Costs.
- Error Detection: Alert on >95% of "toxic" changes (cost increases > threshold, unknown SKUs).
- Export Accuracy: 0 formatting errors for POS import files.

Users
- Inventory Manager / Receiver: Uploads invoices, reviews exceptions, exports data.
- Accountant: Verifies GL coding (mapped from Category/SKU).

Core Workflow (MVP)
1. Ingest: Upload PDF invoices (Email ingestion planned for v2).
2. Extract: Hybrid parsing (LLM + Vision) to get Headers (Vendor, Invoice #, Date, Terms) and Line Items (SKU, Description, Qty, Case Cost, Unit Cost, Ext Price).
3. Validate:
   - Check Calculated Total (Qty * Cost) matches Line Total.
   - Check Line Totals sum to Invoice Subtotal.
   - *Future*: Compare against master product list for Cost Variance and New Item detection.
4. Review: UI highlights low-confidence fields and Validation Errors. User corrects data.
5. Export: Generate CSV/Excel formatted specifically for:
   - POS System (Inventory Receiving)
   - Accounting System (Bills)

Functional Requirements
- Auth: Secure login (Supabase).
- Ingestion: Drag-and-drop UI for PDFs/Images.
- Parsing:
    - Extract Vendor Product Code (SKU) - Critical for POS matching.
    - Handle multi-page liquor invoices.
    - Normalize "Case Cost" vs "Unit Cost" (Liquor invoices often vary).
- Data Model:
    - Invoices: id, status (uploaded, review, approved), vendor_id, dates, totals.
    - Line Items: invoice_id, raw_desc, sku, qty, pack_size, cost, total.
- Validation Rules (The "Robust Error Checking"):
    - Math checks (Qty * Cost = Total).
    - Invoice Footing (Sum lines = Subtotal).
    - Confidence score threshold alerts.
- Error Tracking / Analytics:
    - Log every "validation error" triggered.
    - Dashboard showing "Invoices with Issues" vs "Clean Invoices".
- Export:
    - Configurable mapping for POS columns (e.g. "Vendor Stock No" -> "SKU", "Case Cost" -> "Cost").

Roadmap (MVP to Pilot)
- [ ] Phase 1: Ingestion & Extraction Accuracy (Get the data out).
- [ ] Phase 2: Review Interface & Basic Math Validation (Make it verifiable).
- [ ] Phase 3: Export Formatter (Make it usable).
- [ ] Phase 4: Pilot Launch (One store user testing).

