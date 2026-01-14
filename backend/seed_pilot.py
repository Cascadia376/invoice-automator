import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid

# Add parent directory to path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import Base, Organization, GLCategory
from backend.database import SQLALCHEMY_DATABASE_URL

def seed_pilot():
    print("🚀 Starting Pilot Data Seeding...")
    
    # Database Connection
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # 1. Create Pilot Organization
        org_name = "Liquor Store Pilot"
        existing_org = db.query(Organization).filter(Organization.name == org_name).first()
        
        if existing_org:
            print(f"✅ Organization '{org_name}' already exists. ID: {existing_org.id}")
            org_id = existing_org.id
        else:
            org_id = str(uuid.uuid4())
            new_org = Organization(
                id=org_id,
                name=org_name,
                subscription_status="active",
                created_at=datetime.utcnow()
            )
            db.add(new_org)
            db.commit()
            print(f"✅ Created Organization '{org_name}'. ID: {org_id}")

        # 2. Seed GL Categories
        categories = [
            ("BEER", "Beer & Cider"),
            ("WINE", "Wine"),
            ("LIQUOR", "Spirits & Liquor"),
            ("COOLERS", "Ready to Drink (Coolers)"),
            ("CIDER", "Cider"), # Sometimes separate, key is mapped
            ("TOBACCO", "Tobacco Products"),
            ("LOTTERY", "Lottery"),
            ("MIX & CONFEC", "Mix, Soda, & Confectionary"),
            ("MISC", "Deposits & Freight"), # Deposit/Container often maps here
        ]
        
        print(f"📦 Seeding {len(categories)} GL Categories for Org {org_id}...")
        
        for code, name in categories:
            exists = db.query(GLCategory).filter(
                GLCategory.organization_id == org_id,
                GLCategory.code == code
            ).first()
            
            if not exists:
                new_cat = GLCategory(
                    id=str(uuid.uuid4()),
                    organization_id=org_id,
                    code=code,
                    name=name,
                    full_name=name
                )
                db.add(new_cat)
                print(f"   + Created Category: {code}")
            else:
                print(f"   . Category {code} already exists")
        
        db.commit()
        print("✅ GL Categories seeded successfully.")

        print("\n" + "="*50)
        print("🎉 PILOT SETUP COMPLETE")
        print("="*50)
        print(f"Organization ID: {org_id}")
        print("\nNEXT STEPS for User Onboarding:")
        print("1. Go to Supabase Dashboard -> Authentication -> Users")
        print("2. Find (or create) the Pilot User's email")
        print("3. Edit User -> User Metadata (JSON)")
        print("4. Add the following:")
        print(f'   {{\n     "org_id": "{org_id}",\n     "organization_id": "{org_id}"\n   }}')
        print("="*50)

    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_pilot()
