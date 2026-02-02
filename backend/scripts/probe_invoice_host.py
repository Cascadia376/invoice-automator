import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

async def probe():
    token = os.getenv("STELLAR_API_TOKEN")
    tenant = os.getenv("STELLAR_TENANT_ID") or "cascadialiquor"
    asn = "SUPL-INV-2026-17066"
    short_id = "17066"
    
    targets = [
        {"host": "https://invoice.stellarpos.io", "paths": [
            f"/api/invoices/{asn}",
            f"/api/invoices/{short_id}",
            f"/api/supplier-invoices/{asn}",
            f"/api/supplier-invoices/retrieve/id/{asn}",
            f"/api/invoices/retrieve/{asn}"
        ]},
        {"host": "https://report.stellarpos.io", "paths": [
            f"/api/reports/supplier-invoice/{asn}",
            f"/api/reports/supplier-invoices/{asn}",
            "/api/reports/supplier-invoice", # Query param style?
        ]},
        {"host": "https://inventorymanagement.stellarpos.io", "paths": [
             f"/api/invoices/{asn}", # Maybe it's under 'invoices' not 'supplier-invoices'
             f"/api/supplier-invoices/details/{asn}"
        ]}
    ]
    
    headers = {
        'Authorization': f'Bearer {token}',
        'tenant': tenant,
        'tenant_id': tenant,
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    
    async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
        for target in targets:
            host = target['host']
            print(f"--- Probing {host} ---")
            for path in target['paths']:
                url = f"{host}{path}"
                try:
                    resp = await client.get(url, headers=headers)
                    print(f"[{resp.status_code}] {path}")
                    if resp.status_code == 200:
                        ct = resp.headers.get("content-type", "")
                        print(f"  Content-Type: {ct}")
                        if "json" in ct:
                            print("  FOUND JSON!")
                            print(resp.text[:200])
                            return
                        else:
                            print("  (Not JSON)")
                except Exception as e:
                    print(f"[ERR] {path}: {e}")

if __name__ == "__main__":
    asyncio.run(probe())
