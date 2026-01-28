import sys
import os

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database import SessionLocal
from models import UserRole, Store, Vendor


def verify_stores():
    db = SessionLocal()
    created_data = False
    
    try:
        # Check if we need to seed data
        if db.query(UserRole).count() == 0:
            print("Seeding test data...")
            # Create a test store
            test_store = Store(store_id=99999, name="Test Store", organization_id="test_org")
            db.merge(test_store) # Use merge to avoid PK conflicts if it exists but role doesn't
            
            # Create a test role
            test_role = UserRole(user_id="test_user", role_id="admin", organization_id="99999")
            db.merge(test_role)
            
            db.commit()
            created_data = True
            print("Test data seeded.")
            
        # Find users with roles
        user_ids = [r.user_id for r in db.query(UserRole).distinct(UserRole.user_id).all()]
        
        print(f"Found {len(user_ids)} users with roles.")
        
        for user_id in user_ids:
            print(f"\nUser: {user_id}")
            # 1. Get roles
            user_roles = db.query(UserRole).filter(UserRole.user_id == user_id).all()
            org_ids = list(set([ur.organization_id for ur in user_roles]))
            print(f"  Org IDs from Roles: {org_ids}")
            
            # 2. Compute Stores (logic from admin.py)
            store_ids = []
            for oid in org_ids:
                try:
                    store_ids.append(int(oid))
                except ValueError:
                    print(f"  WARNING: Non-integer Org ID found: {oid}")
                    pass
            
            stores = db.query(Store).filter(Store.store_id.in_(store_ids)).all()
            print(f"  Stores Found ({len(stores)}):")
            for s in stores:
                print(f"    - {s.name} (ID: {s.store_id})")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if created_data:
            print("Cleaning up test data...")
            db.query(UserRole).filter(UserRole.user_id == "test_user").delete()
            db.query(Store).filter(Store.store_id == 99999).delete()
            db.commit()
        db.close()


if __name__ == "__main__":
    verify_stores()
