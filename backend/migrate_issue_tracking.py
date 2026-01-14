
import os
from sqlalchemy import create_engine, text
import models

# Get DB URL from env
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
default_db_path = os.path.join(BASE_DIR, "sql_app.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{default_db_path}")

# Fix for Render's Postgres URL
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

print(f"DATABASE CONNECTION: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else 'sqlite_root'}")

engine = create_engine(DATABASE_URL, connect_args=connect_args)

def migrate():
    with engine.connect() as conn:
        # Add columns to line_items
        new_columns = [
            ("issue_type", "VARCHAR"),
            ("issue_status", "VARCHAR DEFAULT 'open'"),
            ("issue_description", "VARCHAR"),
            ("issue_notes", "VARCHAR")
        ]
        
        for col_name, col_type in new_columns:
            try:
                print(f"Adding {col_name} to line_items...")
                conn.execute(text(f"ALTER TABLE line_items ADD COLUMN {col_name} {col_type}"))
                conn.commit()
            except Exception as e:
                print(f"Note: Could not add {col_name} (likely already exists): {e}")
                
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
