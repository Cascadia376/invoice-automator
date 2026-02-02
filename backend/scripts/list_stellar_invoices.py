import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

async def probe():
    token = os.getenv("STELLAR_API_TOKEN")
    tenant = os.getenv("STELLAR_TENANT_ID") or "cascadialiquor"
    
    base_url = "https://inventorymanagement.stellarpos.io"
    endpoint = "/api/supplier-invoices/retrieve/list"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'tenant': tenant,
        'tenant_id': tenant,
        'Accept': 'application/json'
    }
    
    params = {
        'page': 1,
        'limit': 10
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        url = f"{base_url}{endpoint}"
        try:
            resp = await client.get(url, headers=headers, params=params)
            print(f"Status: {resp.status_code}")
            if resp.is_success:
                data = resp.json()
                print("Success! Recent invoices:")
                # print(data)
                # Try to find an invoice and print its ID
                if 'data' in data and len(data['data']) > 0:
                    for inv in data['data']:
                        print(f"  ASN: {inv.get('asn_number')} (ID: {inv.get('id')})")
            else:
                print(f"Error: {resp.text}")
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(probe())
