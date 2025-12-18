"""
Database migration script to add new columns to invoices table.
Run this once to update the schema.
"""
import os
from sqlalchemy import create_engine, text

# Get DB URL from env
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
default_db_path = os.path.join(BASE_DIR, "sql_app.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{default_db_path}")

# Fix for Render's Postgres URL
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

print(f"DATABASE CONNECTION: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else 'sqlite_root'}")

import models

engine = create_engine(DATABASE_URL, connect_args=connect_args)

def migrate():
    # Ensure all tables exist first
    models.Base.metadata.create_all(bind=engine)
    
    with engine.connect() as conn:
        # 1. Invoices Table Extras
        columns_to_add = [
            ("subtotal", "FLOAT DEFAULT 0.0"),
            ("shipping_amount", "FLOAT DEFAULT 0.0"),
            ("discount_amount", "FLOAT DEFAULT 0.0"),
            ("deposit_amount", "FLOAT DEFAULT 0.0"),
            ("tax_amount", "FLOAT DEFAULT 0.0"),
            ("issue_type", "VARCHAR"),
            ("vendor_id", "VARCHAR REFERENCES vendors(id)"),
            ("raw_extraction_results", "VARCHAR"),
            ("po_number", "VARCHAR")
        ]

        for col_name, col_type in columns_to_add:
            try:
                print(f"Adding {col_name} to invoices...")
                conn.execute(text(f"ALTER TABLE invoices ADD COLUMN {col_name} {col_type}"))
                conn.commit()
            except Exception as e:
                print(f"Note: Could not add {col_name} (likely already exists): {e}")

        # 2. Add organization_id to all relevant tables for multi-tenancy
        tables_to_migrate = [
            "invoices", 
            "line_items", # Added line_items for direct filtering support
            "gl_categories", 
            "sku_category_mappings", 
            "templates",
            "vendors",
            "vendor_field_mappings",
            "vendor_corrections",
            "products",
            "product_orders"
        ]
        
        for table in tables_to_migrate:
            try:
                print(f"Adding organization_id to {table}...")
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN organization_id VARCHAR DEFAULT 'default_org'"))
                conn.execute(text(f"CREATE INDEX ix_{table}_organization_id ON {table} (organization_id)"))
                conn.commit()
            except Exception as e:
                print(f"Note: organization_id might already exist in {table}: {e}")

    
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
