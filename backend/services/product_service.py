import os
import json
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from supabase import create_client, Client
import models
from datetime import datetime

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

_supabase: Optional[Client] = None

def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase

def normalize_category(raw_category: str) -> str:
    if not raw_category:
        return "MISC"
    
    cat = raw_category.upper()
    
    if cat in ["BEER", "WINE", "LIQUOR", "COOLERS", "CIDER", "TOBACCO", "LOTTERY", "MISC", "MIX & CONFEC"]:
        return cat
        
    # Mappings
    if any(x in cat for x in ["SPIRIT", "VODKA", "WHISKEY", "GIN", "RUM", "TEQUILA", "LIQUEUR"]):
        return "LIQUOR"
    if any(x in cat for x in ["KEG", "DRAUGHT", "MALT"]):
        return "BEER"
    if any(x in cat for x in ["RED", "WHITE", "ROSE", "SPARKLING", "FORTIFIED"]):
        return "WINE"
    if any(x in cat for x in ["RTD", "READY", "SELTZER"]):
        return "COOLERS"
    if "CIGAR" in cat or "VAPE" in cat:
        return "TOBACCO"
    if "DEPOSIT" in cat or "CONTAINER" in cat or "FREIGHT" in cat:
        return "MISC"
    if any(x in cat for x in ["MIX", "SODA", "JUICE", "WATER", "GARNISH", "SNACK", "CONFEC"]):
        return "MIX & CONFEC"
        
    return "MISC"

def get_product_by_sku(db: Session, org_id: str, sku: str) -> Optional[models.Product]:
    """Get product from local DB, fallback to Supabase."""
    # 1. Try local cache
    product = db.query(models.Product).filter(
        models.Product.organization_id == org_id,
        models.Product.sku == sku
    ).first()
    
    if product:
        return product
        
    # 2. Try Supabase
    try:
        sb = get_supabase()
        # The table name in Supabase is 'product' (singular)
        response = sb.table("product").select("*").eq("sku", sku).execute()
        
        if response.data:
            sb_prod = response.data[0]
            
            # Normalize Category
            raw_cat = sb_prod.get("category")
            normalized_cat = normalize_category(raw_cat)
            
            # 3. Save to local cache
            new_prod = models.Product(
                organization_id=org_id,
                sku=sb_prod.get("sku"),
                name=sb_prod.get("product_name") or sb_prod.get("name"),
                category=normalized_cat,
                units_per_case=float(sb_prod.get("units_per_case", 1.0)) if sb_prod.get("units_per_case") is not None else 1.0,
                average_cost=float(sb_prod.get("average_cost", 0.0)) if sb_prod.get("average_cost") is not None else 0.0,
                last_cost=float(sb_prod.get("last_cost", 0.0)) if sb_prod.get("last_cost") is not None else 0.0,
                min_typical_qty=float(sb_prod.get("min_typical_qty", 0.0)) if sb_prod.get("min_typical_qty") else None,
                max_typical_qty=float(sb_prod.get("max_typical_qty", 0.0)) if sb_prod.get("max_typical_qty") else None
            )
            db.add(new_prod)
            db.commit()
            return new_prod
    except Exception as e:
        print(f"Supabase lookup failed for SKU {sku}: {e}")
        
    return None

def validate_item_against_master(db: Session, org_id: str, item: Dict) -> Dict:
    """Validate a line item against product master data and return flags."""
    sku = item.get("sku")
    if not sku:
        return {"status": "unknown"}
        
    product = get_product_by_sku(db, org_id, sku)
    if not product:
        return {"status": "not_in_master"}
        
    flags = []
    
    # 1. Check Units Per Case
    if abs(float(item.get("units_per_case", 1.0)) - product.units_per_case) > 0.1:
        flags.append(f"UPC Mismatch: Master={product.units_per_case}, Invoice={item.get('units_per_case')}")
        
    # 2. Check Cost Variance
    unit_cost = float(item.get("unit_cost", 0.0))
    if product.last_cost > 0:
        variance = (unit_cost - product.last_cost) / product.last_cost
        if variance > 0.05:
            flags.append(f"Cost Spike: +{variance*100:.1f}% vs Last Cost (${product.last_cost})")
            
    # 3. Check Quantity Anomaly
    qty = float(item.get("quantity", 0.0))
    if product.max_typical_qty and qty > product.max_typical_qty:
        flags.append(f"Abnormal Qty: {qty} is above typical max ({product.max_typical_qty})")
        
    return {
        "status": "success",
        "product_id": product.sku,
        "master_name": product.name,
        "master_category": product.category,
        "flags": flags
    }
