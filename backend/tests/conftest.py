import os
import sys
import pytest

# Set Auth Bypass BEFORE importing app/auth
os.environ["DISABLE_AUTH"] = "true"
# Set Dummy DB for testing BEFORE importing app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["DB_POOL_DISABLE"] = "true"

# Ensure backend modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app
from database import Base, get_db
import auth # Import auth to patch explicitly if needed

from sqlalchemy.pool import StaticPool

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def db_session():
    # Create tables
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(autouse=True)
def reset_auth_state():
    """Reset auth module variables before every test to prevent pollution."""
    auth.DISABLE_AUTH = True
    auth.AUTH_REQUIRED = False
    auth.AUTH_MODE = "strict"
    # Note: SUPABASE_JWT_SECRET is not reset as it's often not critical for bypass tests
    yield

@pytest.fixture(scope="module")
def client(db_session):
    # Override generic DB dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as c:
        yield c
