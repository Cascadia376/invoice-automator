import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

async def probe():
    tenant = os.getenv("STELLAR_TENANT_ID") or "cascadialiquor"
    js_bundle = "js/app.75b533c2.js"
    url = f"https://{tenant}.stellarpos.io/{js_bundle}"
    
    # Optional: check chunk-vendors too if needed
    # url = f"https://{tenant}.stellarpos.io/js/chunk-vendors.707aa3c4.js"
    
    print(f"Fetching {url}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            print(f"Status: {resp.status_code}")
            if resp.is_success:
                with open("stellar_app_bundle.js", "w", encoding="utf-8") as f:
                    f.write(resp.text)
                print("Saved bundle to stellar_app_bundle.js")
            else:
                print(f"Failed to fetch bundle: {resp.text[:200]}")
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(probe())
