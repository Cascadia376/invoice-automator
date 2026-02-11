
import os
import asyncio
import httpx
from dotenv import load_dotenv
import json

load_dotenv()

async def probe():
    token = os.getenv("STELLAR_API_TOKEN")
    tenant = os.getenv("STELLAR_TENANT_ID") or "cascadialiquor"
    
    # User's provided URL
    url = "https://inventorymanagement.stellarpos.io/api/suppliers/retrieve/list"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'tenant': tenant,
        'tenant_id': tenant,
        'Accept': 'application/json'
    }
    
    params = {
        'search': 'AGLC',
        'page': 1,
        'limit': 10
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, headers=headers, params=params)
            print(f"Status: {resp.status_code}")
            if resp.is_success:
                data = resp.json()
                with open("stellar_supplier_aglc.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                print("Successfully wrote to stellar_supplier_aglc.json")
            else:
                print(f"Error Content: {resp.text}")
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(probe())
