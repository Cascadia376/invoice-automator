"""
Migration script to add ldb_report_url to invoices table.
"""
import os
from sqlalchemy import create_engine, text

# Get DB URL from env
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
default_db_path = os.path.join(BASE_DIR, "sql_app.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{default_db_path}")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
print(f"DATABASE CONNECTION: {DATABASE_URL}")

engine = create_engine(DATABASE_URL, connect_args=connect_args)

def migrate():
    with engine.connect() as conn:
        try:
            print("Adding ldb_report_url to invoices...")
            conn.execute(text("ALTER TABLE invoices ADD COLUMN ldb_report_url VARCHAR"))
            conn.commit()
            print("Migration successful.")
        except Exception as e:
            print(f"Migration failed (column likely exists): {e}")

if __name__ == "__main__":
    migrate()
