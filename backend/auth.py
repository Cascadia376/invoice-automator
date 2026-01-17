import os
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional

class UserContext(BaseModel):
    user_id: str
    org_id: str
    email: Optional[str] = None

security = HTTPBearer(auto_error=False)

# Optional: Add simple API Key header support for scripts
from fastapi import Header
async def get_api_key(x_api_key: Optional[str] = Header(None)):
    return x_api_key


SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
SUPABASE_JWT_AUD = os.getenv("SUPABASE_JWT_AUD", "authenticated")
DISABLE_AUTH = os.getenv("DISABLE_AUTH", "").lower() == "true"

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None)
) -> UserContext:
    # Temporary dev bypass
    if DISABLE_AUTH:
        print("AUTH: Dev Mode Bypass (DISABLE_AUTH=true). Context: dev@example.com / dev-org")
        return UserContext(user_id="dev-user", org_id="dev-org", email="dev@example.com")
    
    # 1. Check for Service API Key (for Scripts/Folder Sync)
    service_api_key = os.getenv("SERVICE_API_KEY")
    if service_api_key and x_api_key and x_api_key == service_api_key:
        print("AUTH: Valid API Key used. Access granted as Service Account.")
        return UserContext(
            user_id="service-account",
            org_id="service-org", # Or configure a specific target org in the script
            email="service@bot"
        )

    # 2. Check for Supabase JWT
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    if not SUPABASE_JWT_SECRET:
        print("CRITICAL AUTH ERROR: SUPABASE_JWT_SECRET is missing from environment!")
        print("This will cause all authenticated requests to fail with 500.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error (JWT)"
        )

    try:
        options = {"verify_aud": bool(SUPABASE_JWT_AUD)}
        print(f"DEBUG: Decoding token with AUD={SUPABASE_JWT_AUD}, Secret Length={len(SUPABASE_JWT_SECRET) if SUPABASE_JWT_SECRET else 0}")
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience=SUPABASE_JWT_AUD if SUPABASE_JWT_AUD else None,
            options=options
        )
        
        user_id = payload.get("sub")
        org_id = payload.get("org_id") or payload.get("organization_id") or user_id
        email = payload.get("email") or payload.get("user_metadata", {}).get("email")
        
        print(f"AUTH SUCCESS: User={user_id}, Org={org_id}")
        return UserContext(
            user_id=user_id,
            org_id=org_id,
            email=email
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        print(f"JWT Decode Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        print(f"Auth Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
