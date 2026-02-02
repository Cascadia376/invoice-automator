import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

async def probe():
    token = os.getenv("STELLAR_API_TOKEN")
    tenant = os.getenv("STELLAR_TENANT_ID") or "cascadialiquor"
    
    host = "https://report.stellarpos.io"
    prefixes = [
        "/api/supplier-invoices/retrieve/id",
        "/api/stock/retrieve-asn",
        "/api/supplier-invoices",
        "/api/supplier-invoices/show",
        "/api/stock/supplier-invoices",
        "/api/inventory/supplier-invoices"
    ]
    
    asn = "SUPL-INV-2026-17066"
    headers = {
        'Authorization': f'Bearer {token}',
        'tenant': tenant,
        'tenant_id': tenant,
        'Accept': 'application/json'
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for prefix in prefixes:
            url = f"{host}{prefix}/{asn}"
            try:
                resp = await client.get(url, headers=headers)
                print(f"URL {url}: {resp.status_code}")
                if resp.is_success:
                    print(f"  FOUND! ASN {asn} at {url}")
                    # print(resp.json())
                    return
            except Exception as e:
                print(f"URL {url}: Error {str(e)}")

if __name__ == "__main__":
    asyncio.run(probe())
