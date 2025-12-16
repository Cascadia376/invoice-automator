"""
Migration script to add deposit_amount column to invoices table.
Run this on Render after deploying the model change.
"""
import os
import sys
from sqlalchemy import create_engine, text

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set")
    sys.exit(1)

# Create engine
engine = create_engine(DATABASE_URL)

print("Adding deposit_amount column to invoices table...")

try:
    with engine.connect() as conn:
        # Add column with default value
        conn.execute(text("""
            ALTER TABLE invoices 
            ADD COLUMN IF NOT EXISTS deposit_amount FLOAT DEFAULT 0.0
        """))
        conn.commit()
        print("✅ Successfully added deposit_amount column")
except Exception as e:
    print(f"❌ Migration failed: {e}")
    sys.exit(1)

print("Migration complete!")
