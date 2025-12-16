"""
Migration script to create vendor management tables.
Run this on Render after deploying the model changes.
"""
import os
import sys
from sqlalchemy import create_engine, text

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set")
    sys.exit(1)

# Fix for Render's Postgres URL
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine
engine = create_engine(DATABASE_URL)

print("Creating vendor management tables...")

try:
    with engine.connect() as conn:
        # Create vendors table
        print("Creating vendors table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS vendors (
                id VARCHAR PRIMARY KEY,
                organization_id VARCHAR NOT NULL,
                name VARCHAR NOT NULL,
                aliases TEXT,
                default_gl_category VARCHAR,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_vendors_org ON vendors(organization_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_vendors_name ON vendors(name)"))
        
        # Create vendor_field_mappings table
        print("Creating vendor_field_mappings table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS vendor_field_mappings (
                id VARCHAR PRIMARY KEY,
                vendor_id VARCHAR REFERENCES vendors(id) ON DELETE CASCADE,
                organization_id VARCHAR NOT NULL,
                field_name VARCHAR NOT NULL,
                textract_field VARCHAR NOT NULL,
                confidence FLOAT DEFAULT 1.0,
                usage_count INTEGER DEFAULT 1,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_vendor_mappings_vendor ON vendor_field_mappings(vendor_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_vendor_mappings_org ON vendor_field_mappings(organization_id)"))
        
        # Create vendor_corrections table
        print("Creating vendor_corrections table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS vendor_corrections (
                id VARCHAR PRIMARY KEY,
                vendor_id VARCHAR REFERENCES vendors(id) ON DELETE CASCADE,
                organization_id VARCHAR NOT NULL,
                invoice_id VARCHAR REFERENCES invoices(id) ON DELETE CASCADE,
                field_name VARCHAR NOT NULL,
                original_value TEXT,
                corrected_value TEXT,
                correction_type VARCHAR NOT NULL,
                rule TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_vendor_corrections_vendor ON vendor_corrections(vendor_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_vendor_corrections_org ON vendor_corrections(organization_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_vendor_corrections_invoice ON vendor_corrections(invoice_id)"))
        
        conn.commit()
        print("✅ Successfully created vendor management tables")
except Exception as e:
    print(f"❌ Migration failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("Migration complete!")
