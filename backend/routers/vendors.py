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
            "stellar_supplier_id": vendor.stellar_supplier_id,
            "stellar_supplier_name": vendor.stellar_supplier_name,
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
        "stellar_supplier_id": vendor.stellar_supplier_id,
        "stellar_supplier_name": vendor.stellar_supplier_name,
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
    
    # Stellar POS integration fields
    if vendor_update.stellar_supplier_id is not None:
        db_vendor.stellar_supplier_id = vendor_update.stellar_supplier_id
    if vendor_update.stellar_supplier_name is not None:
        db_vendor.stellar_supplier_name = vendor_update.stellar_supplier_name
    
    db_vendor.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_vendor)
    
    # Automatically contribute to Global Registry if Stellar IDs are provided
    if db_vendor.stellar_supplier_id and db_vendor.stellar_supplier_name:
        try:
            existing_global = db.query(models.GlobalVendorMapping).filter(
                models.GlobalVendorMapping.vendor_name == db_vendor.name
            ).first()
            
            if existing_global:
                existing_global.stellar_supplier_id = db_vendor.stellar_supplier_id
                existing_global.stellar_supplier_name = db_vendor.stellar_supplier_name
                existing_global.updated_at = datetime.utcnow()
            else:
                new_global = models.GlobalVendorMapping(
                    id=str(uuid.uuid4()),
                    vendor_name=db_vendor.name,
                    stellar_supplier_id=db_vendor.stellar_supplier_id,
                    stellar_supplier_name=db_vendor.stellar_supplier_name
                )
                db.add(new_global)
            db.commit()
        except Exception as e:
            print(f"Failed to auto-contribute to global registry: {e}")
            db.rollback()
    
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

@router.post("/link-stellar-by-name")
def link_stellar_by_name(
    link_data: schemas.VendorLinkStellarRequest,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """
    Link a vendor to a Stellar Supplier by Name.
    If the vendor doesn't exist, it creates it.
    Also updates the Global Registry.
    """
    # 1. Find or Create Vendor
    vendor = vendor_service.find_vendor_by_name(db, link_data.vendor_name, ctx.org_id)
    
    if not vendor:
        # Create new vendor
        vendor = models.Vendor(
            id=str(uuid.uuid4()),
            organization_id=ctx.org_id,
            name=link_data.vendor_name,
            stellar_supplier_id=link_data.stellar_supplier_id,
            stellar_supplier_name=link_data.stellar_supplier_name
        )
        db.add(vendor)
    else:
        # Update existing
        vendor.stellar_supplier_id = link_data.stellar_supplier_id
        vendor.stellar_supplier_name = link_data.stellar_supplier_name
        vendor.updated_at = datetime.utcnow()
        
    db.commit()
    db.refresh(vendor)
    
    # 2. Update Global Registry (Always)
    try:
        existing_global = db.query(models.GlobalVendorMapping).filter(
            models.GlobalVendorMapping.vendor_name == link_data.vendor_name
        ).first()
        
        if existing_global:
            existing_global.stellar_supplier_id = link_data.stellar_supplier_id
            existing_global.stellar_supplier_name = link_data.stellar_supplier_name
            existing_global.updated_at = datetime.utcnow()
        else:
            new_global = models.GlobalVendorMapping(
                id=str(uuid.uuid4()),
                vendor_name=link_data.vendor_name,
                stellar_supplier_id=link_data.stellar_supplier_id,
                stellar_supplier_name=link_data.stellar_supplier_name
            )
            db.add(new_global)
        db.commit()
    except Exception as e:
        print(f"Failed to update global registry during link: {e}")
        # Don't fail the request, just log
        
    return {"status": "success", "message": f"Linked '{link_data.vendor_name}' to Stellar Supplier"}
