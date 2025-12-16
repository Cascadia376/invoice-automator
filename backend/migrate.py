"""
Database migration script to add new columns to invoices table.
Run this once to update the schema.
"""
import os
from sqlalchemy import create_engine, text

# Get DB URL from env
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")

# Fix for Render's Postgres URL
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

def migrate():
    with engine.connect() as conn:
        try:
            # Add new columns if they don't exist
            print("Adding subtotal column...")
            conn.execute(text("ALTER TABLE invoices ADD COLUMN subtotal FLOAT DEFAULT 0.0"))
            conn.commit()
        except Exception as e:
            print(f"subtotal column might already exist or error: {e}")
        
        try:
            print("Adding shipping_amount column...")
            conn.execute(text("ALTER TABLE invoices ADD COLUMN shipping_amount FLOAT DEFAULT 0.0"))
            conn.commit()
        except Exception as e:
            print(f"shipping_amount column might already exist or error: {e}")
        
        try:
            print("Adding discount_amount column...")
            conn.execute(text("ALTER TABLE invoices ADD COLUMN discount_amount FLOAT DEFAULT 0.0"))
            conn.commit()
        except Exception as e:
            print(f"discount_amount column might already exist or error: {e}")
        
        try:
            print("Adding deposit_amount column...")
            conn.execute(text("ALTER TABLE invoices ADD COLUMN deposit_amount FLOAT DEFAULT 0.0"))
            conn.commit()
        except Exception as e:
            print(f"deposit_amount column might already exist or error: {e}")

        # Multi-tenancy migrations
        tables_to_migrate = [
            "invoices", 
            "gl_categories", 
            "sku_category_mappings", 
            "qbo_credentials", 
            "templates"
        ]
        
        for table in tables_to_migrate:
            try:
                print(f"Adding organization_id to {table}...")
                # Add as nullable first or with default to handle existing rows
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN organization_id VARCHAR DEFAULT 'default_org'"))
                conn.execute(text(f"CREATE INDEX ix_{table}_organization_id ON {table} (organization_id)"))
                conn.commit()
            except Exception as e:
                print(f"organization_id column might already exist in {table} or error: {e}")

    
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
