"""
Vendor management service for correction learning and auto-application.
"""
import json
import uuid
import re
from typing import Optional, Dict, List, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

import models
import json
import os
from services.textract_service import parse_float

def normalize_vendor_name(name: str) -> str:
    """Normalize vendor name for consistent matching."""
    if not name:
        return ""
    
    # Remove extra whitespace, newlines
    normalized = ' '.join(name.replace('\n', ' ').split())
    
    # Convert to title case
    normalized = normalized.title()
    
    # Remove common suffixes for matching
    suffixes = [' Inc', ' Inc.', ' LLC', ' Ltd', ' Ltd.', ' Corp', ' Corp.', ' Co', ' Co.']
    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)].strip()
            break
    
    return normalized

def find_vendor_by_name(db: Session, name: str, org_id: str) -> Optional[models.Vendor]:
    """Find vendor by name or alias."""
    normalized_name = normalize_vendor_name(name)
    
    # Try exact match first
    vendor = db.query(models.Vendor).filter(
        and_(
            models.Vendor.organization_id == org_id,
            models.Vendor.name == normalized_name
        )
    ).first()
    
    if vendor:
        return vendor
    
    # Try alias match
    vendors = db.query(models.Vendor).filter(
        models.Vendor.organization_id == org_id
    ).all()
    
    for vendor in vendors:
        if vendor.aliases:
            try:
                aliases = json.loads(vendor.aliases)
                if normalized_name in [normalize_vendor_name(a) for a in aliases]:
                    return vendor
            except:
                pass
    
    return None

def get_or_create_vendor(db: Session, vendor_name: str, org_id: str) -> models.Vendor:
    """Get existing vendor or create new one."""
    vendor = find_vendor_by_name(db, vendor_name, org_id)
    
    if vendor:
        print(f"DEBUG: Found existing vendor: {vendor.name} (ID: {vendor.id})")
        return vendor
    
    # Create new vendor
    normalized_name = normalize_vendor_name(vendor_name)
    vendor = models.Vendor(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        name=normalized_name,
        aliases=json.dumps([vendor_name]) if vendor_name != normalized_name else None
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    
    print(f"Created new vendor: {normalized_name} (org: {org_id})")
    return vendor

def get_vendor_field_mappings(db: Session, vendor_id: str) -> Dict[str, str]:
    """Get learned field mappings for a vendor."""
    mappings = db.query(models.VendorFieldMapping).filter(
        models.VendorFieldMapping.vendor_id == vendor_id
    ).all()
    
    # Return dict of field_name -> textract_field
    return {m.field_name: m.textract_field for m in mappings}

def apply_vendor_corrections(db: Session, invoice_data: Dict, vendor: models.Vendor) -> Dict:
    """Apply learned corrections to invoice data using raw results."""
    try:
        # 1. Get field mappings for this vendor
        mappings = get_vendor_field_mappings(db, vendor.id)
        if not mappings:
            return invoice_data
            
        print(f"DEBUG: Applying learned corrections for vendor {vendor.name} ({len(mappings)} mappings found)")
            
        # 2. Extract raw results if present
        raw_results_str = invoice_data.get("raw_extraction_results")
        if not raw_results_str:
            return invoice_data
            
        raw_data = json.loads(raw_results_str)
        
        # 3. Apply mappings
        for field_name, raw_field in mappings.items():
            if raw_field in raw_data:
                learned_val = parse_float(raw_data[raw_field])
                if learned_val != 0:
                    print(f"APPLYING MAPPING: {field_name} = {learned_val} (from raw field '{raw_field}')")
                    invoice_data[field_name] = learned_val
                    
    except Exception as e:
        print(f"ERROR: Failed to apply vendor corrections: {e}")
        import traceback
        traceback.print_exc()
        
    return invoice_data

def learn_from_correction(
    db: Session,
    invoice_id: str,
    vendor_id: str,
    org_id: str,
    field_name: str,
    original_value: Any,
    corrected_value: Any,
    raw_extraction_results: Optional[str] = None,
    user_id: Optional[str] = None
):
    """Learn from a user correction."""
    # Determine correction type
    correction_type = "wrong_value"
    if original_value is None or original_value == "" or original_value == 0:
        correction_type = "missing"
    
    correction = models.VendorCorrection(
        id=str(uuid.uuid4()),
        vendor_id=vendor_id,
        organization_id=org_id,
        invoice_id=invoice_id,
        field_name=field_name,
        original_value=str(original_value) if original_value is not None else None,
        corrected_value=str(corrected_value) if corrected_value is not None else None,
        correction_type=correction_type,
        created_by=user_id
    )
    db.add(correction)
    
    # --- LEARNING LOOP ---
    if raw_extraction_results and corrected_value:
        try:
            raw_data = json.loads(raw_extraction_results)
            corrected_val_str = str(corrected_value).strip()
            
            # Look for a field in the raw scan that matches the corrected value
            for raw_field, raw_val in raw_data.items():
                if str(raw_val).strip() == corrected_val_str:
                    print(f"MATCH FOUND: Corrected {field_name} matches raw scan field '{raw_field}'")
                    
                    # Create or update mapping
                    existing_mapping = db.query(models.VendorFieldMapping).filter(
                        models.VendorFieldMapping.vendor_id == vendor_id,
                        models.VendorFieldMapping.field_name == field_name,
                        models.VendorFieldMapping.textract_field == raw_field
                    ).first()
                    
                    if existing_mapping:
                        existing_mapping.usage_count += 1
                        existing_mapping.last_used = datetime.utcnow()
                    else:
                        new_mapping = models.VendorFieldMapping(
                            id=str(uuid.uuid4()),
                            vendor_id=vendor_id,
                            organization_id=org_id,
                            field_name=field_name,
                            textract_field=raw_field,
                            usage_count=1
                        )
                        db.add(new_mapping)
                    break
        except Exception as e:
            print(f"Learning failed: {e}")
    db.commit()
    print(f"Learned correction for vendor {vendor_id}: {field_name} = {corrected_value}")

def get_vendor_corrections(db: Session, vendor_id: str, limit: int = 50) -> List[models.VendorCorrection]:
    """Get correction history for a vendor."""
    return db.query(models.VendorCorrection).filter(
        models.VendorCorrection.vendor_id == vendor_id
    ).order_by(models.VendorCorrection.created_at.desc()).limit(limit).all()

def get_vendor_stats(db: Session, vendor_id: str) -> Dict:
    """Get statistics for a vendor."""
    # Count invoices
    invoice_count = db.query(func.count(models.Invoice.id)).filter(
        models.Invoice.vendor_name.contains(
            db.query(models.Vendor.name).filter(models.Vendor.id == vendor_id).scalar()
        )
    ).scalar()
    
    # Count corrections
    correction_count = db.query(func.count(models.VendorCorrection.id)).filter(
        models.VendorCorrection.vendor_id == vendor_id
    ).scalar()
    
    # Get last invoice date
    last_invoice = db.query(models.Invoice).filter(
        models.Invoice.vendor_name.contains(
            db.query(models.Vendor.name).filter(models.Vendor.id == vendor_id).scalar()
        )
    ).order_by(models.Invoice.created_at.desc()).first()
    
    return {
        "invoice_count": invoice_count or 0,
        "correction_count": correction_count or 0,
        "last_invoice_date": last_invoice.created_at.isoformat() if last_invoice else None,
        "accuracy_rate": 1.0 - (correction_count / invoice_count) if invoice_count > 0 else 1.0
    }
