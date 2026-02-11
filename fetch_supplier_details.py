
import os
import sys
import asyncio
import json

# Setup pathing for backend imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, 'backend'))

# Add backend directory to sys.path specifically for internal imports like 'models'
sys.path.append(os.path.join(BASE_DIR, 'backend'))

from backend.services import stellar_service

async def main():
    print("Searching for 'Container World' in Stellar...")
    try:
        # Search for the supplier
        results = await stellar_service.search_stellar_suppliers(query="Container World", tenant_id="os_8_1")
        
        # Normalize result structure
        items = []
        if isinstance(results, dict):
            items = results.get('result', []) or results.get('data', []) or []
        elif isinstance(results, list):
            items = results
            
        print(f"Found {len(items)} matches.")
        for item in items:
            print("\n--- Supplier Details ---")
            print(json.dumps(item, indent=2))
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
