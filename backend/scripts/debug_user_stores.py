import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import models
from database import get_db

USER_ID = 'a9d96a82-3428-4347-8cdf-83f7a9498889'

def debug_stores():
    # Setup DB
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL not set")
        return

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        print(f"DEBUG: Querying roles for user {USER_ID}")
        
        # 1. Get user roles
        user_roles = db.query(models.UserRole).filter(
            models.UserRole.user_id == USER_ID
        ).all()
        
        print(f"DEBUG: Found {len(user_roles)} roles")
        for ur in user_roles:
            print(f" - Role: {ur.role_id} for Org: {ur.organization_id} (Type: {type(ur.organization_id)})")
            
        org_ids = list(set([ur.organization_id for ur in user_roles]))
        print(f"DEBUG: Unique Org IDs: {org_ids}")
        
        # 2. Fetch Stores
        print("DEBUG: Querying stores with organization_id IN list")
        stores = db.query(models.Store).filter(
            models.Store.organization_id.in_(org_ids)
        ).all()
        
        print(f"DEBUG: Found {len(stores)} stores")
        for s in stores:
            print(f" - Store: {s.name} (ID: {s.store_id}, OrgID: {s.organization_id})")
            
    finally:
        db.close()

if __name__ == "__main__":
    debug_stores()
