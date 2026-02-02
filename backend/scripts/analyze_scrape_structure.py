import os
import asyncio
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import json

load_dotenv()

async def probe():
    token = os.getenv("STELLAR_API_TOKEN")
    tenant = os.getenv("STELLAR_TENANT_ID") or "cascadialiquor"
    asn = "SUPL-INV-2026-17066"
    
    # Try the review URL
    url = f"https://{tenant}.stellarpos.io/supplier-invoices/{asn}/review"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'tenant': tenant,
        'tenant_id': tenant,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        print(f"Fetching {url}...")
        try:
            resp = await client.get(url, headers=headers)
            print(f"Status: {resp.status_code}")
            
            # Save HTML to a file for analysis
            with open("sample_invoice_scrape.html", "w", encoding="utf-8") as f:
                f.write(resp.text)
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Look for script tags with JSON
            scripts = soup.find_all('script')
            print(f"Found {len(scripts)} script tags.")
            
            for i, script in enumerate(scripts):
                if script.string:
                    if 'invoice' in script.string.lower() or 'data' in script.string.lower():
                        print(f"Script {i} might contain data. Length: {len(script.string)}")
                        # Print a snippet
                        # print(script.string[:200])
            
            # Look for common data attributes
            # ...
            
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(probe())
