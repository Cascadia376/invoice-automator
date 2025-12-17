from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid
import json
from datetime import datetime

import models, schemas, auth
from database import get_db
from services import vendor_service

router = APIRouter(
    prefix="/api/vendors",
    tags=["vendors"]
)

@router.get("", response_model=List[schemas.VendorWithStats])
def list_vendors(
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """List all vendors for the organization with stats."""
    
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

@router.get("/{vendor_id}", response_model=schemas.VendorWithStats)
def get_vendor(
    vendor_id: str,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """Get vendor details with stats."""
    
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

@router.post("", response_model=schemas.Vendor)
def create_vendor(
    vendor: schemas.VendorCreate,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """Create a new vendor manually."""
    
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

@router.put("/{vendor_id}", response_model=schemas.Vendor)
def update_vendor(
    vendor_id: str,
    vendor_update: schemas.VendorUpdate,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """Update vendor details."""
    
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

@router.delete("/{vendor_id}")
def delete_vendor(
    vendor_id: str,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    db_vendor = db.query(models.Vendor).filter(
        models.Vendor.id == vendor_id,
        models.Vendor.organization_id == ctx.org_id
    ).first()
    
    if not db_vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
        
    db.delete(db_vendor)
    db.commit()
    
    return {"status": "success", "message": "Vendor deleted"}
