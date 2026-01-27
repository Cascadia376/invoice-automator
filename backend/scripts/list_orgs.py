import sys
import os

# Add parent directory to path to import backend modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database import SessionLocal
from models import Organization

def list_orgs():
    db = SessionLocal()
    try:
        orgs = db.query(Organization).all()
        print(f"Found {len(orgs)} organizations:")
        for org in orgs:
            print(f"- {org.name} (ID: {org.id})")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    list_orgs()
