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
    # models.Base.metadata.create_all(bind=engine)
    
    with engine.connect() as conn:
        print("Starting consolidated migration...")

        # 1. NEW TABLES (from various migration scripts)
        # We manually create some to ensure specific constraints if metadata.create_all isn't enough or clear
        
        # gl_categories
        try:
            print("Creating gl_categories table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS gl_categories (
                    id VARCHAR PRIMARY KEY,
                    organization_id VARCHAR DEFAULT 'dev-org',
                    code VARCHAR NOT NULL,
                    name VARCHAR NOT NULL,
                    full_name VARCHAR NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
        except Exception as e:
            print(f"Note: gl_categories table creation: {e}")

        # sku_category_mappings
        try:
            print("Creating sku_category_mappings table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sku_category_mappings (
                    id VARCHAR PRIMARY KEY,
                    organization_id VARCHAR DEFAULT 'dev-org',
                    sku VARCHAR NOT NULL,
                    category_gl_code VARCHAR NOT NULL,
                    usage_count INTEGER DEFAULT 1,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sku_mappings_sku ON sku_category_mappings(sku)"))
            conn.commit()
        except Exception as e:
            print(f"Note: sku_category_mappings table creation: {e}")

        # issues
        try:
            print("Creating issues table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS issues (
                    id VARCHAR PRIMARY KEY,
                    organization_id VARCHAR NOT NULL,
                    invoice_id VARCHAR NOT NULL,
                    vendor_id VARCHAR,
                    type VARCHAR,
                    status VARCHAR DEFAULT 'open',
                    description VARCHAR,
                    resolution_type VARCHAR,
                    resolution_status VARCHAR DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP,
                    FOREIGN KEY (invoice_id) REFERENCES invoices(id),
                    FOREIGN KEY (vendor_id) REFERENCES vendors(id)
                )
            """))
            conn.commit()
        except Exception as e:
            print(f"Note: issues table creation: {e}")

        # issue_communications
        try:
            print("Creating issue_communications table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS issue_communications (
                    id VARCHAR PRIMARY KEY,
                    issue_id VARCHAR NOT NULL,
                    organization_id VARCHAR NOT NULL,
                    type VARCHAR,
                    content VARCHAR,
                    recipient VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR,
                    FOREIGN KEY (issue_id) REFERENCES issues(id)
                )
            """))
            conn.commit()
        except Exception as e:
            print(f"Note: issue_communications table creation: {e}")

        # issue_line_items (Association)
        try:
            print("Creating issue_line_items table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS issue_line_items (
                    issue_id VARCHAR NOT NULL,
                    line_item_id VARCHAR NOT NULL,
                    PRIMARY KEY (issue_id, line_item_id),
                    FOREIGN KEY (issue_id) REFERENCES issues(id),
                    FOREIGN KEY (line_item_id) REFERENCES line_items(id)
                )
            """))
            conn.commit()
        except Exception as e:
            print(f"Note: issue_line_items table creation: {e}")

        # 2. COLUMN ADDITIONS
        
        # Invoices Table Extras
        invoice_columns = [
            ("subtotal", "FLOAT DEFAULT 0.0"),
            ("shipping_amount", "FLOAT DEFAULT 0.0"),
            ("discount_amount", "FLOAT DEFAULT 0.0"),
            ("deposit_amount", "FLOAT DEFAULT 0.0"),
            ("tax_amount", "FLOAT DEFAULT 0.0"),
            ("issue_type", "VARCHAR"),
            ("vendor_id", "VARCHAR REFERENCES vendors(id)"),
            ("raw_extraction_results", "VARCHAR"),
            ("po_number", "VARCHAR"),
            ("ldb_report_url", "VARCHAR"),
            ("is_posted", "BOOLEAN DEFAULT FALSE")
        ]

        for col_name, col_type in invoice_columns:
            try:
                print(f"Checking {col_name} in invoices...")
                conn.execute(text(f"ALTER TABLE invoices ADD COLUMN {col_name} {col_type}"))
                conn.commit()
            except Exception as e:
                pass # Already exists or constraint issue

        # Line Items Table Extras
        line_item_columns = [
            ("sku", "VARCHAR"),
            ("units_per_case", "FLOAT DEFAULT 1.0"),
            ("cases", "FLOAT DEFAULT 0.0"),
            ("category_gl_code", "VARCHAR"),
            ("confidence_score", "FLOAT DEFAULT 1.0"),
            ("case_cost", "FLOAT"),
            ("issue_type", "VARCHAR"),
            ("issue_status", "VARCHAR DEFAULT 'open'"),
            ("issue_description", "VARCHAR"),
            ("issue_notes", "VARCHAR")
        ]
        
        for col_name, col_type in line_item_columns:
            try:
                print(f"Checking {col_name} in line_items...")
                conn.execute(text(f"ALTER TABLE line_items ADD COLUMN {col_name} {col_type}"))
                conn.commit()
            except Exception as e:
                pass

        # Renames (Line Items)
        try:
            print("Checking for unit_price -> unit_cost rename...")
            conn.execute(text("ALTER TABLE line_items RENAME COLUMN unit_price TO unit_cost"))
            conn.commit()
        except Exception as e:
            pass

        # 3. Add organization_id to all relevant tables (Safe multisubs support)
        tables_to_migrate = [
            "invoices", 
            "line_items",
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
                print(f"Updating organization_id in {table}...")
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN organization_id VARCHAR DEFAULT 'dev-org'"))
                conn.commit()
            except Exception as e:
                pass
            
            try:
                conn.execute(text(f"UPDATE {table} SET organization_id = 'dev-org' WHERE organization_id = 'default_org' OR organization_id IS NULL"))
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{table}_organization_id ON {table} (organization_id)"))
                conn.commit()
            except Exception as e:
                pass

    print("Consolidated Migration complete!")

if __name__ == "__main__":
    migrate()
