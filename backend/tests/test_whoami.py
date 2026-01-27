import pytest
from unittest.mock import patch, AsyncMock
import auth
from fastapi.testclient import TestClient

def test_whoami_no_token_permissive(client):
    """Case 1: no token + AUTH_REQUIRED=false => 200 and authenticated=False"""
    with patch("auth.AUTH_REQUIRED", False), \
         patch("auth.DISABLE_AUTH", False):
        response = client.get("/whoami")
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
        assert data["user_id"] is None
        assert data["auth_required"] is False

def test_whoami_invalid_token_permissive(client):
    """Case 2: invalid token + AUTH_REQUIRED=false => 200 and authenticated=False"""
    with patch("auth.AUTH_REQUIRED", False), \
         patch("auth.DISABLE_AUTH", False), \
         patch("auth.get_jwks", AsyncMock(return_value=None)), \
         patch("auth.SUPABASE_JWT_SECRET", None):
        
        response = client.get("/whoami", headers={"Authorization": "Bearer invalid-token"})
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
        assert data["user_id"] is None

def test_whoami_valid_token_rs256(client):
    """Case 3: valid token => 200 and user_id populated"""
    mock_payload = {
        "sub": "test-user-uuid",
        "email": "test@example.com",
        "org_id": "test-org",
        "iss": f"{auth.SUPABASE_URL}/auth/v1",
        "aud": "authenticated",
        "exp": 9999999999,
        "iat": 1000000000
    }
    
    # We mock at the decode level to avoid complexities of actual RSA key generation in tests
    with patch("auth.AUTH_REQUIRED", True), \
         patch("auth.DISABLE_AUTH", False), \
         patch("auth.get_jwks", AsyncMock(return_value={"keys": [{"kid": "test-kid"}]})), \
         patch("jwt.get_unverified_header", return_value={"kid": "test-kid"}), \
         patch("jwt.decode", return_value=mock_payload), \
         patch("jwt.algorithms.RSAAlgorithm.from_jwk", return_value="mock-pub-key"):
        
        response = client.get("/whoami", headers={"Authorization": "Bearer valid-mock-token"})
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["user_id"] == "test-user-uuid"
        assert data["email"] == "test@example.com"
        assert "claims" in data
        assert data["claims"]["sub"] == "test-user-uuid"

def test_whoami_unauthorized_strict(client):
    """Extra: no token + AUTH_REQUIRED=true => 401"""
    with patch("auth.AUTH_REQUIRED", True), \
         patch("auth.DISABLE_AUTH", False):
        response = client.get("/whoami")
        assert response.status_code == 401
        assert response.json()["detail"] == "Authentication required"
