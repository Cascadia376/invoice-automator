import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

async def probe():
    token = os.getenv("STELLAR_API_TOKEN")
    tenant = os.getenv("STELLAR_TENANT_ID") or "cascadialiquor"
    
    hosts = [
        "https://inventorymanagement.stellarpos.io",
        "https://report.stellarpos.io",
        f"https://{tenant}.stellarpos.io",
        "https://stock-import.stellarpos.io"
    ]
    
    prefixes = [
        "/api/supplier-invoices/retrieve/id",
        "/api/stock/retrieve-asn",
        "/api/v1/supplier-invoices",
        "/api/purchase-orders/retrieve/id"
    ]
    
    asn = "SUPL-INV-2026-17066"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'tenant': tenant,
        'tenant_id': tenant,
        'accept': 'application/json'
    }
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for host in hosts:
            for prefix in prefixes:
                url = f"{host}{prefix}/{asn}"
                try:
                    resp = await client.get(url, headers=headers)
                    print(f"URL {url}: {resp.status_code}")
                    if resp.is_success:
                        print(f"  FOUND! ASN {asn} at {url}")
                        # print(json.dumps(resp.json(), indent=2))
                        return
                except Exception as e:
                    print(f"URL {url}: Error {str(e)}")

if __name__ == "__main__":
    asyncio.run(probe())
