import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

async def probe():
    token = os.getenv("STELLAR_API_TOKEN")
    tenant = os.getenv("STELLAR_TENANT_ID") or "cascadialiquor"
    
    url = f"https://{tenant}.stellarpos.io/api/supplier-invoices/retrieve/id/SUPL-INV-2026-17066"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'tenant': tenant,
        'tenant_id': tenant,
        'Accept': 'application/json, text/plain, */*',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        print(f"Testing {url} with X-Requested-With...")
        try:
            resp = await client.get(url, headers=headers)
            print(f"  Status: {resp.status_code}")
            print(f"  Content-Type: {resp.headers.get('content-type')}")
            if resp.is_success and 'application/json' in resp.headers.get('content-type', ''):
                print("  FOUND JSON!")
                # print(resp.json())
                return
            else:
                print("  Still HTML or failed.")
        except Exception as e:
            print(f"  Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(probe())
