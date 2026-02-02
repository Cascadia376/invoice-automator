import os
import asyncio
import httpx
from dotenv import load_dotenv
import json

load_dotenv()

async def probe_item():
    token = os.getenv("STELLAR_API_TOKEN")
    tenant = os.getenv("STELLAR_TENANT_ID") or "cascadialiquor"
    
    # SKU from the invoice we inspected
    sku = "651433" 
    
    headers = {
        'Authorization': f'Bearer {token}',
        'tenant': tenant,
        'tenant_id': tenant,
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    }
    
    # Potential endpoints based on list_all_api_paths
    urls = [
        f"https://inventorymanagement.stellarpos.io/api/items?search={sku}",
        f"https://inventorymanagement.stellarpos.io/api/products?search={sku}",
        f"https://catalog.stellarpos.io/api/items?search={sku}",
        f"https://stock-import.stellarpos.io/api/items?search={sku}"
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for url in urls:
            print(f"Checking {url}...")
            try:
                resp = await client.get(url, headers=headers)
                print(f"  Status: {resp.status_code}")
                if resp.is_success:
                    data = resp.json()
                    print("  Success! Data sample:")
                    print(json.dumps(data, indent=2)[:500])
                    
                    # Check for category field
                    # Usually in 'result' list or 'data' list
                    results = data.get('result', []) or data.get('data', [])
                    if isinstance(results, list) and len(results) > 0:
                        item = results[0]
                        print(f"  Item fields: {list(item.keys())}")
                        if 'category' in item:
                            print(f"  Category found: {item['category']}")
                        elif 'category_name' in item:
                            print(f"  Category found: {item['category_name']}")
                        elif 'group' in item:
                             print(f"  Group found: {item['group']}")
                        else:
                            print("  No explicit category field found in item.")
                            
                    return
            except Exception as e:
                print(f"  Error: {e}")

if __name__ == "__main__":
    asyncio.run(probe_item())
