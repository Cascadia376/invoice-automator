import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

async def probe():
    token = os.getenv("STELLAR_API_TOKEN")
    tenant = os.getenv("STELLAR_TENANT_ID") or "cascadialiquor"
    
    base_url = "https://inventorymanagement.stellarpos.io"
    ids = ["SUPL-INV-2026-17066", "17066"]
    paths = [
        "/api/supplier-invoices/retrieve/id",
        "/api/supplier-invoices/show",
        "/api/supplier-invoices"
    ]
    
    headers = {
        'Authorization': f'Bearer {token}',
        'tenant': tenant,
        'tenant_id': tenant,
        'Accept': 'application/json'
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for path in paths:
            for id in ids:
                url = f"{base_url}{path}/{id}"
                print(f"Testing {url}...")
                try:
                    resp = await client.get(url, headers=headers)
                    print(f"  Status: {resp.status_code}")
                    if resp.is_success:
                        print(f"  FOUND! ID {id} at {url}")
                        # print(resp.json())
                        return
                except Exception as e:
                    print(f"  Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(probe())
