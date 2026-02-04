import sys
import os
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load env
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(root_dir, ".env"))

from database import SessionLocal
import models

def list_stores():
    db = SessionLocal()
    try:
        stores = db.query(models.Store).all()
        print(f"Found {len(stores)} stores:")
        print("-" * 80)
        print(f"{'ID':<5} | {'Name':<30} | {'Org ID':<15} | {'Enabled':<10} | {'Tenant':<15}")
        print("-" * 80)
        
        for store in stores:
            enabled = str(store.stellar_enabled)
            tenant = str(store.stellar_tenant)
            print(f"{store.store_id:<5} | {store.name:<30} | {store.organization_id:<15} | {enabled:<10} | {tenant:<15}")

    finally:
        db.close()

if __name__ == "__main__":
    list_stores()
