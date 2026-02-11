import os
import uuid
import json
import shutil
from sqlalchemy.orm import Session
from fastapi import HTTPException
import models
from services import parser, vendor_service, product_service, storage
from services import store_routing_service
from services.textract_service import parse_float

def process_invoice(
    db: Session,
    file_path: str,
    org_id: str,
    user_id: str,
    original_filename: str = "invoice.pdf"
):
    """
    Core logic to ingest an invoice file:
    1. Upload to S3
    2. Extract data (Textract/Parser)
    3. Resolve Vendor
    4. Create DB Records
    """
    
    file_id = str(uuid.uuid4())
    file_ext = os.path.splitext(original_filename)[1]
    
    # 1. Upload to S3
    # Note: The router was saving to a temp file first. 
    # Here we assume file_path is already a local temp file we can read.
    
    s3_key = f"invoices/{org_id}/{file_id}{file_ext}"
    s3_bucket = os.getenv("AWS_BUCKET_NAME", "swift-invoice-zen-uploads")
    print(f"Ingestion Service: Uploading to S3: {s3_key}")
    
    # We upload the file at file_path
    storage.upload_file(file_path, s3_key)
    
    # 2. Parse PDF
    print("Ingestion Service: Starting PDF parsing...")
    extracted_data = parser.extract_invoice_data(file_path, org_id, s3_key=s3_key, s3_bucket=s3_bucket)
    print("Ingestion Service: PDF parsing complete.")
    
    # 3. Create or find vendor
    vendor_name = extracted_data.get("vendor_name", "Unknown Vendor")
    vendor = vendor_service.get_or_create_vendor(db, vendor_name, org_id)
    print(f"Ingestion Service: Vendor: {vendor.name} (ID: {vendor.id})")
    
    # 4. Apply learned corrections
    extracted_data = vendor_service.apply_vendor_corrections(db, extracted_data, vendor)
    
    # 5. Product Intelligence & Validation
    # (Note: Logic copied from router)
    for item in extracted_data.get("line_items", []):
        validation = product_service.validate_item_against_master(db, org_id, item)
        if validation["status"] == "success" and validation["flags"]:
            # We aren't storing flags on the line item model yet in this codebase version,
            # but we use the master category if found.
            if validation.get("master_category"):
                item["category_gl_code"] = validation["master_category"]

    # 6. Store Routing - resolve destination store from extracted license number
    resolved_store = None
    destination_license = None
    destination_store_name = None
    
    try:
        # Build the fields dict for store routing to search
        raw_fields = {}
        raw_str = extracted_data.get('raw_extraction_results', '{}')
        if raw_str:
            try:
                raw_fields = json.loads(raw_str)
            except:
                pass
        # Also add receiver fields directly
        if extracted_data.get('receiver_name'):
            raw_fields['receiver_name'] = extracted_data['receiver_name']
        if extracted_data.get('receiver_address'):
            raw_fields['receiver_address'] = extracted_data['receiver_address']
        if extracted_data.get('vendor_address'):
            raw_fields['vendor_address'] = extracted_data['vendor_address']
            
        resolved_store, destination_license = store_routing_service.resolve_store(
            db, raw_fields, org_id
        )
        if resolved_store:
            destination_store_name = resolved_store.name
            print(f"Ingestion Service: Store routed -> {resolved_store.name} (License: {destination_license})")
        else:
            print(f"Ingestion Service: No store resolved (License found: {destination_license})")
    except Exception as e:
        print(f"WARNING: Store routing failed: {e}")

    # 7. Create DB Entry (Invoice)
    db_invoice = models.Invoice(
        id=file_id,
        organization_id=org_id,
        invoice_number=extracted_data.get("invoice_number", "UNKNOWN"),
        vendor_name=extracted_data.get("vendor_name", "Unknown Vendor"),
        vendor_address=extracted_data.get("vendor_address"),
        date=extracted_data.get("date"),
        total_amount=extracted_data.get("total_amount", 0.0),
        subtotal=extracted_data.get("subtotal", 0.0),
        shipping_amount=extracted_data.get("shipping_amount", 0.0),
        discount_amount=extracted_data.get("discount_amount", 0.0),
        tax_amount=extracted_data.get("tax_amount", 0.0),
        deposit_amount=extracted_data.get("deposit_amount", 0.0),
        currency=extracted_data.get("currency", "CAD"),
        po_number=extracted_data.get("po_number"),
        status="needs_review",
        file_url=s3_key,
        raw_extraction_results=extracted_data.get("raw_extraction_results"),
        vendor_id=vendor.id,
        store_id=resolved_store.store_id if resolved_store else None,
        destination_license=destination_license,
        destination_store_name=destination_store_name
    )

    # 7. Save Line Items
    line_items_data = extracted_data.get("line_items", [])
    print(f"Ingestion Service: Saving {len(line_items_data)} line items for invoice {file_id}")
    
    for item in line_items_data:
        sku = item.get("sku")
        category_gl_code = item.get("category_gl_code")
        
        # Dictionary-based SKU mapping lookup
        if sku and not category_gl_code:
            try:
                mapping = db.query(models.SKUCategoryMapping).filter(
                    models.SKUCategoryMapping.sku == sku,
                    models.SKUCategoryMapping.organization_id == org_id
                ).order_by(models.SKUCategoryMapping.usage_count.desc()).first()
                if mapping:
                    category_gl_code = mapping.category_gl_code
            except Exception as e:
                print(f"WARNING: SKU mapping lookup error: {e}")
        
        db_item = models.LineItem(
            id=str(uuid.uuid4()), 
            invoice_id=file_id, 
            sku=sku,
            description=item.get("description", "Item"),
            units_per_case=parse_float(item.get("units_per_case", 1.0)),
            cases=parse_float(item.get("cases", 0.0)),
            quantity=parse_float(item.get("quantity", 1.0)),
            case_cost=parse_float(item.get("case_cost")) if item.get("case_cost") is not None else None,
            unit_cost=parse_float(item.get("unit_cost", 0.0)),
            amount=parse_float(item.get("amount", 0.0)),
            category_gl_code=category_gl_code,
            confidence_score=parse_float(item.get("confidence_score", 1.0))
        )
        db_invoice.line_items.append(db_item)
    
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)
    
    print(f"SUCCESS: Invoice {file_id} saved with {len(db_invoice.line_items)} line items")

    if db_invoice.file_url and not db_invoice.file_url.startswith("http"):
            db_invoice.file_url = storage.get_presigned_url(db_invoice.file_url)
            
    return db_invoice
