import os
import jwt
import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from jwt.algorithms import RSAAlgorithm
import json

class UserContext(BaseModel):
    user_id: str
    org_id: str
    email: Optional[str] = None

security = HTTPBearer(auto_error=False)

# Optional: Add simple API Key header support for scripts
from fastapi import Header
async def get_api_key(x_api_key: Optional[str] = Header(None)):
    return x_api_key


# Cache for JWKS
jwks_cache = {}

def get_jwks(issuer_url: str):
    if issuer_url in jwks_cache:
        return jwks_cache[issuer_url]
    
    try:
        response = requests.get(f"{issuer_url}/.well-known/jwks.json")
        response.raise_for_status()
        jwks = response.json()
        jwks_cache[issuer_url] = jwks
        return jwks
    except Exception as e:
        print(f"Error fetching JWKS: {e}")
        return None

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None)
) -> UserContext:
    
    # 1. Check for Service API Key (for Scripts/Folder Sync)
    service_api_key = os.getenv("SERVICE_API_KEY")
    if service_api_key and x_api_key and x_api_key == service_api_key:
        print("AUTH: Valid API Key used. Access granted as Service Account.")
        return UserContext(
            user_id="service-account",
            org_id="service-org", # Or configure a specific target org in the script
            email="service@bot"
        )

    # 2. Check for Clerk JWT
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    issuer_url = os.getenv("CLERK_ISSUER_URL")
    
    # ... rest of JWT logic ...
    
    print(f"AUTH DEBUG: Received token (len={len(token)})")
    print(f"AUTH DEBUG: Issuer URL: {issuer_url}")

    if not issuer_url:
        print("AUTH ERROR: CLERK_ISSUER_URL is missing!")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CLERK_ISSUER_URL not configured"
        )

    try:
        # Get Key ID (kid) from header
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        
        # Fetch JWKS and find the key
        jwks = get_jwks(issuer_url)
        if not jwks:
             print("AUTH ERROR: Could not fetch JWKS")
             raise HTTPException(status_code=500, detail="Could not fetch JWKS")
             
        public_key = None
        for key in jwks["keys"]:
            if key["kid"] == kid:
                public_key = RSAAlgorithm.from_jwk(json.dumps(key))
                break
        
        if not public_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token key ID"
            )

        # Decode and Validate
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=issuer_url,
            options={"verify_aud": False} 
        )
        
        # Extract Context
        user_id = payload.get("sub")
        org_id = payload.get("org_id")
        
        if not org_id:
             org_id = user_id

        print(f"AUTH SUCCESS: User={user_id}, Org={org_id}")
        return UserContext(
            user_id=user_id,
            org_id=org_id,
            email=payload.get("email")
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
