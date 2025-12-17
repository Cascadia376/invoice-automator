import fitz
import os
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
import models
from services import storage, vendor_service

def generate_demo_pdf(output_path: str):
    """
    Generates a simple 'Stark Industries' PDF invoice using PyMuPDF.
    """
    doc = fitz.open()
    page = doc.new_page()
    
    # Fonts
    # font = fitz.Font("helv") # Default helvetica
    
    # Header
    page.insert_text((50, 50), "STARK INDUSTRIES", fontsize=24, color=(0, 0, 0))
    page.insert_text((50, 80), "10880 Malibu Point, Malibu, CA 90265", fontsize=10)
    
    page.insert_text((400, 50), "INVOICE", fontsize=24, color=(0, 0, 0))
    page.insert_text((400, 80), "Invoice #: SI-2025-001", fontsize=12)
    page.insert_text((400, 100), f"Date: {datetime.now().strftime('%Y-%m-%d')}", fontsize=12)
    
    # Bill To
    page.insert_text((50, 150), "BILL TO:", fontsize=12, fontname="helv-bo")
    page.insert_text((50, 170), "Future Innovation Corp", fontsize=12)
    
    # Line Items Header
    y = 250
    page.draw_rect(fitz.Rect(50, y-20, 550, y), color=(0.9, 0.9, 0.9), fill=(0.9, 0.9, 0.9))
    page.insert_text((60, y-5), "Description", fontsize=10, fontname="helv-bo")
    page.insert_text((350, y-5), "Qty", fontsize=10, fontname="helv-bo")
    page.insert_text((400, y-5), "Unit Price", fontsize=10, fontname="helv-bo")
    page.insert_text((480, y-5), "Amount", fontsize=10, fontname="helv-bo")
    
    # Items
    items = [
        ("Arc Reactor Model IV (Palladium Core)", 1, 50000.00),
        ("Jarvis AI Enterprise License (Annual)", 1, 12000.00),
        ("Mark VI Armor Plating (Titanium-Gold)", 4, 2500.00)
    ]
    
    y += 20
    total = 0
    for desc, qty, price in items:
        amount = qty * price
        total += amount
        page.insert_text((60, y), desc, fontsize=10)
        page.insert_text((350, y), str(qty), fontsize=10)
        page.insert_text((400, y), f"${price:,.2f}", fontsize=10)
        page.insert_text((480, y), f"${amount:,.2f}", fontsize=10)
        y += 20
    
    # Totals
    y += 20
    page.draw_line(fitz.Point(350, y), fitz.Point(550, y))
    y += 20
    page.insert_text((400, y), "Subtotal:", fontsize=10)
    page.insert_text((480, y), f"${total:,.2f}", fontsize=10)
    y += 20
    page.insert_text((400, y), "Tax (0%):", fontsize=10)
    page.insert_text((480, y), "$0.00", fontsize=10)
    y += 20
    page.insert_text((400, y), "TOTAL:", fontsize=12, fontname="helv-bo")
    page.insert_text((480, y), f"${total:,.2f}", fontsize=12, fontname="helv-bo", color=(0, 0, 1))
    
    # Footer
    page.insert_text((50, 750), "Payment due within 30 days. Thank you for your business.", fontsize=9, fontname="helv-ob")

    doc.save(output_path)
    doc.close()

def seed_demo_data(db: Session, org_id: str) -> models.Invoice:
    """
    Creates a demo invoice for the user.
    """
    # 1. Vendor
    vendor_name = "Stark Industries"
    vendor = vendor_service.get_or_create_vendor(db, vendor_name, org_id)
    
    # 2. PDF Generation
    file_id = str(uuid.uuid4())
    filename = f"demo_stark_{file_id}.pdf"
    
    # Use standard uploads dir logic (duplicated from main.py for isolation, ideally shared config)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    temp_path = os.path.join(UPLOAD_DIR, filename) # Saving directly to uploads for simplicity in demo
    
    generate_demo_pdf(temp_path)
    
    # 3. "Upload" logic (S3 + URL)
    # For demo, if we are local, we might just point to static file?
    # But existing logic uses s3_key in file_url usually unless it's a URL.
    # We will simulate S3 upload if configured, else use local path logic
    
    # Actually, simpler: Use the upload_file service if it handles local fallback
    # But for now, let's assume we just want it to work.
    # main.py serves /uploads. 
    # file_url logic in main.py is: if http -> fetch, else -> open(path)
    # The frontend expects a URL it can display.
    # The backend PDFViewer expects a URL (PDFViewer.tsx uses whatever is passed).
    # Wait, PDFViewer gets `pdfUrl` from `getPdfUrl` in `InvoiceReview`.
    # `getPdfUrl` constructs `${API_BASE}/api/invoices/${id}/pdf`.
    # That endpoint (`/api/invoices/{id}/pdf`) needs to serve the file.
    # Let's check `routers/billing.py` or wherever that is. 
    # Actually, in `main.py` there is likely a serve endpoint.
    
    # Assuming standard flow:
    # We set file_url to the relative path or s3 key.
    # Let's assume we want to support the "local" flow which main.py seems to support via StaticFiles("/uploads")
    # if `file_url` stored in DB is accessible.
    
    # Let's store the relative path in `file_url` assuming `main.py` logic handles it.
    # Looking at `main.py` viewed earlier:
    # It has `app.mount("/uploads", ...)`
    # And `get_invoice_highlights` logic: `if invoice.file_url.startswith("http"): ... else: path = invoice.file_url.lstrip("/")`
    
    # So if we store "uploads/filename.pdf", it should work for backend processing.
    # For Frontend, we need a URL. `InvoiceReview` usually calls an API to get the PDF or uses a static URL?
    # I'll check `InvoiceReview` again later if needed.
    
    # For now: Store relative path `uploads/filename.pdf`
    # Ensure file exists there.
    rel_path = f"uploads/{filename}"
    
    # Create Invoice Record
    invoice_id = str(uuid.uuid4())
    inv = models.Invoice(
        id=invoice_id,
        organization_id=org_id,
        invoice_number="SI-2025-001",
        vendor_name="Stark Industries",
        date=datetime.now().strftime('%Y-%m-%d'),
        total_amount=72000.00,
        subtotal=72000.00,
        shipping_amount=0,
        tax_amount=0,
        discount_amount=0,
        currency="USD",
        status="needs_review", # User needs to review it
        file_url=rel_path
    )
    
    # Line Items
    inv.line_items = [
        models.LineItem(id=str(uuid.uuid4()), description="Arc Reactor Model IV (Palladium Core)", quantity=1, unit_cost=50000.00, amount=50000.00, confidence_score=0.99),
        models.LineItem(id=str(uuid.uuid4()), description="Jarvis AI Enterprise License (Annual)", quantity=1, unit_cost=12000.00, amount=12000.00, confidence_score=0.98),
        models.LineItem(id=str(uuid.uuid4()), description="Mark VI Armor Plating (Titanium-Gold)", quantity=4, unit_cost=2500.00, amount=10000.00, confidence_score=0.95),
    ]
    
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv
