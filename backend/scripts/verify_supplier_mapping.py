
import asyncio
import os
import sys
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Load .env w/ python-dotenv
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(dotenv_path):
    print(f"Loading .env from {dotenv_path}")
    load_dotenv(dotenv_path)

from models import Base, Vendor, GlobalVendorMapping
from services import stellar_service

# Setup DB connection
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db") # Default or from env
# Assuming we can connect to the dev DB or a local one.
# For safety in this environment, I'll try to connect to the actual DB if env is set, 
# otherwise I might need to mock or use a test DB. 
# Given the user's environment, let's assume we can use the main DB but be careful with data.

from database import SessionLocal

async def test_mapping():
    db = SessionLocal()
    
    test_id = str(uuid.uuid4())
    vendor_name = f"Test Vendor {test_id}"
    mapped_name = f"Mapped Vendor {test_id}"
    mapped_id = f"stellar_{test_id}"
    
    try:
        # 1. Create a Vendor (unmapped)
        print(f"Creating test vendor: {vendor_name}")
        vendor = Vendor(
            id=test_id,
            organization_id="test_org",
            name=vendor_name
        )
        db.add(vendor)
        db.commit()
        
        # 2. Create a Global Mapping
        print(f"Creating global mapping: {vendor_name} -> {mapped_name}")
        mapping = GlobalVendorMapping(
            id=str(uuid.uuid4()),
            vendor_name=vendor_name,
            stellar_supplier_id=mapped_id,
            stellar_supplier_name=mapped_name
        )
        db.add(mapping)
        db.commit()
        
        # 3. refetch vendor
        db.refresh(vendor)
        assert vendor.stellar_supplier_id is None
        
        # 4. Run ensure_vendor_mapping
        print("Running ensure_vendor_mapping...")
        result_id = await stellar_service.ensure_vendor_mapping(db, vendor)
        
        # 5. Verify
        print(f"Result ID: {result_id}")
        assert result_id == mapped_id
        
        db.refresh(vendor)
        print(f"Vendor Stellar ID: {vendor.stellar_supplier_id}")
        print(f"Vendor Stellar Name: {vendor.stellar_supplier_name}")
        
        assert vendor.stellar_supplier_id == mapped_id
        assert vendor.stellar_supplier_name == mapped_name
        
        print("SUCCESS: Mapping logic verified!")
        
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        print("Cleaning up...")
        try:
            db.query(GlobalVendorMapping).filter(GlobalVendorMapping.vendor_name == vendor_name).delete()
            db.query(Vendor).filter(Vendor.id == test_id).delete()
            db.commit()
        except:
            pass
        db.close()

if __name__ == "__main__":
    asyncio.run(test_mapping())
