import asyncio
import os
import json
import glob
import httpx
from dotenv import load_dotenv

load_dotenv()

import asyncio
import os
import json
import httpx
from dotenv import load_dotenv

# Explicitly load from root .env
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(root_dir, '.env')
load_dotenv(env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL") or "https://wobndqnfqtumbyxxtojl.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_KEY:
    print(f"ERROR: SUPABASE_SERVICE_ROLE_KEY not found in {env_path}")
    # Fallback to hardcoded for the agent session if needed (but try to avoid)
    # exit(1)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

async def fetch_categories():
    # 1. Fetch Unique SKUs from DB
    print("Fetching unique SKUs from Supabase...")
    # This query might be heavy if many rows, but select distinct is better
    # But API doesn't support SELECT DISTINCT easily on non-PK.
    # We can fetch all and distinct in python or use an RPC if available.
    # Fallback: Fetch all SKUs (limit 10000) - for 1300 invoices, ~40k rows. 
    # Better: Use RPC or raw SQL? Without RPC, we just fetch.
    # Actually, we can assume we only need SKUs for invoices we have.
    
    encoded_skus = set()
    
    async with httpx.AsyncClient() as client:
        # Paging through items
        offset = 0
        limit = 1000
        while True:
            # Use limit/offset for PostgREST
            r = await client.get(
                f"{SUPABASE_URL}/rest/v1/supplier_invoice_items?select=sku&limit={limit}&offset={offset}",
                headers=HEADERS
            )
            if r.status_code != 200:
                print(f"Error fetching SKUs: {r.text}")
                break
                
            items = r.json()
            if not items:
                break
                
            for i in items:
                if i.get('sku'):
                    encoded_skus.add(i['sku'])
            
            offset += limit
            print(f"Loaded {len(encoded_skus)} unique SKUs so far... (offset {offset})")
            if len(items) < limit:
                break

    print(f"Total Unique SKUs: {len(encoded_skus)}")

    # 2. Check which ones we already have in `stellar_sku_categories`
    existing_skus = set()
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{SUPABASE_URL}/rest/v1/stellar_sku_categories?select=sku", headers=HEADERS)
        if r.status_code == 200:
            for row in r.json():
                existing_skus.add(row['sku'])
    
    to_fetch = list(encoded_skus - existing_skus)
    print(f"Need to fetch info for {len(to_fetch)} new SKUs.")
    
    if not to_fetch:
        print("All SKUs already categorized.")
        return

    # 3. Fetch from Stellar & Upsert
    token = os.getenv("STELLAR_API_TOKEN")
    tenant = os.getenv("STELLAR_TENANT_ID") or "cascadialiquor"
    
    stellar_headers = {
        'Authorization': f'Bearer {token}',
        'tenant': tenant,
        'tenant_id': tenant,
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    }
    
    sem = asyncio.Semaphore(10)
    
    async def process_sku(sku, client):
        async with sem:
            cat = "Unknown"
            url = f"https://catalog.stellarpos.io/api/items?search={sku}"
            try:
                resp = await client.get(url, headers=stellar_headers)
                if resp.is_success:
                    data = resp.json()
                    results = data.get('result', [])
                    match = None
                    for r in results:
                        if str(r.get('supplier_sku')) == str(sku):
                            match = r
                            break
                    if not match and results:
                        match = results[0]
                    
                    if match:
                        cat = match.get('item_group', 'Unknown')
            except Exception as e:
                print(f"Error fetching {sku}: {e}")
            
            # Upsert to DB
            payload = {"sku": sku, "category": cat}
            try:
                await client.post(
                    f"{SUPABASE_URL}/rest/v1/stellar_sku_categories?on_conflict=sku",
                    headers={**HEADERS, "Prefer": "resolution=merge-duplicates"},
                    json=payload
                )
                # print(f"Saved {sku} -> {cat}")
            except Exception as e:
                print(f"Error saving {sku}: {e}")

    async with httpx.AsyncClient(timeout=15.0) as client:
        tasks = []
        for i, sku in enumerate(to_fetch):
            tasks.append(process_sku(sku, client))
            if len(tasks) >= 20:
                await asyncio.gather(*tasks)
                tasks = []
                print(f"Progress: {i}/{len(to_fetch)}...")
        
        if tasks:
            await asyncio.gather(*tasks)

    print("Done categorizing SKUs.")

if __name__ == "__main__":
    asyncio.run(fetch_categories())

if __name__ == "__main__":
    asyncio.run(fetch_categories())
