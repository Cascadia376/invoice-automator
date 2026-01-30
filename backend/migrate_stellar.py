"""
Migration: Add Stellar POS integration fields

Adds fields to support Stellar POS integration:
- Vendor: stellar_supplier_id, stellar_supplier_name
- Invoice: stellar_posted_at, stellar_asn_number, stellar_response
- New Table: global_vendor_mappings
"""

from sqlalchemy import text, inspect
import os
from database import engine

if not os.getenv("DATABASE_URL"):
    print("ERROR: DATABASE_URL not set.")
    exit(1)

def migrate():
    """Add Stellar integration fields and tables"""
    
    inspector = inspect(engine)
    
    with engine.connect() as conn:
        # 1. Create global_vendor_mappings table if it doesn't exist
        print("Checking global_vendor_mappings table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS global_vendor_mappings (
                id VARCHAR(255) PRIMARY KEY,
                vendor_name VARCHAR(255) UNIQUE NOT NULL,
                stellar_supplier_id VARCHAR(255) NOT NULL,
                stellar_supplier_name VARCHAR(255) NOT NULL,
                confidence_score FLOAT DEFAULT 1.0,
                usage_count INTEGER DEFAULT 1,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()
        print("✓ Global vendor mappings table check completed")

        # 2. Check vendors table
        print("\nChecking vendors table...")
        columns = [c['name'] for c in inspector.get_columns('vendors')]
        
        vendor_fields = {
            'stellar_supplier_id': 'VARCHAR(255)',
            'stellar_supplier_name': 'VARCHAR(255)'
        }
        
        for field, field_type in vendor_fields.items():
            if field not in columns:
                print(f"Adding {field} to vendors...")
                conn.execute(text(f"ALTER TABLE vendors ADD COLUMN {field} {field_type}"))
                print(f"✓ Added {field}")
            else:
                print(f"- {field} already exists in vendors")
        
        conn.commit()
        
        # Check store table
        print("\nChecking store table...")
        # Note: table name is 'store' based on models.py
        columns = [c['name'] for c in inspector.get_columns('store')]
        
        store_fields = {
            'stellar_tenant': 'VARCHAR(255)',
            'stellar_location_id': 'VARCHAR(255)',
            'stellar_location_name': 'VARCHAR(255)',
            'stellar_enabled': 'BOOLEAN'
        }
        
        for field, field_type in store_fields.items():
            if field not in columns:
                print(f"Adding {field} to store...")
                conn.execute(text(f"ALTER TABLE store ADD COLUMN {field} {field_type}"))
                print(f"✓ Added {field}")
            else:
                print(f"- {field} already exists in store")
        
        conn.commit()
        
        # Check invoices table
        print("\nChecking invoices table...")
        columns = [c['name'] for c in inspector.get_columns('invoices')]
        
        invoice_fields = {
            'stellar_posted_at': 'TIMESTAMP',
            'stellar_asn_number': 'VARCHAR(255)',
            'stellar_response': 'TEXT'
        }
        
        for field, field_type in invoice_fields.items():
            if field not in columns:
                print(f"Adding {field} to invoices...")
                conn.execute(text(f"ALTER TABLE invoices ADD COLUMN {field} {field_type}"))
                print(f"✓ Added {field}")
            else:
                print(f"- {field} already exists in invoices")
        
        conn.commit()
        
        # Create index on ASN number
        print("\nCreating index on stellar_asn_number...")
        try:
            # SQL for index creation is generally similar across DBs, but 
            # we'll catch errors just in case.
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_invoices_stellar_asn 
                ON invoices(stellar_asn_number)
            """))
            conn.commit()
            print("✓ Index check completed")
        except Exception as e:
            print(f"Note on index creation: {e}")
    
    print("\n✅ Stellar migration completed successfully!")

if __name__ == "__main__":
    migrate()
