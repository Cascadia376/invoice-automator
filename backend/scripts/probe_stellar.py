import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

async def probe():
    token = os.getenv("STELLAR_API_TOKEN")
    tenant = os.getenv("STELLAR_TENANT_ID") or "cascadialiquor"
    base_url = "https://inventorymanagement.stellarpos.io"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'tenant': tenant,
        'tenant_id': tenant
    }
    
    # Probe around 17066
    for i in range(17060, 17075):
        asn = f"SUPL-INV-2026-{i}"
        url = f"{base_url}/api/supplier-invoices/retrieve/id/{asn}"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers)
                if resp.is_success:
                    data = resp.json()
                    inv_num = data.get('invoice_number') or data.get('supplierInvoiceNumber')
                    print(f"ASN {asn}: OK - Inv# {inv_num}")
                else:
                    print(f"ASN {asn}: Failed {resp.status_code}")
        except Exception as e:
            print(f"ASN {asn}: Error {str(e)}")

if __name__ == "__main__":
    asyncio.run(probe())
