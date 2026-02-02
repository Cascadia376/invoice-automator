import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

async def probe():
    token = os.getenv("STELLAR_API_TOKEN")
    tenant = os.getenv("STELLAR_TENANT_ID") or "cascadialiquor"
    
    base_url = "https://report.stellarpos.io"
    endpoint = "/api/reports/list" # common pattern
    
    headers = {
        'Authorization': f'Bearer {token}',
        'tenant': tenant,
        'tenant_id': tenant,
        'Accept': 'application/json'
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        url = f"{base_url}{endpoint}"
        try:
            resp = await client.get(url, headers=headers)
            print(f"Status: {resp.status_code}")
            if resp.is_success:
                data = resp.json()
                print("Available reports:")
                # print(data)
                if isinstance(data, list):
                    for r in data:
                        print(f"  {r.get('name')} (ID: {r.get('id')})")
                elif isinstance(data, dict):
                    # Check for data or items key
                    items = data.get('data') or data.get('items') or []
                    for r in items:
                        print(f"  {r.get('name')} (ID: {r.get('id')})")
            else:
                print(f"Error: {resp.text}")
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(probe())
