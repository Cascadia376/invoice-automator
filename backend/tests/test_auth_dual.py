import pytest
import jwt
import auth
from fastapi.testclient import TestClient
from unittest.mock import patch

def test_whoami_unauthenticated(client):
    auth.AUTH_REQUIRED = False
    auth.DISABLE_AUTH = False  # Ensure bypass is off
    response = client.get("/api/auth/whoami")
    assert response.status_code == 200
    assert response.json()["authenticated"] is False

def test_hs256_fallback_success(client):
    # Setup legacy secret
    auth.SUPABASE_JWT_SECRET = "legacy-secret"
    auth.AUTH_REQUIRED = True
    
    with patch("auth.DISABLE_AUTH", False):
        # Create HS256 token
        token = jwt.encode(
            {"sub": "user-123", "email": "test@example.com", "aud": "authenticated"},
            "legacy-secret",
            algorithm="HS256"
        )
        
        response = client.get("/api/auth/whoami", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["user_id"] == "user-123"
        assert response.json()["authenticated"] is True

def test_auth_required_blocks_missing(client):
    auth.AUTH_REQUIRED = True
    auth.DISABLE_AUTH = False  # Ensure bypass is off
    response = client.get("/api/auth/whoami")
    assert response.status_code == 401
    assert "Authentication required" in response.json()["detail"]

def test_invalid_token_blocks_in_strict(client):
    auth.AUTH_REQUIRED = True
    auth.DISABLE_AUTH = False  # Ensure bypass is off
    auth.SUPABASE_JWT_SECRET = "secret"
    
    response = client.get("/api/auth/whoami", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401

def test_invalid_token_allows_in_log_only(client):
    auth.AUTH_REQUIRED = False
    auth.DISABLE_AUTH = False  # Ensure bypass is off
    auth.SUPABASE_JWT_SECRET = "secret"
    
    response = client.get("/api/auth/whoami", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 200
    assert response.json()["authenticated"] is False
