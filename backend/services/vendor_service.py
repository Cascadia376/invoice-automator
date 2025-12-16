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
    """Apply learned corrections to invoice data."""
    # Get field mappings
    mappings = get_vendor_field_mappings(db, vendor.id)
    
    # Apply mappings (this would be used during Textract extraction)
    # For now, just return the data as-is
    # TODO: Implement field mapping application during extraction
    
    return invoice_data

def learn_from_correction(
    db: Session,
    invoice_id: str,
    vendor_id: str,
    org_id: str,
    field_name: str,
    original_value: Any,
    corrected_value: Any,
    user_id: Optional[str] = None
):
    """Learn from a user correction."""
    # Determine correction type
    correction_type = "wrong_value"
    if original_value is None or original_value == "" or original_value == 0:
        correction_type = "missing"
    
    # Store correction
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
    
    # Update field mapping confidence if applicable
    # TODO: Implement confidence scoring based on correction frequency
    
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
