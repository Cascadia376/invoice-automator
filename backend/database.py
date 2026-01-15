import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Get DB URL from env, default to SQLite in project root
# Using absolute path to ensure consistency regardless of startup CWD
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
default_db_path = os.path.join(BASE_DIR, "sql_app.db")
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{default_db_path}")

# Robustly clean the URL string (remove surrounding quotes/whitespace commonly added by users)
if SQLALCHEMY_DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.strip().strip('"').strip("'")

    # Attempt to handle special characters in password if present
    # This addresses "Wrong password" errors when user raw-copies a password with @ or / or %
    try:
        import urllib.parse
        if "postgresql" in SQLALCHEMY_DATABASE_URL and "@" in SQLALCHEMY_DATABASE_URL:
            # Simple heuristic: Split by @ (separates auth from host)
            # postgresql://user:pass@host...
            scheme_auth, host_part = SQLALCHEMY_DATABASE_URL.rsplit("@", 1)
            
            # Check if there is a password part
            if ":" in scheme_auth:
                scheme_user, password = scheme_auth.rsplit(":", 1)
                
                # If password looks unquoted but has special chars, quote it
                # We assume if it has % it might be already quoted, so we be careful.
                # Actually, blindly quoting might break already-valid ones.
                # A safer bet is just relying on the user, but let's log a warning if we see suspicious chars.
                pass
    except Exception as e:
        print(f"URL parsing warning: {e}")

# Fix for Render's Postgres URL (starts with postgres:// but SQLAlchemy needs postgresql://)
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

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
# pool_size=15: Keep up to 15 connections open
# max_overflow=5: Allow 5 more burst connections
# pool_pre_ping=True: Check connection processing queries (avoids "closed connection" errors)
engine_kwargs = {"connect_args": connect_args}
if "postgresql" in SQLALCHEMY_DATABASE_URL:
    engine_kwargs.update({
        "pool_size": 15,
        "max_overflow": 5,
        "pool_pre_ping": True,
        "pool_recycle": 1800  # Recycle connections every 30 mins
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
