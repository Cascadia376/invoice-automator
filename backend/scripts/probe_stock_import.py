import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

async def probe():
    token = os.getenv("STELLAR_API_TOKEN")
    tenant = os.getenv("STELLAR_TENANT_ID") or "cascadialiquor"
    
    url = f"https://stock-import.stellarpos.io/api/stock/retrieve-asn/SUPL-INV-2026-17066"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'tenant': tenant,
        'tenant_id': tenant,
        'Accept': 'application/json'
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        print(f"Testing {url}...")
        try:
            resp = await client.get(url, headers=headers)
            print(f"  Status: {resp.status_code}")
            if resp.is_success:
                print("  FOUND!")
                # print(resp.json())
                return
            else:
                print(f"  Failed: {resp.text}")
        except Exception as e:
            print(f"  Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(probe())
