import sys
import os
from sqlalchemy.orm import Session
# Ensure backend modules are found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine
from models import Role, Base

def seed_roles():
    db = SessionLocal()
    try:
        roles_to_seed = [
            {"id": "admin", "name": "Administrator", "description": "Full access to all resources"},
            {"id": "manager", "name": "Manager", "description": "Can manage stores and users, but limited system settings"},
            {"id": "staff", "name": "Staff", "description": "Standard access, view-only or limited edit rights"},
        ]

        print("🌱 Seeding Roles...")
        for r_data in roles_to_seed:
            existing = db.query(Role).filter(Role.id == r_data["id"]).first()
            if not existing:
                new_role = Role(**r_data)
                db.add(new_role)
                print(f"   + Created role: {r_data['id']}")
            else:
                print(f"   . Role {r_data['id']} already exists")
        
        db.commit()
        print("✅ Roles seeded successfully!")

    except Exception as e:
        print(f"❌ Error seeding roles: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_roles()
