import os
import jwt
import requests
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jwt import PyJWKClient

class UserContext(BaseModel):
    user_id: str
    org_id: str
    email: Optional[str] = None

security = HTTPBearer(auto_error=False)

# --- Configuration ---
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
SUPABASE_JWT_AUD = os.getenv("SUPABASE_JWT_AUD", "authenticated")
DISABLE_AUTH = os.getenv("DISABLE_AUTH", "").lower() == "true"

# Backward compatibility and Rollout flags
AUTH_MODE = os.getenv("AUTH_MODE", "strict").lower()
AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "false").lower() == "true"

# Respect legacy AUTH_MODE if AUTH_REQUIRED is not set
if AUTH_MODE == "strict" and "AUTH_REQUIRED" not in os.environ:
    AUTH_REQUIRED = True

# JWKS Setup
JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json" if SUPABASE_URL else None
jwks_client = PyJWKClient(JWKS_URL) if JWKS_URL else None

# Fallback for log-only mode to avoid 500s in routers expecting ctx.org_id
LOG_ONLY_FALLBACK = UserContext(user_id="anon-user", org_id="anon-org", email="anon@example.com")

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None)
) -> Optional[UserContext]:
    """
    Authenticated user context. 
    Supports dual verification: RS256 (JWKS) first, then fallback to HS256 (Secret).
    """
    # 1. Bypass logic (Local Dev / Emergency)
    if DISABLE_AUTH:
        return UserContext(user_id="dev-user", org_id="dev-org", email="dev@example.com")
    
    # 2. Service API Key (Internal automation)
    service_api_key = os.getenv("SERVICE_API_KEY")
    if service_api_key and x_api_key == service_api_key:
        return UserContext(user_id="service-account", org_id="service-org", email="service@bot")

    # 3. Guard: No credentials provided
    if not credentials:
        if AUTH_REQUIRED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return LOG_ONLY_FALLBACK if AUTH_MODE == "log-only" else None

    token = credentials.credentials
    
    # 4. Verification Attempt 1: RS256 (Modern / JWKS)
    if jwks_client:
        try:
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=SUPABASE_JWT_AUD,
                options={"verify_aud": True}
            )
            print(f"AUTH: Success via RS256 (JWKS)")
            return _context_from_payload(payload)
        except Exception:
            pass

    # 5. Verification Attempt 2: HS256 (Legacy / Secret)
    if SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience=SUPABASE_JWT_AUD,
                options={"verify_aud": True}
            )
            print(f"AUTH: Success via HS256 (Legacy)")
            return _context_from_payload(payload)
        except Exception as e:
            print(f"AUTH FAIL (HS256): {str(e)}")

    # 6. Final check
    if AUTH_REQUIRED:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Return None for log-only but only if we didn't use the fallback
    return LOG_ONLY_FALLBACK if AUTH_MODE == "log-only" else None

def _context_from_payload(payload: dict) -> UserContext:
    user_id = payload.get("sub")
    org_id = payload.get("org_id") or payload.get("organization_id") or user_id
    email = payload.get("email") or payload.get("user_metadata", {}).get("email")
    return UserContext(user_id=user_id, org_id=org_id, email=email)

from database import get_db

def require_role(role_name: str):
    return RoleChecker(role_name)

class RoleChecker:
    def __init__(self, allowed_role: str):
        self.allowed_role = allowed_role

    def __call__(self, ctx: Optional[UserContext] = Depends(get_current_user), db = Depends(get_db)):
        # Bypass role checks in log-only or disabled modes to prevent disruption during rollout
        if DISABLE_AUTH or AUTH_MODE == "log-only" or (not AUTH_REQUIRED and not ctx):
            if AUTH_MODE == "log-only":
                print(f"AUTH ROLE (Log-only): Bypassing role check for {self.allowed_role}")
            return True
        
        if not ctx:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

        import models
        has_role = db.query(models.UserRole).filter(
            models.UserRole.user_id == ctx.user_id,
            models.UserRole.role_id == self.allowed_role,
            models.UserRole.organization_id == ctx.org_id
        ).first()
        
        if not has_role:
             # Admin fallback
             if self.allowed_role != "admin":
                 is_admin = db.query(models.UserRole).filter(
                    models.UserRole.user_id == ctx.user_id,
                    models.UserRole.role_id == "admin",
                    models.UserRole.organization_id == ctx.org_id
                ).first()
                 if is_admin:
                     return True

             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Operation requires {self.allowed_role} role"
            )
        return True
