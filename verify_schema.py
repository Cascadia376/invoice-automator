
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Mock database module to avoid import errors if database not reachable
import types
sys.modules['database'] = types.ModuleType('database')
sys.modules['database'].Base = object

try:
    # We need to mock sqlalchemy Base if it's imported in models
    # Actually models imports Base from database.
    # Let's try importing schemas directly first, but schemas imports pydantic.
    # We need to make sure models are importable or just mock them if schemas don't depend on them at runtime for logic.
    # Schemas don't import models?
    # backend/schemas.py imports: pydantic, typing, datetime.
    # It does not import models.
    
    from backend import schemas
    from datetime import datetime
    
    print("Import successful. Verifying Invoice schema...")
    
    # Test instantiation
    issue = schemas.Issue(
        id="issue1",
        organization_id="org1",
        invoice_id="inv1",
        type="breakage",
        status="open",
        resolution_status="pending",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    invoice = schemas.Invoice(
        id="inv1",
        invoice_number="123",
        status="needs_review",
        created_at=datetime.now(),
        line_items=[],
        issues=[issue] # This is what we added
    )
    
    print("Schema verification successful: Invoice accepts 'issues' list.")
    
except Exception as e:
    print(f"Verification Failed: {e}")
    # traceback
    import traceback
    traceback.print_exc()
    sys.exit(1)
