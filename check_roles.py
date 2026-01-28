import sys
import os
# Add root directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from backend.database import SessionLocal
from backend.models import Role

db = SessionLocal()
try:
    roles = db.query(Role).all()
    print("ROLES IN DB:")
    for r in roles:
        print(f"- {r.id}: {r.name} ({r.description})")
    if not roles:
        print("No roles found in DB!")
except Exception as e:
    print(e)
finally:
    db.close()
