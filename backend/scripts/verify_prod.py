import os
import sys
from sqlalchemy import create_engine, text, inspect
import boto3
from openai import OpenAI

def check_env():
    print("=== Checking Environment Variables ===")
    vars_to_check = [
        "DATABASE_URL",
        "OPENAI_API_KEY",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_BUCKET_NAME",
        "SUPABASE_URL",
        "SUPABASE_KEY"
    ]
    all_ok = True
    for v in vars_to_check:
        val = os.getenv(v)
        if val:
            # Mask sensitive info
            masked = val[:5] + "..." + val[-5:] if len(val) > 10 else "***"
            print(f"✅ {v}: FOUND ({masked})")
        else:
            print(f"❌ {v}: MISSING")
            all_ok = False
    return all_ok

def check_db():
    print("\n=== Checking Database Schema ===")
    url = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
        
    try:
        engine = create_engine(url)
        inspector = inspect(engine)
        
        tables = inspector.get_table_names()
        print(f"Found tables: {', '.join(tables)}")
        
        # Check critical table: invoices
        if "invoices" in tables:
            columns = [c['name'] for c in inspector.get_columns("invoices")]
            required = ["organization_id", "po_number", "vendor_id", "raw_extraction_results"]
            print(f"Invoices columns: {len(columns)}")
            for req in required:
                if req in columns:
                    print(f"  ✅ Column '{req}': OK")
                else:
                    print(f"  ❌ Column '{req}': MISSING")
        else:
            print("❌ Table 'invoices' NOT FOUND")
            
        # Check critical table: products
        if "products" in tables:
            print("✅ Table 'products': OK")
        else:
            print("❌ Table 'products': MISSING")
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

if __name__ == "__main__":
    check_env()
    check_db()
