from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import shutil
import os
import uuid
import models, schemas, database, auth
from services import parser, storage, vendor_service, validation_service, demo_service
import fitz # PyMuPDF - needed for highlights

from routers import billing

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

app.include_router(billing.router, prefix="/api/billing", tags=["billing"])

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for MVP
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Use absolute path for uploads to avoid CWD issues
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

from fastapi.staticfiles import StaticFiles
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.post("/api/invoices/upload", response_model=schemas.Invoice)
async def upload_invoice(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    print(f"UPLOAD REQUEST: User={ctx.user_id}, Org={ctx.org_id}")
    try:
        file_id = str(uuid.uuid4())
        file_ext = os.path.splitext(file.filename)[1]
        # Use temp file for processing
        temp_file_path = f"/tmp/{file_id}{file_ext}"
        
        print(f"Saving temp file to: {temp_file_path}")
        
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        print(f"File saved. Size: {os.path.getsize(temp_file_path)} bytes")
        
        # Upload to S3 FIRST (so Textract can access it)
        s3_key = f"invoices/{ctx.org_id}/{file_id}{file_ext}"
        s3_bucket = os.getenv("AWS_BUCKET_NAME", "swift-invoice-zen-uploads")
        print(f"Uploading to S3: {s3_key}")
        storage.upload_file(temp_file_path, s3_key)
        
        # Parse PDF (Textract will read from S3)
        print("Starting PDF parsing...")
        extracted_data = parser.extract_invoice_data(temp_file_path, ctx.org_id, s3_key=s3_key, s3_bucket=s3_bucket)
        print("PDF parsing complete.")
        
        # Create or find vendor
        vendor_name = extracted_data.get("vendor_name", "Unknown Vendor")
        vendor = vendor_service.get_or_create_vendor(db, vendor_name, ctx.org_id)
        print(f"Vendor: {vendor.name} (ID: {vendor.id})")
        
        # Create DB Entry
        db_invoice = models.Invoice(
            id=file_id,
            organization_id=ctx.org_id,
            invoice_number=extracted_data.get("invoice_number", "UNKNOWN"),
            vendor_name=extracted_data.get("vendor_name", "Unknown Vendor"),
            date=extracted_data.get("date"),
            total_amount=extracted_data.get("total_amount", 0.0),
            subtotal=extracted_data.get("subtotal", 0.0),
            shipping_amount=extracted_data.get("shipping_amount", 0.0),
            discount_amount=extracted_data.get("discount_amount", 0.0),
            tax_amount=extracted_data.get("tax_amount", 0.0),
            deposit_amount=extracted_data.get("deposit_amount", 0.0),
            currency=extracted_data.get("currency", "USD"),
            status="needs_review",
            file_url=s3_key # Store S3 key
        )
        db.add(db_invoice)
        db.commit()
        db.refresh(db_invoice)

        # Save Line Items
        line_items_data = extracted_data.get("line_items", [])
        for item in line_items_data:
            # Check if we have a learned category for this SKU
            sku = item.get("sku")
            category_gl_code = item.get("category_gl_code")
            
            if sku and not category_gl_code:
                try:
                    # Look up learned category mapping
                    # Use text() for safety in case table doesn't exist yet to avoid compilation errors
                    # But ORM should be fine if we catch the OperationalError
                    mapping = db.query(models.SKUCategoryMapping).filter(
                        models.SKUCategoryMapping.sku == sku,
                        models.SKUCategoryMapping.organization_id == ctx.org_id
                    ).order_by(models.SKUCategoryMapping.usage_count.desc()).first()
                    
                    if mapping:
                        category_gl_code = mapping.category_gl_code
                except Exception as e:
                    print(f"WARNING: Could not look up SKU mapping (table might be missing): {e}")
            
            db_item = models.LineItem(
                id=str(uuid.uuid4()), 
                invoice_id=file_id, 
                sku=sku,
                description=item.get("description", "Item"),
                units_per_case=float(item.get("units_per_case", 1.0)),
                cases=float(item.get("cases", 0.0)),
                quantity=float(item.get("quantity", 1.0)),
                unit_cost=float(item.get("unit_cost", 0.0)),
                amount=float(item.get("amount", 0.0)),
                category_gl_code=category_gl_code,
                confidence_score=float(item.get("confidence_score", 1.0))
            )
            db.add(db_item)
        
        db.commit()
        db.refresh(db_invoice)
        
        # Generate presigned URL for immediate display
        if db_invoice.file_url and not db_invoice.file_url.startswith("http"):
             db_invoice.file_url = storage.get_presigned_url(db_invoice.file_url)
             
        return db_invoice
    except Exception as e:
        print(f"ERROR processing invoice: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/invoices", response_model=List[schemas.Invoice])
@app.get("/api/invoices", response_model=List[schemas.Invoice])
def read_invoices(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    print(f"FETCH REQUEST: User={ctx.user_id}, Org={ctx.org_id}")
    invoices = db.query(models.Invoice).filter(models.Invoice.organization_id == ctx.org_id).offset(skip).limit(limit).all()
    
    # Generate presigned URLs
    for inv in invoices:
        if inv.file_url and not inv.file_url.startswith("http"):
             # Assume it's an S3 key
             inv.file_url = storage.get_presigned_url(inv.file_url)
             
    return invoices

@app.get("/api/invoices/{invoice_id}", response_model=schemas.Invoice)
@app.get("/api/invoices/{invoice_id}", response_model=schemas.Invoice)
def read_invoice(
    invoice_id: str, 
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    invoice = db.query(models.Invoice).filter(
        models.Invoice.id == invoice_id,
        models.Invoice.organization_id == ctx.org_id
    ).first()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    if invoice.file_url and not invoice.file_url.startswith("http"):
         invoice.file_url = storage.get_presigned_url(invoice.file_url)
         
    return invoice

@app.put("/api/invoices/{invoice_id}", response_model=schemas.Invoice)
@app.put("/api/invoices/{invoice_id}", response_model=schemas.Invoice)
def update_invoice(
    invoice_id: str, 
    invoice: schemas.InvoiceUpdate, 
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    db_invoice = db.query(models.Invoice).filter(
        models.Invoice.id == invoice_id,
        models.Invoice.organization_id == ctx.org_id
    ).first()
    if db_invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    update_data = invoice.dict(exclude_unset=True)
    
    # Handle line items separately if needed, for now simple update
    if "line_items" in update_data:
        # Clear existing
        db.query(models.LineItem).filter(models.LineItem.invoice_id == invoice_id).delete()
        # Add new
        for item in update_data["line_items"]:
            # Learn SKU → Category mapping if both are present
            sku = item.get("sku")
            category_gl_code = item.get("category_gl_code")
            
            if sku and category_gl_code:
                try:
                    # Check if mapping exists
                    mapping = db.query(models.SKUCategoryMapping).filter(
                        models.SKUCategoryMapping.sku == sku,
                        models.SKUCategoryMapping.category_gl_code == category_gl_code,
                        models.SKUCategoryMapping.organization_id == ctx.org_id
                    ).first()
                    
                    if mapping:
                        # Update usage count and last_used
                        mapping.usage_count += 1
                        mapping.last_used = datetime.utcnow()
                    else:
                        # Create new mapping
                        new_mapping = models.SKUCategoryMapping(
                            id=str(uuid.uuid4()),
                            organization_id=ctx.org_id,
                            sku=sku,
                            category_gl_code=category_gl_code,
                            usage_count=1,
                            last_used=datetime.utcnow()
                        )
                        db.add(new_mapping)
                except Exception as e:
                    print(f"WARNING: Could not learn SKU mapping (table might be missing): {e}")
            
            db_item = models.LineItem(id=str(uuid.uuid4()), invoice_id=invoice_id, **item)
            db.add(db_item)
        del update_data["line_items"]

    for key, value in update_data.items():
        setattr(db_invoice, key, value)

    db.commit()
    db.refresh(db_invoice)
    
    # Generate presigned URL for display
    if db_invoice.file_url and not db_invoice.file_url.startswith("http"):
         db_invoice.file_url = storage.get_presigned_url(db_invoice.file_url)
         
    return db_invoice



# QuickBooks Integration
from services import qbo
from services import demo_service

@app.get("/api/auth/qbo/connect")
def qbo_connect():
    auth_url = qbo.get_auth_url()
    return {"auth_url": auth_url}

@app.post("/api/seed/demo")
def seed_demo_invoice(
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """
    Generate and inject a Stark Industries demo invoice.
    """
    invoice = demo_service.seed_demo_data(db, ctx.org_id)
    return {"message": "Demo invoice created", "invoice_id": invoice.id}

@app.get("/api/auth/qbo/callback")
@app.get("/api/auth/qbo/callback")
def qbo_callback(
    code: str, 
    realmId: str, 
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    try:
        qbo.handle_callback(code, realmId, db, ctx.org_id)
        # In a real app, we'd redirect to the frontend with a success param
        # For now, we'll return a simple HTML page that closes itself or redirects
        return "Connected to QuickBooks! You can close this window."
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/auth/qbo/status")
@app.get("/api/auth/qbo/status")
def qbo_status(
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    credentials = db.query(models.QBOCredentials).filter(models.QBOCredentials.organization_id == ctx.org_id).first()
    if credentials:
        return {"connected": True, "realm_id": credentials.realm_id, "updated_at": credentials.updated_at}
    return {"connected": False}

@app.post("/api/auth/qbo/disconnect")
@app.post("/api/auth/qbo/disconnect")
def qbo_disconnect(
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    db.query(models.QBOCredentials).filter(models.QBOCredentials.organization_id == ctx.org_id).delete()
    db.commit()
    return {"status": "success", "message": "Disconnected from QuickBooks"}

@app.post("/api/invoices/{invoice_id}/push")
@app.post("/api/invoices/{invoice_id}/push")
def push_to_qbo(
    invoice_id: str, 
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    db_invoice = db.query(models.Invoice).filter(
        models.Invoice.id == invoice_id,
        models.Invoice.organization_id == ctx.org_id
    ).first()
    if db_invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    try:
        # Create Bill in QBO
        bill = qbo.create_bill(invoice_id, db, ctx.org_id)
        
        # Update status
        db_invoice.status = "pushed"
        db.commit()
        
        return {"status": "success", "message": f"Pushed to QBO. Bill ID: {bill.Id}"}
    except Exception as e:
        print(f"Error pushing to QBO: {e}")
        raise HTTPException(status_code=500, detail=str(e))

import csv
import io
from fastapi.responses import StreamingResponse

@app.get("/api/invoices/{invoice_id}/export/csv")
def export_invoice_csv(
    invoice_id: str, 
    columns: str = None, 
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    invoice = db.query(models.Invoice).filter(
        models.Invoice.id == invoice_id,
        models.Invoice.organization_id == ctx.org_id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Define all available columns and their data getters
    all_columns_map = {
        "Invoice Number": lambda i, item: i.invoice_number,
        "Date": lambda i, item: i.date,
        "Vendor": lambda i, item: i.vendor_name,
        "SKU": lambda i, item: item.sku,
        "Description": lambda i, item: item.description,
        "Units/Case": lambda i, item: item.units_per_case,
        "Cases": lambda i, item: item.cases,
        "Quantity": lambda i, item: item.quantity,
        "Unit Cost": lambda i, item: item.unit_cost,
        "Total": lambda i, item: item.amount,
        "Category/GL Code": lambda i, item: item.category_gl_code
    }
    
    # Default behavior: Use all columns with default names
    header_map = {k: k for k in all_columns_map.keys()}
    selected_keys = list(all_columns_map.keys())

    if columns:
        try:
            # Try parsing as JSON mapping: {"Invoice Number": "Doc #", "SKU": "Item Code"}
            import json
            custom_map = json.loads(columns)
            if isinstance(custom_map, dict):
                # Filter to only valid internal keys
                valid_map = {k: v for k, v in custom_map.items() if k in all_columns_map}
                if valid_map:
                    selected_keys = list(valid_map.keys())
                    header_map = valid_map
        except json.JSONDecodeError:
            # Fallback: Treat as comma-separated list of keys (legacy)
            requested_keys = columns.split(",")
            valid_keys = [k for k in requested_keys if k in all_columns_map]
            if valid_keys:
                selected_keys = valid_keys
                header_map = {k: k for k in selected_keys}
    
    # Header Row (use custom values from map)
    writer.writerow([header_map[k] for k in selected_keys])
    
    # Data Rows
    for item in invoice.line_items:
        row = [all_columns_map[k](invoice, item) for k in selected_keys]
        writer.writerow(row)
        
    output.seek(0)
    
    headers = {
        'Content-Disposition': f'attachment; filename="invoice_{invoice.invoice_number or invoice_id}.csv"'
    }
    
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers=headers)

@app.get("/api/invoices/{invoice_id}/validate")
def validate_invoice_endpoint(
    invoice_id: str,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    invoice = db.query(models.Invoice).filter(
        models.Invoice.id == invoice_id,
        models.Invoice.organization_id == ctx.org_id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    return validation_service.validate_invoice(db, invoice)

@app.get("/api/invoices/{invoice_id}/highlights")
def get_invoice_highlights(
    invoice_id: str,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    import fitz # PyMuPDF

    invoice = db.query(models.Invoice).filter(
        models.Invoice.id == invoice_id,
        models.Invoice.organization_id == ctx.org_id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Download PDF
    s3_key = invoice.file_url
    temp_file_path = f"/tmp/highlights_{invoice_id}.pdf"
    
    try:
        if s3_key and not s3_key.startswith("http") and not os.path.exists(s3_key):
             storage.download_file(s3_key, temp_file_path)
        elif s3_key and os.path.exists(s3_key):
             # Local file (dev/test)
             shutil.copy(s3_key, temp_file_path)
        elif invoice.file_url and invoice.file_url.startswith("/"):
             # Legacy local path
             local_path = os.path.join(BASE_DIR, invoice.file_url.lstrip("/"))
             if os.path.exists(local_path):
                shutil.copy(local_path, temp_file_path)
             else:
                return {} # File not found locally
        else:
             return {} # No file to process
             
        # Search for highlights
        highlights = {}
        doc = fitz.open(temp_file_path)
        
        def add_highlight(field_name, text_value):
            if not text_value or str(text_value).lower() == "unknown":
                return
            
            text_str = str(text_value)
            # Remove currency symbols for search if needed, but keeping exact for now
            # Maybe strip common currency symbols
            clean_text = text_str.replace("$", "").replace(",", "").strip()
            
            found = []
            for page_num, page in enumerate(doc):
                # Search for exact string
                rects = page.search_for(text_str)
                if not rects and clean_text != text_str:
                    rects = page.search_for(clean_text)
                
                for r in rects:
                    # r is [x0, y0, x1, y1]
                    # Convert to % to be resolution independent on frontend?
                    # Or return points and let frontend handle scaling if it knows PDF size.
                    # Returning normalized coordinates (0-1) is safest for responsiveness.
                    
                    width = page.rect.width
                    height = page.rect.height
                    
                    found.append({
                        "page": page_num + 1,
                        "rect": [r.x0, r.y0, r.x1 - r.x0, r.y1 - r.y0], # x, y, w, h
                        "norm": [r.x0/width, r.y0/height, (r.x1-r.x0)/width, (r.y1-r.y0)/height]
                    })
            
            if found:
                highlights[field_name] = found

        # main fields
        add_highlight("invoice_number", invoice.invoice_number)
        add_highlight("total_amount", f"{invoice.total_amount:.2f}")
        add_highlight("total_amount", f"{invoice.total_amount:,.2f}") # Try formatted
        add_highlight("date", invoice.date)
        add_highlight("vendor_name", invoice.vendor_name)
        
        # Line items
        for idx, item in enumerate(invoice.line_items):
            # item ID is the key? Or "line_items[0].amount"?
            # Let's use a flat key convention if possible or nested
            prefix = f"line_items[{idx}]"
            add_highlight(f"{prefix}.amount", f"{item.amount:.2f}")
            add_highlight(f"{prefix}.unit_cost", f"{item.unit_cost:.2f}")
            add_highlight(f"{prefix}.quantity", str(int(item.quantity) if item.quantity.is_integer() else item.quantity))
            add_highlight(f"{prefix}.description", item.description)

        doc.close()
        # Clean up
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
        return highlights

    except Exception as e:
        print(f"Error generating highlights: {e}")
        return {}

@app.get("/api/debug/templates")
@app.get("/api/debug/templates")
def list_templates(
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """Debug endpoint to list all learned templates"""
    templates = db.query(models.Template).filter(models.Template.organization_id == ctx.org_id).all()
    
    return {
        "count": len(templates),
        "templates": [
            {
                "id": t.id,
                "vendor_name": t.vendor_name,
                "created_at": t.created_at,
                "content_preview": t.content[:50] + "..." if t.content else ""
            }
            for t in templates
        ],
        "source": "database"
    }

@app.get("/api/debug/db-info")
def get_db_info():
    """Debug endpoint to check which database is being used"""
    db_url = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")
    is_sqlite = "sqlite" in db_url
    return {
        "database_type": "sqlite" if is_sqlite else "postgres",
        "database_url_masked": db_url.split("@")[-1] if "@" in db_url else "sqlite_local"
    }

from fastapi import BackgroundTasks

@app.post("/api/invoices/{invoice_id}/feedback")
@app.post("/api/invoices/{invoice_id}/feedback")
def submit_feedback(
    invoice_id: str, 
    feedback_data: schemas.InvoiceUpdate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    db_invoice = db.query(models.Invoice).filter(
        models.Invoice.id == invoice_id,
        models.Invoice.organization_id == ctx.org_id
    ).first()
    if db_invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Handle S3 file for feedback
    # file_url is now S3 key
    s3_key = db_invoice.file_url
    
    # 1. Trigger legacy template refinement in background
    if s3_key and not s3_key.startswith("http"):
        temp_file_path = f"/tmp/feedback_{invoice_id}.pdf"
        storage.download_file(s3_key, temp_file_path)
        
        background_tasks.add_task(
            parser.refine_template_with_feedback, 
            temp_file_path, 
            feedback_data.dict(exclude_unset=True),
            ctx.org_id
        )
    else:
        # Fallback for old local files (if any exist)
        relative_path = db_invoice.file_url.lstrip("/")
        file_path = os.path.join(os.path.dirname(__file__), relative_path)
        background_tasks.add_task(
            parser.refine_template_with_feedback, 
            file_path, 
            feedback_data.dict(exclude_unset=True),
            ctx.org_id
        )

    # 2. Trigger new vendor correction learning
    # Detect changes and record corrections
    if db_invoice.vendor_id: # Only if linked to a vendor
        changes = []
        feedback_dict = feedback_data.dict(exclude_unset=True)
        
        # Check standard fields
        fields_to_check = ['total_amount', 'subtotal', 'tax_amount', 'deposit_amount', 'shipping_amount', 'date', 'invoice_number']
        for field in fields_to_check:
            if field in feedback_dict:
                new_val = str(feedback_dict[field])
                old_val = str(getattr(db_invoice, field)) if getattr(db_invoice, field) is not None else ""
                
                # Simple string comparison for now. Ideally handle float tolerance.
                if new_val != old_val:
                    vendor_service.learn_from_correction(
                        db,
                        invoice_id,
                        db_invoice.vendor_id,
                        ctx.org_id,
                        field,
                        old_val,
                        new_val,
                        user_id=ctx.user_id
                    )

    
    return {"status": "success", "message": "Feedback received, refining template in background"}

@app.delete("/api/invoices/{invoice_id}")
@app.delete("/api/invoices/{invoice_id}")
def delete_invoice(
    invoice_id: str, 
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    db_invoice = db.query(models.Invoice).filter(
        models.Invoice.id == invoice_id,
        models.Invoice.organization_id == ctx.org_id
    ).first()
    if db_invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Optional: Delete file from disk
    # if db_invoice.file_url:
    #     ...

    db.delete(db_invoice)
    db.commit()
    return {"status": "success", "message": "Invoice deleted"}

# GL Category Management Endpoints
@app.get("/api/gl-categories", response_model=List[schemas.GLCategory])
@app.get("/api/gl-categories", response_model=List[schemas.GLCategory])
def get_gl_categories(
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    categories = db.query(models.GLCategory).filter(models.GLCategory.organization_id == ctx.org_id).all()
    return categories

@app.post("/api/gl-categories", response_model=schemas.GLCategory)
@app.post("/api/gl-categories", response_model=schemas.GLCategory)
def create_gl_category(
    category: schemas.GLCategoryCreate, 
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    db_category = models.GLCategory(
        id=str(uuid.uuid4()),
        organization_id=ctx.org_id,
        code=category.code,
        name=category.name,
        full_name=category.full_name
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

@app.put("/api/gl-categories/{category_id}", response_model=schemas.GLCategory)
@app.put("/api/gl-categories/{category_id}", response_model=schemas.GLCategory)
def update_gl_category(
    category_id: str, 
    category: schemas.GLCategoryCreate, 
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    db_category = db.query(models.GLCategory).filter(
        models.GLCategory.id == category_id,
        models.GLCategory.organization_id == ctx.org_id
    ).first()
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    
    db_category.code = category.code
    db_category.name = category.name
    db_category.full_name = category.full_name
    db.commit()
    db.refresh(db_category)
    return db_category

@app.delete("/api/gl-categories/{category_id}")
@app.delete("/api/gl-categories/{category_id}")
def delete_gl_category(
    category_id: str, 
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    db_category = db.query(models.GLCategory).filter(
        models.GLCategory.id == category_id,
        models.GLCategory.organization_id == ctx.org_id
    ).first()
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    
    db.delete(db_category)
    db.commit()
    return {"status": "success", "message": "Category deleted"}

@app.get("/api/sku-mappings/{sku}")
@app.get("/api/sku-mappings/{sku}")
def get_sku_category(
    sku: str, 
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    mapping = db.query(models.SKUCategoryMapping).filter(
        models.SKUCategoryMapping.sku == sku,
        models.SKUCategoryMapping.organization_id == ctx.org_id
    ).order_by(models.SKUCategoryMapping.usage_count.desc()).first()
    
    if mapping:
        return {"sku": sku, "category_gl_code": mapping.category_gl_code, "usage_count": mapping.usage_count}
    return {"sku": sku, "category_gl_code": None}

# ===== VENDOR MANAGEMENT ROUTES =====

@app.get("/api/vendors", response_model=List[schemas.VendorWithStats])
def list_vendors(
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """List all vendors for the organization with stats."""
    import json
    
    vendors = db.query(models.Vendor).filter(
        models.Vendor.organization_id == ctx.org_id
    ).all()
    
    # Add stats to each vendor
    vendor_list = []
    for vendor in vendors:
        stats = vendor_service.get_vendor_stats(db, vendor.id)
        vendor_dict = {
            "id": vendor.id,
            "organization_id": vendor.organization_id,
            "name": vendor.name,
            "aliases": json.loads(vendor.aliases) if vendor.aliases else None,
            "default_gl_category": vendor.default_gl_category,
            "notes": vendor.notes,
            "created_at": vendor.created_at,
            "updated_at": vendor.updated_at,
            **stats
        }
        vendor_list.append(vendor_dict)
    
    return vendor_list

@app.get("/api/vendors/{vendor_id}", response_model=schemas.VendorWithStats)
def get_vendor(
    vendor_id: str,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """Get vendor details with stats."""
    import json
    
    vendor = db.query(models.Vendor).filter(
        models.Vendor.id == vendor_id,
        models.Vendor.organization_id == ctx.org_id
    ).first()
    
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    stats = vendor_service.get_vendor_stats(db, vendor.id)
    
    return {
        "id": vendor.id,
        "organization_id": vendor.organization_id,
        "name": vendor.name,
        "aliases": json.loads(vendor.aliases) if vendor.aliases else None,
        "default_gl_category": vendor.default_gl_category,
        "notes": vendor.notes,
        "created_at": vendor.created_at,
        "updated_at": vendor.updated_at,
        **stats
    }

@app.post("/api/vendors", response_model=schemas.Vendor)
def create_vendor(
    vendor: schemas.VendorCreate,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """Create a new vendor manually."""
    import json
    
    db_vendor = models.Vendor(
        id=str(uuid.uuid4()),
        organization_id=ctx.org_id,
        name=vendor.name,
        aliases=json.dumps(vendor.aliases) if vendor.aliases else None,
        default_gl_category=vendor.default_gl_category,
        notes=vendor.notes
    )
    db.add(db_vendor)
    db.commit()
    db.refresh(db_vendor)
    
    return db_vendor

@app.put("/api/vendors/{vendor_id}", response_model=schemas.Vendor)
def update_vendor(
    vendor_id: str,
    vendor_update: schemas.VendorUpdate,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """Update vendor details."""
    import json
    
    db_vendor = db.query(models.Vendor).filter(
        models.Vendor.id == vendor_id,
        models.Vendor.organization_id == ctx.org_id
    ).first()
    
    if not db_vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Update fields
    if vendor_update.name is not None:
        db_vendor.name = vendor_update.name
    if vendor_update.aliases is not None:
        db_vendor.aliases = json.dumps(vendor_update.aliases)
    if vendor_update.default_gl_category is not None:
        db_vendor.default_gl_category = vendor_update.default_gl_category
    if vendor_update.notes is not None:
        db_vendor.notes = vendor_update.notes
    
    db_vendor.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_vendor)
    
    return db_vendor

@app.delete("/api/vendors/{vendor_id}")
def delete_vendor(
    vendor_id: str,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """Delete a vendor."""
    db_vendor = db.query(models.Vendor).filter(
        models.Vendor.id == vendor_id,
        models.Vendor.organization_id == ctx.org_id
    ).first()
    
    if not db_vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    db.delete(db_vendor)
    db.commit()
    
    return {"message": "Vendor deleted successfully"}

@app.get("/api/vendors/{vendor_id}/corrections")
def get_vendor_corrections(
    vendor_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """Get correction history for a vendor."""
    vendor = db.query(models.Vendor).filter(
        models.Vendor.id == vendor_id,
        models.Vendor.organization_id == ctx.org_id
    ).first()
    
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    corrections = vendor_service.get_vendor_corrections(db, vendor_id, limit)
    
    return [{
        "id": c.id,
        "field_name": c.field_name,
        "original_value": c.original_value,
        "corrected_value": c.corrected_value,
        "correction_type": c.correction_type,
        "rule": c.rule,
        "created_at": c.created_at.isoformat(),
        "created_by": c.created_by
    } for c in corrections]
