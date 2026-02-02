import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

async def probe():
    token = os.getenv("STELLAR_API_TOKEN")
    tenant = os.getenv("STELLAR_TENANT_ID") or "cascadialiquor"
    asn = "SUPL-INV-2026-17066"
    
    # Based on fetchData code: 
    # I.STOCK_IMPORT.get("/supplier-invoices/" + id)
    
    # We probe both with and without /api prefix as structure is unknown
    paths = [
        f"/supplier-invoices/{asn}",
        f"/api/supplier-invoices/{asn}",
        f"/stock/supplier-invoices/{asn}", # sometimes namespaced
    ]
    
    # Also try just the numeric part
    short_id = "17066"
    paths.append(f"/supplier-invoices/{short_id}")
    paths.append(f"/api/supplier-invoices/{short_id}")

    base_url = "https://stock-import.stellarpos.io"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'tenant': tenant,
        'tenant_id': tenant,
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for path in paths:
            url = f"{base_url}{path}"
            print(f"Testing {url}...")
            try:
                resp = await client.get(url, headers=headers)
                print(f"  Status: {resp.status_code}")
                if resp.is_success:
                    print("  FOUND!")
                    # Check if it looks like the right data
                    print(resp.text[:500])
                    return
                else:
                    print(f"  Failed: {resp.text[:100]}")
            except Exception as e:
                print(f"  Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(probe())
