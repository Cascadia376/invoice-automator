import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def test_endpoints():
    token = os.getenv("STELLAR_API_TOKEN")
    tenant = os.getenv("STELLAR_TENANT_ID") or "cascadiabc" # fallback for testing
    base_url = os.getenv("STELLAR_BASE_URL", "https://stock-import.stellarpos.io")
    
    if not token:
        print("Error: STELLAR_API_TOKEN not found in environment.")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "tenant": tenant,
        "tenant_id": tenant
    }
    
    # Common REST endpoints to try
    endpoints = [
        "/api/suppliers",
        "/api/stock/suppliers",
        "/api/v1/suppliers",
        "/api/locations",
        "/api/stock/locations"
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for ep in endpoints:
            url = f"{base_url}{ep}"
            print(f"Testing {url}...")
            try:
                resp = await client.get(url, headers=headers)
                print(f"  Status: {resp.status_code}")
                if resp.is_success:
                    data = resp.json()
                    print(f"  Success! Found {len(data) if isinstance(data, list) else 'data'}")
                    # print(json.dumps(data, indent=2)[:500])
            except Exception as e:
                print(f"  Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_endpoints())
