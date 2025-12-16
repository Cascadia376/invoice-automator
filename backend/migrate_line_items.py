"""
Database migration script for line item redesign.
Adds new columns to line_items table and creates new tables for GL categories and SKU mappings.
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
        print("=== Migrating line_items table ===")
        
        # Add new columns to line_items
        columns_to_add = [
            ("sku", "VARCHAR"),
            ("units_per_case", "FLOAT DEFAULT 1.0"),
            ("cases", "FLOAT DEFAULT 0.0"),
            ("category_gl_code", "VARCHAR"),
            ("confidence_score", "FLOAT DEFAULT 1.0")
        ]

        for col_name, col_type in columns_to_add:
            try:
                print(f"Adding {col_name} column...")
                conn.execute(text(f"ALTER TABLE line_items ADD COLUMN {col_name} {col_type}"))
                conn.commit()
            except Exception as e:
                # Check if error is because column exists
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"Column {col_name} already exists.")
                else:
                    print(f"Error adding {col_name}: {e}")
        
        try:
            print("Renaming unit_price to unit_cost...")
            conn.execute(text("ALTER TABLE line_items RENAME COLUMN unit_price TO unit_cost"))
            conn.commit()
        except Exception as e:
            if "does not exist" in str(e).lower():
                print("Column unit_price does not exist (maybe already renamed).")
            else:
                print(f"Error renaming unit_price: {e}")
        
        print("\n=== Creating gl_categories table ===")
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS gl_categories (
                    id VARCHAR PRIMARY KEY,
                    code VARCHAR UNIQUE NOT NULL,
                    name VARCHAR NOT NULL,
                    full_name VARCHAR NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            print("gl_categories table created successfully")
        except Exception as e:
            print(f"Error creating gl_categories table: {e}")
        
        print("\n=== Creating sku_category_mappings table ===")
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sku_category_mappings (
                    id VARCHAR PRIMARY KEY,
                    sku VARCHAR NOT NULL,
                    category_gl_code VARCHAR NOT NULL,
                    usage_count INTEGER DEFAULT 1,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            print("sku_category_mappings table created successfully")
        except Exception as e:
            print(f"Error creating sku_category_mappings table: {e}")
        
        # Create index on sku for faster lookups
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_sku_mappings_sku ON sku_category_mappings(sku)"))
            conn.commit()
            print("Created index on sku column")
        except Exception as e:
            print(f"Error creating index: {e}")
    
    print("\n=== Migration complete! ===")

if __name__ == "__main__":
    migrate()
