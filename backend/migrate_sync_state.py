"""
Migration script to add sync_states table.
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

engine = create_engine(DATABASE_URL, connect_args=connect_args)

def migrate():
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if "sync_states" not in existing_tables:
        print("Creating sync_states table...")
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE sync_states (
                    id VARCHAR PRIMARY KEY,
                    organization_id VARCHAR,
                    delta_token VARCHAR,
                    last_sync_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sync_states_organization_id ON sync_states (organization_id)"))
            conn.commit()
        print("sync_states table created.")
    else:
        print("sync_states table already exists.")

if __name__ == "__main__":
    migrate()
