from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime

import models, schemas, auth
from database import get_db
from services import stellar_service
from services.stellar_service import StellarError

router = APIRouter(
    prefix="/api/stellar",
    tags=["stellar"]
)

@router.get("/discover/suppliers", response_model=Optional[schemas.GlobalVendorMapping])
def discover_supplier(
    name: str = Query(..., description="The name of the vendor to look up"),
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """
    Search for a suggested Stellar mapping for a vendor name.
    """
    # Simple exact match for now, could be enhanced with fuzzy search later
    mapping = db.query(models.GlobalVendorMapping).filter(
        models.GlobalVendorMapping.vendor_name == name
    ).first()
    
    return mapping

@router.post("/mappings", response_model=schemas.GlobalVendorMapping)
def contribute_mapping(
    mapping_in: schemas.GlobalVendorMappingCreate,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """
    Manually contribute or update a global mapping.
    """
    existing = db.query(models.GlobalVendorMapping).filter(
        models.GlobalVendorMapping.vendor_name == mapping_in.vendor_name
    ).first()
    
    if existing:
        existing.stellar_supplier_id = mapping_in.stellar_supplier_id
        existing.stellar_supplier_name = mapping_in.stellar_supplier_name
        existing.usage_count += 1
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    
    new_mapping = models.GlobalVendorMapping(
        id=str(uuid.uuid4()),
        vendor_name=mapping_in.vendor_name,
        stellar_supplier_id=mapping_in.stellar_supplier_id,
        stellar_supplier_name=mapping_in.stellar_supplier_name,
        confidence_score=mapping_in.confidence_score
    )
    db.add(new_mapping)
    db.commit()
    db.refresh(new_mapping)
    return new_mapping

@router.post("/bulk-import")
def bulk_import_mappings(
    mappings: List[schemas.GlobalVendorMappingCreate],
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """
    Bulk import mapping records (Option C).
    """
    count = 0
    for m in mappings:
        existing = db.query(models.GlobalVendorMapping).filter(
            models.GlobalVendorMapping.vendor_name == m.vendor_name
        ).first()
        
        if existing:
            existing.stellar_supplier_id = m.stellar_supplier_id
            existing.stellar_supplier_name = m.stellar_supplier_name
            existing.updated_at = datetime.utcnow()
        else:
            new_m = models.GlobalVendorMapping(
                id=str(uuid.uuid4()),
                vendor_name=m.vendor_name,
                stellar_supplier_id=m.stellar_supplier_id,
                stellar_supplier_name=m.stellar_supplier_name
            )
            db.add(new_m)
        count += 1
    
    db.commit()
    return {"status": "success", "imported": count}

@router.get("/proxy/suppliers")
async def proxy_search_suppliers(
    name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """
    Proxy request to Stellar to search for suppliers.
    """
    # Fetch store config to get the correct tenant
    store = db.query(models.Store).filter(
        models.Store.organization_id == ctx.org_id
    ).first()
    
    tenant_id = getattr(store, 'stellar_tenant', None)
    
    try:
        results = await stellar_service.search_stellar_suppliers(
            query=name or "",
            tenant_id=tenant_id
        )
        return results
    except StellarError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
