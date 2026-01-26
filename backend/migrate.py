"""
Database migration script to add new columns to invoices table.
Run this once to update the schema.
"""
import os
from sqlalchemy import create_engine, text, inspect

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
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    with engine.connect() as conn:
        print("Starting consolidated migration...")

        # 1. NEW TABLES 
        
        # gl_categories
        if "gl_categories" not in existing_tables:
            print("Creating gl_categories table...")
            conn.execute(text("""
                CREATE TABLE gl_categories (
                    id VARCHAR PRIMARY KEY,
                    organization_id VARCHAR DEFAULT 'dev-org',
                    code VARCHAR NOT NULL,
                    name VARCHAR NOT NULL,
                    full_name VARCHAR NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
        
        # sku_category_mappings
        if "sku_category_mappings" not in existing_tables:
            print("Creating sku_category_mappings table...")
            conn.execute(text("""
                CREATE TABLE sku_category_mappings (
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

        # issues
        if "issues" not in existing_tables:
            print("Creating issues table...")
            conn.execute(text("""
                CREATE TABLE issues (
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

        # issue_communications
        if "issue_communications" not in existing_tables:
            print("Creating issue_communications table...")
            conn.execute(text("""
                CREATE TABLE issue_communications (
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

        # issue_line_items (Association)
        if "issue_line_items" not in existing_tables:
            print("Creating issue_line_items table...")
            conn.execute(text("""
                CREATE TABLE issue_line_items (
                    issue_id VARCHAR NOT NULL,
                    line_item_id VARCHAR NOT NULL,
                    PRIMARY KEY (issue_id, line_item_id),
                    FOREIGN KEY (issue_id) REFERENCES issues(id),
                    FOREIGN KEY (line_item_id) REFERENCES line_items(id)
                )
            """))
            conn.commit()

        # 2. COLUMN ADDITIONS
        
        def safe_add_column(table_name, col_name, col_type):
            # Refresh inspector columns
            columns = [c["name"] for c in inspect(engine).get_columns(table_name)]
            if col_name not in columns:
                print(f"Adding {col_name} to {table_name}...")
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"))
                conn.commit()
        
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
            ("is_posted", "BOOLEAN DEFAULT FALSE"),
            ("organization_id", "VARCHAR DEFAULT 'dev-org'") # Ensure this is here
        ]

        if "invoices" in existing_tables:
            for col, dtype in invoice_columns:
                safe_add_column("invoices", col, dtype)

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
            ("issue_notes", "VARCHAR"),
            ("organization_id", "VARCHAR DEFAULT 'dev-org'") # Ensure this is here
        ]
        
        if "line_items" in existing_tables:
            for col, dtype in line_item_columns:
                safe_add_column("line_items", col, dtype)

        # Renames (Line Items)
        if "line_items" in existing_tables:
            li_cols = [c["name"] for c in inspect(engine).get_columns("line_items")]
            if "unit_price" in li_cols and "unit_cost" not in li_cols:
                print("Renaming unit_price -> unit_cost in line_items...")
                conn.execute(text("ALTER TABLE line_items RENAME COLUMN unit_price TO unit_cost"))
                conn.commit()

        # 3. Add organization_id to all relevant tables (Safe multisubs support)
        # We already handled invoices and line_items above, but let's do the others locally
        tables_to_migrate = [
            # "invoices", "line_items", # Done above
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
            if table in existing_tables:
                safe_add_column(table, "organization_id", "VARCHAR DEFAULT 'dev-org'")
                
                # Backfill and Index
                try:
                    conn.execute(text(f"UPDATE {table} SET organization_id = 'dev-org' WHERE organization_id = 'default_org' OR organization_id IS NULL"))
                    conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{table}_organization_id ON {table} (organization_id)"))
                    conn.commit()
                except Exception as e:
                    print(f"Index/Update warning on {table}: {e}")
                    conn.rollback()

    print("Consolidated Migration complete!")

if __name__ == "__main__":
    migrate()
