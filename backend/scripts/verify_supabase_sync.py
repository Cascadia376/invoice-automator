import requests
import logging

SUPABASE_URL = "https://wobndqnfqtumbyxxtojl.supabase.co"
SUPABASE_KEY = "sb_secret_wCoX-veuddkQ-S-23vmadA_fkvQ-bz_"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def verify_sync():
    # Count Invoices
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/supplier_invoices?select=count",
        headers={**HEADERS, "Range-Unit": "items"},
    )
    
    # Range-Unit: items
    # Content-Range: 0-0/44  <-- Total is 44
    content_range = resp.headers.get("Content-Range", "0-0/0")
    total_invoices = content_range.split("/")[-1]
    
    print(f"Total Invoices in Database: {total_invoices}")

    # Check for specific Invoice
    check_asn = "SUPL-INV-2026-17067"
    item_resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/supplier_invoices?invoice_id=eq.{check_asn}&select=*",
        headers=HEADERS
    )
    
    if item_resp.status_code == 200 and len(item_resp.json()) > 0:
        print(f"Verified {check_asn}: EXISTS")
    else:
        print(f"Verified {check_asn}: MISSING")

if __name__ == "__main__":
    verify_sync()
