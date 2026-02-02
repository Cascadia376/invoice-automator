import asyncio
import os
import sys
import logging
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services import stellar_service

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Configuration
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL") or "https://wobndqnfqtumbyxxtojl.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") # Must be provided in env
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation, resolution=merge-duplicates"
}

# Helpers
def to_float(val):
    try:
        return float(val) if val is not None else 0.0
    except:
        return 0.0

def to_int(val):
    try:
        return int(float(val)) if val is not None else 0
    except:
        return 0

def to_date(val):
    if not val: return None
    try:
        # Check against common empty strings or simple dates
        if isinstance(val, str) and len(val) < 5: return None
        return val
    except:
        return None

def get_latest_local_id():
    """Fetch the highest invoice_id (SUPL-INV-...) from Supabase."""
    try:
        # We assume format SUPL-INV-YYYY-XXXXX. 
        # Ordering by string might be tricky but roughly correct for recent years. 
        # Ideally we extract the number, but we can just grab the top 10 descending and parse.
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/supplier_invoices?select=invoice_id&order=invoice_id.desc&limit=5",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        )
        resp.raise_for_status()
        data = resp.json()
        
        max_id = 0
        for row in data:
            inv_id = row.get('invoice_id', '')
            if inv_id.startswith("SUPL-INV-2026-"):
                try:
                    num_part = int(inv_id.split("-")[-1])
                    if num_part > max_id:
                        max_id = num_part
                except:
                    pass
        return max_id
    except Exception as e:
        logger.error(f"Failed to get latest ID: {e}")
        return 17000 # Fallback safe start

async def process_invoice(asn, tenant):
    try:
        # 1. Fetch from Stellar
        data = await stellar_service.retrieve_stellar_invoice(asn, tenant)
        
        # 2. Parse & Aggregate
        result = data.get("result", {})
        supplier_inv = result.get("supplierInvoice", {})
        items = result.get("supplierInvoiceItems", [])
        
        if not supplier_inv and not items:
            logger.warning(f"  Empty data for {asn}")
            return False

        # Prepare Header
        header_payload = {
            "invoice_id": asn,
            "supplier_name": supplier_inv.get("supplier_name"),
            "supplier_invoice_number": supplier_inv.get("supplier_invoice_no") or supplier_inv.get("invoice_number"),
            "original_po_number": supplier_inv.get("original_po_number"),
            "status": supplier_inv.get("status"),
            "store_name": supplier_inv.get("location_name"),
            "sub_total": to_float(supplier_inv.get("sub_total") or supplier_inv.get("total_amount_excluded_tax")),
            "total_taxes": to_float(supplier_inv.get("total_tax") or supplier_inv.get("tax_amount")),
            "total_deposits": to_float(supplier_inv.get("total_deposit")),
            "invoice_total": to_float(supplier_inv.get("total_amount_included_tax") or supplier_inv.get("grand_total")),
            "created_date": to_date(supplier_inv.get("createdAt")),
            "date_received": to_date(supplier_inv.get("received_date") or supplier_inv.get("lastReceivedAt")),
            "date_posted": to_date(supplier_inv.get("updatedAt")),
            "meta_data": json.dumps(result)
        }
        
        # Upsert Header
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/supplier_invoices?on_conflict=invoice_id",
            headers=HEADERS,
            json=header_payload
        )
        if resp.status_code not in [200, 201]:
            logger.error(f"  Failed Header {asn}: {resp.text}")
            return False

        # Clear existing items
        del_resp = requests.delete(
            f"{SUPABASE_URL}/rest/v1/supplier_invoice_items?invoice_id=eq.{asn}",
            headers=HEADERS
        )
        
        # Aggregate Items
        aggregated_items = {} 
        for item in items:
            sku = item.get("sku")
            if not sku: continue
            
            qty_rec = to_float(item.get("shipped_qty_received") or item.get("shipped_qty") or 0)
            qty_ord = to_int(float(item.get("shipped_qty") or 0))
            unit_price = to_float(item.get("unit_price_received") or item.get("unit_price") or 0)
            deposit = to_float(item.get("depositAmount") or 0)
            line_total = (qty_rec * unit_price) if qty_rec else 0.0

            if sku in aggregated_items:
                agg = aggregated_items[sku]
                agg["received_quantity"] += qty_rec
                agg["units_ordered"] += qty_ord
                agg["total_cost"] += line_total
                agg["total_deposits"] += deposit
                agg["_metadata_list"].append(item)
            else:
                aggregated_items[sku] = {
                    "sku": sku,
                    "product_name": item.get("item_name"),
                    "volume": item.get("volume"),
                    "units_ordered": qty_ord,
                    "received_quantity": qty_rec,
                    "total_cost": line_total,
                    "total_deposits": deposit,
                    "invoice_date": supplier_inv.get("lastReceivedAt"),
                    "_metadata_list": [item]
                }

        # Build Items Payload
        items_payload = []
        line_num = 1
        for sku, agg in aggregated_items.items():
            avg_cost = (agg["total_cost"] / agg["received_quantity"]) if agg["received_quantity"] > 0 else 0.0
            items_payload.append({
                "invoice_id": asn,
                "line_number": line_num,
                "sku": sku,
                "product_name": agg["product_name"],
                "volume": agg["volume"],
                "units_ordered": agg["units_ordered"],
                "received_quantity": agg["received_quantity"],
                "unit_cost": avg_cost,
                "total_cost": agg["total_cost"],
                "total_deposits": agg["total_deposits"],
                "invoice_date": to_date(agg["invoice_date"]),
                "metadata": json.dumps(agg["_metadata_list"])
            })
            line_num += 1

        if items_payload:
            item_resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/supplier_invoice_items",
                headers=HEADERS,
                json=items_payload
            )
            if item_resp.status_code not in [200, 201]:
                logger.error(f"  Failed Items {asn}: {item_resp.text}")
                return False
        
        logger.info(f"Synced {asn}")
        return True

    except stellar_service.StellarError as e:
        if e.status_code == 404:
            return "404"
        logger.error(f"  API Error {asn}: {e}")
        return False
    except Exception as e:
        logger.error(f"  Error {asn}: {e}")
        return False

async def main():
    if not SUPABASE_KEY:
        logger.error("Missing SUPABASE_SERVICE_ROLE_KEY")
        return

    logger.info("Starting Daily Invoice Sync...")
    
    # 1. Get Start ID
    last_id = get_latest_local_id()
    logger.info(f"Last known Invoice ID: {last_id}")
    
    # 2. Iterate forward
    current_id = last_id + 1
    consecutive_404s = 0
    max_404s = 10 # Stop if 10 blanks in a row
    limit_processed = 500 # Safety cap
    
    processed = 0
    tenant = os.getenv("STELLAR_TENANT_ID") or "cascadialiquor"
    
    while consecutive_404s < max_404s and processed < limit_processed:
        asn = f"SUPL-INV-2026-{current_id}"
        # logger.info(f"Checking {asn}...")
        
        result = await process_invoice(asn, tenant)
        
        if result == "404":
            consecutive_404s += 1
            logger.info(f"{asn} not found. ({consecutive_404s}/{max_404s})")
        elif result is True:
            consecutive_404s = 0 # Reset on success
            processed += 1
        else:
            # Other error, keep going but count as gap? No, retry?
            # For simplicity, treat as gap but log it
            pass
            
        current_id += 1
        await asyncio.sleep(0.5) # Gentle rate limit

    logger.info(f"Daily Sync Complete. Processed {processed} new invoices.")

if __name__ == "__main__":
    asyncio.run(main())
