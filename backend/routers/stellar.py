from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime

import models, schemas, auth
from database import get_db
from services import stellar_service, reporting_service
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
    
    tenant_id = getattr(store, 'stellar_tenant', None) if store else None
    
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

@router.get("/suppliers")
async def list_all_suppliers(
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """
    List all Stellar suppliers (or top 1000) for preloading in UI.
    Cached for performance (not really, but frontend should cache).
    """
    # Fetch store config to get the correct tenant
    store = db.query(models.Store).filter(
        models.Store.organization_id == ctx.org_id
    ).first()
    
    tenant_id = getattr(store, 'stellar_tenant', None) if store else None
    
    # We could implement redis/memory caching here if needed
    
    items = await stellar_service.list_stellar_suppliers(tenant_id=tenant_id)
    return items


@router.get("/sync/{invoice_id}")
async def sync_invoice_from_stellar(
    invoice_id: str,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """
    Retrieve the latest data from Stellar for a specific invoice and update our records.
    """
    invoice = db.query(models.Invoice).filter(
        models.Invoice.id == invoice_id,
        models.Invoice.organization_id == ctx.org_id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    if not invoice.stellar_asn_number:
        raise HTTPException(status_code=400, detail="Invoice has not been posted to Stellar yet")
        
    # Get store/tenant config
    store = db.query(models.Store).filter(
        models.Store.organization_id == ctx.org_id
    ).first()
    
    tenant_id = getattr(store, 'stellar_tenant', None)
    if not tenant_id:
        # Fallback to env default if store not configured
        tenant_id = stellar_service.STELLAR_TENANT_ID
        
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Stellar Tenant ID not configured for this store")
        
    try:
        # Retrieve latest data from Stellar
        stellar_data = await stellar_service.retrieve_stellar_invoice(
            asn_number=invoice.stellar_asn_number,
            tenant_id=tenant_id
        )
        
        # Update local record with latest response
        import json
        invoice.stellar_response = json.dumps(stellar_data)
        
        # If Stellar has a different internal ID/ASN, update ours
        # (Useful if the first post returned a temporary ID)
        if 'asn_number' in stellar_data:
            invoice.stellar_asn_number = stellar_data['asn_number']
        elif 'id' in stellar_data:
            invoice.stellar_asn_number = stellar_data['id']
            
        db.commit()
        db.refresh(invoice)
        
        return {
            "status": "success",
            "message": "Synced with Stellar",
            "invoice": {
                "id": invoice.id,
                "stellar_asn_number": invoice.stellar_asn_number,
                "stellar_data": stellar_data,
                "stellar_tenant": tenant_id
            }
        }
    except StellarError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@router.get("/reports/receiving-summary")
def get_receiving_summary_report(
    start_date: str = Query(..., description="ISO format date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="ISO format date (YYYY-MM-DD)"),
    store_name: Optional[str] = Query(None),
    format: str = Query("json", description="json or csv"),
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """
    Generate the 'Receiving Summary' report for a date range.
    """
    try:
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    data = reporting_service.generate_receiving_summary(
        db=db,
        start_date=start_dt,
        end_date=end_dt,
        store_name=store_name
    )

    if format.lower() == "csv":
        from fastapi.responses import Response
        csv_data = reporting_service.export_summary_to_csv(data)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=receiving_summary_{start_date}_{end_date}.csv"}
        )

    return data

