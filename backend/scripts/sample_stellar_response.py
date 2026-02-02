import os
import asyncio
import httpx
import json
from dotenv import load_dotenv

load_dotenv()

async def probe():
    token = os.getenv("STELLAR_API_TOKEN")
    tenant = os.getenv("STELLAR_TENANT_ID") or "cascadialiquor"
    asn = "SUPL-INV-2026-17066"
    url = f"https://{tenant}.stellarpos.io/api/supplier-invoices/retrieve/id/{asn}"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'tenant': tenant,
        'tenant_id': tenant,
        'accept': 'application/json'
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            if resp.is_success:
                data = resp.json()
                print(json.dumps(data, indent=2))
            else:
                print(f"Failed: {resp.status_code}")
                print(resp.text)
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(probe())
