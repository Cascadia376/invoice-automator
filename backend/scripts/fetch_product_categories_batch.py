import asyncio
import os
import json
import glob
import httpx
from dotenv import load_dotenv

load_dotenv()

async def fetch_categories():
    # 1. Extract Unique SKUs
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "stellar_invoices")
    files = glob.glob(os.path.join(data_dir, "*.json"))
    
    encoded_skus = set()
    sku_mapping = {} # catalog_sku -> item_group
    
    print(f"Scanning {len(files)} invoices for SKUs...")
    
    for fpath in files:
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            result = data.get('result', {})
            # Handle different structures if any
            items = result.get('supplierInvoiceItems', [])
            
            for item in items:
                # We use the catalog_sku or sku used in the search
                # Probe showed search=? matches `supplier_sku`. item also has `catalog_sku`
                # Let's collect supplier_sku as that's what we likely searched
                s_sku = item.get('sku')
                if s_sku:
                    encoded_skus.add(s_sku)
                    
        except Exception as e:
            pass
            
    print(f"Found {len(encoded_skus)} unique SKUs.")
    
    # 2. Fetch from Stellar Catalog
    token = os.getenv("STELLAR_API_TOKEN")
    tenant = os.getenv("STELLAR_TENANT_ID") or "cascadialiquor"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'tenant': tenant,
        'tenant_id': tenant,
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    }
    
    # Load existing if available to resume
    cache_file = os.path.join(data_dir, "sku_categories.json")
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            sku_mapping = json.load(f)
            
    # Filter out already known
    to_fetch = [s for s in encoded_skus if s not in sku_mapping]
    print(f"Need to fetch {len(to_fetch)} SKUs.")
    
    sem = asyncio.Semaphore(10) # 10 concurrent requests
    
    async def fetch_one(sku, client):
        async with sem:
            if sku in sku_mapping:
                return
            
            url = f"https://catalog.stellarpos.io/api/items?search={sku}"
            try:
                resp = await client.get(url, headers=headers)
                if resp.is_success:
                    data = resp.json()
                    results = data.get('result', [])
                    if results:
                        # Find exact match if possible, or take first
                        # results often contain fuzzy matches
                        # We look for item where supplier_sku == sku
                        match = None
                        for r in results:
                            if str(r.get('supplier_sku')) == str(sku):
                                match = r
                                break
                        if not match and results:
                            match = results[0]
                            
                        if match:
                            group = match.get('item_group', 'Unknown')
                            sku_mapping[sku] = group
                            return
                            
                sku_mapping[sku] = "Unknown" # Mark as checked
            except Exception as e:
                print(f"Err {sku}: {e}")

    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = []
        for i, sku in enumerate(to_fetch):
            tasks.append(fetch_one(sku, client))
            if len(tasks) >= 50:
                await asyncio.gather(*tasks)
                tasks = []
                print(f"Progress: {i}/{len(to_fetch)}...")
                # Save intermediate
                with open(cache_file, 'w') as f:
                    json.dump(sku_mapping, f, indent=2)
                    
        if tasks:
            await asyncio.gather(*tasks)
            
    # Final Save
    with open(cache_file, 'w') as f:
        json.dump(sku_mapping, f, indent=2)
        
    print("Done fetching categories.")

if __name__ == "__main__":
    asyncio.run(fetch_categories())
