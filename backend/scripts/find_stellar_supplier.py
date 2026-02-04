import sys
import os
import asyncio
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load env
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(root_dir, ".env"))

from services import stellar_service

async def search(query):
    print(f"Searching Stellar for: '{query}'...")
    try:
        results = await stellar_service.search_stellar_suppliers(query=query)
        print(f"DEBUG: Results type: {type(results)}")
        if isinstance(results, dict):
             print(f"DEBUG: Results keys: {list(results.keys())}")

        # Stellar API returns { "result": [...] }
        if isinstance(results, dict):
            if 'result' in results:
                data = results['result']
            elif 'data' in results:
                data = results['data']
            else:
                data = results
        else:
             data = results

        
        print(f"DEBUG: Data type: {type(data)}")
        if isinstance(data, dict):
             print(f"DEBUG: Data keys: {list(data.keys())}")
             # Maybe the list is inside 'data' again?
             if 'data' in data:
                 data = data['data']
                 print("DEBUG: found nested data key")


        
        print(f"DEBUG: Final data list: {data}")
        
        print(f"Found {len(data)} results:")
        print("-" * 80)
        print(f"{'ID':<10} | {'Name':<40} | {'Contact':<20}")
        print("-" * 80)
        
        for supplier in data:
            s_id = str(supplier.get('id', 'N/A'))
            s_name = supplier.get('name', 'N/A')
            s_contact = supplier.get('contact_name', '')
            print(f"{s_id:<10} | {s_name:<40} | {s_contact:<20}")

            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python find_stellar_supplier.py <vendor_name>")
        sys.exit(1)
    
    query = sys.argv[1]
    asyncio.run(search(query))
