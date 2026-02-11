
import os
import sys
import asyncio

# Setup pathing for backend imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, 'backend'))

# Mock env vars if needed
if not os.getenv("STELLAR_BASE_URL"):
    os.environ["STELLAR_BASE_URL"] = "https://inventorymanagement.stellarpos.io"

from backend.services import stellar_service
import models

# Setup DB connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL not set")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

async def main():
    print("Searching for 'Container'...")
    results = await stellar_service.search_stellar_suppliers(query="Container", tenant_id="os_8_1")
    print(f"Found {len(results)} matches for 'Container':")
    for r in results:
        print(f"  - {r.get('name')} (ID: {r.get('id')}) Type: {r.get('supplier_type')}")

    print("\nSearching for 'Import'...")
    results = await stellar_service.search_stellar_suppliers(query="Import", tenant_id="os_8_1")
    print(f"Found {len(results)} matches for 'Import':")
    for r in results:
        print(f"  - {r.get('name')} (ID: {r.get('id')}) Type: {r.get('supplier_type')}")
        
    print("\nSearching for 'LDB'...")
    results = await stellar_service.search_stellar_suppliers(query="LDB", tenant_id="os_8_1")
    print(f"Found {len(results)} matches for 'LDB':")
    for r in results:
        print(f"  - {r.get('name')} (ID: {r.get('id')}) Type: {r.get('supplier_type')}")

if __name__ == "__main__":
    # Mock env vars if needed
    # os.environ['STELLAR_API_TOKEN'] = '...' # Already in env hopefully
    asyncio.run(main())
