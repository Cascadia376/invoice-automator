import os
from sqlalchemy import create_engine

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Get DB URL from env
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

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

connect_args = {}

# Enforce SSL for Postgres (required by Supabase)
if "postgresql" in SQLALCHEMY_DATABASE_URL and "?" not in SQLALCHEMY_DATABASE_URL:
    SQLALCHEMY_DATABASE_URL += "?sslmode=require"

print(f"DATABASE CONNECTION: {SQLALCHEMY_DATABASE_URL.split('@')[-1] if '@' in SQLALCHEMY_DATABASE_URL else 'postgres'}")
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
# Use QueuePool with strict limits to prevent "Max client connections reached"
# Default to 5 connections, with up to 10 overflow.
pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))

engine_kwargs = {"connect_args": connect_args}

if "postgresql" in SQLALCHEMY_DATABASE_URL:
    engine_kwargs.update({
        "pool_size": pool_size,
        "max_overflow": max_overflow,
        "pool_recycle": 300,  # Recycle connections every 5 minutes
        "pool_pre_ping": True, # CPing connection before use (catch stale ones)
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
