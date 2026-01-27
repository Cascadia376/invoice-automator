import pytest
from fastapi.testclient import TestClient
import auth

def test_strict_mode_blocks_requests(client):
    # Set to strict mode
    auth.AUTH_REQUIRED = True
    auth.AUTH_MODE = "strict"
    auth.DISABLE_AUTH = False
    
    # Request without token
    response = client.get("/api/vendors")
    assert response.status_code == 401
    assert "Authentication required" in response.json()["detail"]

def test_log_only_mode_allows_requests(client):
    # Set to log-only mode
    auth.AUTH_REQUIRED = False
    auth.AUTH_MODE = "log-only"
    auth.DISABLE_AUTH = False
    
    # Request without token should succeed with anon fallback
    response = client.get("/api/vendors")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_disabled_mode_allows_requests(client):
    # Set to disabled mode
    auth.AUTH_REQUIRED = False
    auth.AUTH_MODE = "disabled"
    auth.DISABLE_AUTH = True # This is the real bypass
    
    # Request without token should succeed with dev bypass
    response = client.get("/api/vendors")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_role_check_bypass_in_log_only(client):
    # Set to log-only
    auth.AUTH_REQUIRED = False
    auth.AUTH_MODE = "log-only"
    auth.DISABLE_AUTH = False
    
    # Access an admin-only route
    response = client.get("/api/admin/organizations")
    assert response.status_code == 200
