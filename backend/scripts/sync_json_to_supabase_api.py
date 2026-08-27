import os
import json
import glob
import logging
import requests
import sys

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://wobndqnfqtumbyxxtojl.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def sync_invoices():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "stellar_invoices")
    files = glob.glob(os.path.join(data_dir, "*.json"))
    files.sort()

    logger.info(f"Found {len(files)} invoice files to sync via API.")

    success_count = 0
    fail_count = 0

    for fpath in files:
        try:
            filename = os.path.basename(fpath)
            file_id_str = filename.replace("SUPL-INV-2026-", "").replace(".json", "")
            if int(file_id_str) <= 17666:
                continue
        except Exception:
            pass

        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if "status" in data and isinstance(data.get("status"), int) and data.get("status") != 200:
                logger.warning(f"Skipping {os.path.basename(fpath)}: Status {data.get('status')}")
                continue

            result = data.get("result", {})
            if not result:
                logger.warning(f"Skipping {os.path.basename(fpath)}: Empty result")
                continue

            supplier_inv = result.get("supplierInvoice", {})
            supplier_data = result.get("supplierData", {})
            items = result.get("supplierInvoiceItems", [])

            asn = supplier_inv.get("name")
            if not asn:
                asn = os.path.basename(fpath).replace(".json", "")

            def to_float(val):
                if val is None or val == "":
                    return None
                try:
                    return float(val)
                except Exception:
                    return None

            def to_int(val):
                if val is None or val == "":
                    return None
                try:
                    return int(val)
                except Exception:
                    return None

            def to_date(val):
                if not val:
                    return None
                return val

            invoice_payload = {
                "invoice_id": asn,
                "supplier_name": supplier_inv.get("supplier_name") or supplier_data.get("name"),
                "supplier_invoice_number": supplier_inv.get("supplier_invoice_no"),
                "original_po_number": supplier_inv.get("associatedPOId"),
                "store_name": supplier_inv.get("target_warehouse_address"),
                "created_date": to_date(supplier_inv.get("createdAt")),
                "date_received": to_date(supplier_inv.get("lastReceivedAt")),
                "date_posted": to_date(supplier_inv.get("completedAt")),
                "invoice_type": "invoice",
                "sub_total": to_float(supplier_inv.get("subTotal")),
                "total_deposits": to_float(supplier_inv.get("totalDeposits")),
                "total_taxes": to_float(supplier_inv.get("totalTaxes")),
                "invoice_total": to_float(supplier_inv.get("grandTotal")),
                "status": "completed" if supplier_inv.get("completed") else "pending",
                "metadata": json.dumps(result)
            }

            upsert_headers = HEADERS.copy()
            upsert_headers["Prefer"] = "resolution=merge-duplicates,return=representation"

            resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/supplier_invoices?on_conflict=invoice_id",
                headers=upsert_headers,
                json=invoice_payload
            )

            if resp.status_code not in [200, 201]:
                logger.error(f"Failed to upsert invoice {asn}: {resp.text}")
                fail_count += 1
                continue

            requests.delete(
                f"{SUPABASE_URL}/rest/v1/supplier_invoice_items?invoice_id=eq.{asn}",
                headers=HEADERS
            )

            if items:
                aggregated_items = {}

                for item in items:
                    sku = item.get("sku")
                    if not sku:
                        continue
                    qty_received = to_float(item.get("shipped_qty_received") or item.get("shipped_qty") or 0)
                    qty_ordered = to_int(float(item.get("shipped_qty") or 0))
                    unit_price = to_float(item.get("unit_price_received") or item.get("unit_price") or 0)
                    deposit_amt = to_float(item.get("depositAmount") or 0)
                    line_total_cost = (qty_received * unit_price) if qty_received and unit_price else 0.0

                    if sku in aggregated_items:
                        agg = aggregated_items[sku]
                        agg["received_quantity"] += (qty_received or 0)
                        agg["units_ordered"] += (qty_ordered or 0)
                        agg["total_cost"] += line_total_cost
                        agg["total_deposits"] += deposit_amt
                        agg["_metadata_list"].append(item)
                    else:
                        aggregated_items[sku] = {
                            "sku": sku,
                            "product_name": item.get("item_name"),
                            "volume": item.get("volume"),
                            "units_ordered": qty_ordered,
                            "received_quantity": qty_received,
                            "total_cost": line_total_cost,
                            "total_deposits": deposit_amt,
                            "invoice_date": supplier_inv.get("lastReceivedAt"),
                            "_metadata_list": [item]
                        }

                items_payload = []
                line_number = 1

                for _, agg in aggregated_items.items():
                    avg_unit_cost = (
                        agg["total_cost"] / agg["received_quantity"]
                        if agg["received_quantity"] and agg["received_quantity"] > 0
                        else 0.0
                    )
                    items_payload.append({
                        "invoice_id": asn,
                        "line_number": line_number,
                        "sku": agg["sku"],
                        "product_name": agg["product_name"],
                        "volume": agg["volume"],
                        "units_ordered": agg["units_ordered"],
                        "received_quantity": agg["received_quantity"],
                        "unit_cost": avg_unit_cost,
                        "total_cost": agg["total_cost"],
                        "total_deposits": agg["total_deposits"],
                        "invoice_date": to_date(agg["invoice_date"]),
                        "metadata": json.dumps(agg["_metadata_list"])
                    })
                    line_number += 1

                item_resp = requests.post(
                    f"{SUPABASE_URL}/rest/v1/supplier_invoice_items",
                    headers=HEADERS,
                    json=items_payload
                )

                if item_resp.status_code not in [200, 201]:
                    logger.error(f"Failed to insert items for {asn}: {item_resp.text}")

            logger.info(f"Synced {asn} | {len(items)} raw -> {len(items_payload) if items else 0} agg items")
            success_count += 1

        except Exception as e:
            logger.error(f"Error processing {fpath}: {str(e)}")
            fail_count += 1

    logger.info(f"Sync Complete. Success: {success_count}, Failed: {fail_count}")

if __name__ == "__main__":
    sync_invoices()
