
import os
import httpx
import asyncio
import json

api_token = os.getenv("STELLAR_API_TOKEN")
tenant_id = "os_8_1"
inventory_url = "https://inventorymanagement.stellarpos.io"

async def main():
    if not api_token:
        print("STELLAR_API_TOKEN not found in environment")
        return

    headers = {
        'Authorization': f'Bearer {api_token}',
        'tenant': tenant_id,
        'tenant_id': tenant_id,
        'Referer': f'https://{tenant_id}.stellarpos.io/',
        'accept': 'application/json, text/plain, */*'
    }

    print(f"Querying Stellar for suppliers in {tenant_id}...")
    
    queries = ["Container", "Custom", "Import", "LDB", "AGLC"]
    
    for query in queries:
        print(f"\n--- Results for '{query}' ---")
        url = f"{inventory_url}/api/suppliers/retrieve/list"
        params = {'search': query, 'page': 1, 'limit': 10}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url, params=params, headers=headers)
                if response.is_success:
                    data = response.json()
                    results = data.get('result', [])
                    if not results:
                        print("No results found.")
                    for r in results:
                        print(f"Match: {r.get('name')} (ID: {r.get('id')})")
                        print(f"  Type: {r.get('supplier_type')}")
                        print(f"  Idx: {r.get('idx')}")
                else:
                    print(f"Error {response.status_code}: {response.text}")
            except Exception as e:
                print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
