import os
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Get DB URL from env, default to SQLite in project root
# Using absolute path to ensure consistency regardless of startup CWD
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
default_db_path = os.path.join(BASE_DIR, "sql_app.db")
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{default_db_path}")

# Robustly clean the URL string
if SQLALCHEMY_DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.strip().strip('"').strip("'")

    if "postgresql" in SQLALCHEMY_DATABASE_URL and "@" in SQLALCHEMY_DATABASE_URL:
        try:
            import urllib.parse
            # Force replace postgres:// with postgresql:// if needed
            if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
                SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)
            
            # Parsing the URL to properly quote the password
            # Format: postgresql://user:password@host:port/dbname
            prefix, rest = SQLALCHEMY_DATABASE_URL.split("://", 1)
            auth_part, host_part = rest.rsplit("@", 1)
            
            if ":" in auth_part:
                user, password = auth_part.split(":", 1)
                # Only quote if not already quoted (heuristic: contains % means likely quoted)
                if "%" not in password:
                    encoded_password = urllib.parse.quote_plus(password)
                    SQLALCHEMY_DATABASE_URL = f"{prefix}://{user}:{encoded_password}@{host_part}"
                    print("DATABASE: Password URL-encoded for safety.")
        except Exception as e:
            print(f"URL parsing warning: {e}")

connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}

# Enforce SSL for Postgres (required by Supabase)
if "postgresql" in SQLALCHEMY_DATABASE_URL and "?" not in SQLALCHEMY_DATABASE_URL:
    SQLALCHEMY_DATABASE_URL += "?sslmode=require"

print(f"DATABASE CONNECTION: {SQLALCHEMY_DATABASE_URL.split('@')[-1] if '@' in SQLALCHEMY_DATABASE_URL else 'sqlite_root'}")
try:
    if "postgresql" in SQLALCHEMY_DATABASE_URL:
        # Extract user/host for debugging (safely, no password)
        # expected: postgresql://user:pass@host:port/db
        prefix_removed = SQLALCHEMY_DATABASE_URL.split("://")[1]
        user_part = prefix_removed.split(":")[0]
        host_part = prefix_removed.split("@")[1].split("/")[0]
        print(f"DEBUG: Attempting to connect to Postgres Host: {host_part}")
        print(f"DEBUG: Connecting as User: {user_part}")
except:
    pass

# Pooling configuration for Render/Supabase stability
# Use NullPool with Supabase Transaction Pooler (port 6543/5432 pooler)
# Client-side pooling is detrimental when using a transaction pooler.
engine_kwargs = {"connect_args": connect_args}
if "postgresql" in SQLALCHEMY_DATABASE_URL:
    engine_kwargs.update({
        "poolclass": NullPool,
        # Remove pool_size/max_overflow/recycle as they don't apply to NullPool
    })

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, **engine_kwargs
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
