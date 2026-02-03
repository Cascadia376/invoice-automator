import os
import jwt
import requests
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import httpx
import logging
from cachetools import TTLCache, cached
from jwt import decode, algorithms
from jwt.algorithms import RSAAlgorithm
from database import get_db

# Setup logging
logger = logging.getLogger("auth")
logger.setLevel(logging.INFO)

class UserContext(BaseModel):
    user_id: str
    org_id: str
    email: Optional[str] = None

security = HTTPBearer(auto_error=False)

# --- Configuration ---
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
SUPABASE_JWT_AUD = os.getenv("SUPABASE_JWT_AUD", "authenticated")
SUPABASE_ISSUER = f"{SUPABASE_URL}/auth/v1" if SUPABASE_URL else None
DISABLE_AUTH = os.getenv("DISABLE_AUTH", "").lower() == "true"

# Backward compatibility and Rollout flags
AUTH_MODE = os.getenv("AUTH_MODE", "strict").lower()
AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "false").lower() == "true"

# Respect legacy AUTH_MODE if AUTH_REQUIRED is not set
if AUTH_MODE == "strict" and "AUTH_REQUIRED" not in os.environ:
    AUTH_REQUIRED = True

# JWKS Setup
JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json" if SUPABASE_URL else None
jwks_cache = TTLCache(maxsize=1, ttl=3600) # Cache JWKS for 1 hour

async def get_jwks():
    """Fetch JWKS from Supabase with caching."""
    if "jwks" in jwks_cache:
        return jwks_cache["jwks"]
    
    if not JWKS_URL:
        return None
        
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(JWKS_URL)
            response.raise_for_status()
            jwks = response.json()
            jwks_cache["jwks"] = jwks
            return jwks
    except Exception as e:
        logger.error(f"AUTH ERROR: Failed to fetch JWKS: {str(e)}")
        return None

# Fallback for log-only mode to avoid 500s in routers expecting ctx.org_id
LOG_ONLY_FALLBACK = UserContext(user_id="anon-user", org_id="anon-org", email="anon@example.com")

async def get_supabase_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    FastAPI dependency to verify Supabase JWT and return claims.
    Usage: claims: dict = Depends(get_supabase_user)
    """
    if DISABLE_AUTH:
        logger.info("AUTH: Bypass (DISABLE_AUTH=true)")
        return {"sub": "dev-user", "email": "dev@example.com", "org_id": "dev-org"}

    if not credentials:
        if AUTH_REQUIRED:
            logger.warning("AUTH FAIL: Missing Authorization header (Strict Mode)")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        logger.info("AUTH: Missing Authorization header (Permissive Mode)")
        return None

    token = credentials.credentials
    
    # 1. RS256 JWKS Verification (Modern)
    jwks = await get_jwks()
    if jwks:
        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            key_data = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
            if key_data:
                public_key = RSAAlgorithm.from_jwk(key_data)
                payload = jwt.decode(
                    token,
                    public_key,
                    algorithms=["RS256"],
                    audience=SUPABASE_JWT_AUD,
                    issuer=SUPABASE_ISSUER,
                    options={
                        "verify_aud": True,
                        "verify_iss": bool(SUPABASE_ISSUER),
                        "verify_exp": True,
                        "verify_iat": True,
                        "require": ["exp", "iat", "sub"]
                    }
                )
                logger.debug(f"AUTH: RS256 Success for {payload.get('email')}")
                return payload
        except Exception as e:
            logger.error(f"AUTH RS256 Error: {str(e)}")

    # 2. HS256 Fallback (Legacy / Secret)
    if SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience=SUPABASE_JWT_AUD,
                options={"verify_aud": True}
            )
            logger.info(f"AUTH: HS256 Success for {payload.get('email')}")
            return payload
        except Exception as e:
            logger.warning(f"AUTH HS256 Error: {str(e)}")

    # 3. Final failure handling
    if AUTH_REQUIRED:
        logger.error("AUTH FAIL: Invalid or expired token (Strict Mode)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.info("AUTH: Invalid token (Permissive Mode)")
    return None

async def get_current_user(
    claims: Optional[dict] = Depends(get_supabase_user),
    x_api_key: Optional[str] = Header(None),
    x_organization_id: Optional[str] = Header(None, alias="x-organization-id"),
    db = Depends(get_db)
) -> Optional[UserContext]:
    """
    Wraps get_supabase_user to return a structured UserContext.
    Maintains compatibility with existing routes.
    """
    # Service API Key check (highest priority if provided)
    service_api_key = os.getenv("SERVICE_API_KEY")
    if service_api_key and x_api_key == service_api_key:
        return UserContext(user_id="service-account", org_id="service-org", email="service@bot")

    if not claims:
        return LOG_ONLY_FALLBACK if AUTH_MODE == "log-only" else None

    ctx = _context_from_payload(claims)
    
    # Handle Organization Switch (Store Switch)
    if x_organization_id and x_organization_id != ctx.org_id:
        if DISABLE_AUTH:
            ctx.org_id = x_organization_id
        else:
            # Verify user belongs to the target organization
            import models
            user_has_access = db.query(models.UserRole).filter(
                models.UserRole.user_id == ctx.user_id,
                models.UserRole.organization_id == x_organization_id
            ).first()
            
            if user_has_access:
                # logger.info(f"AUTH SWAP: User {ctx.user_id} switched to Org {x_organization_id}")
                ctx.org_id = x_organization_id
            elif ctx.email == "jay@trufflesgroup.com" or ctx.email == "dev@example.com":
                 # SUPER ADMIN BYPASS
                 ctx.org_id = x_organization_id
            else:
                logger.warning(f"AUTH FAIL: User {ctx.user_id} attempted to access Org {x_organization_id} without role")
                # We do NOT throw here to avoid breaking the request if it was just a hint? 
                # Actually we should throw 403 if they explicitly asked for it and can't have it.
                raise HTTPException(status_code=403, detail="Not authorized for this organization")

    return ctx

def _context_from_payload(payload: dict) -> UserContext:
    user_id = payload.get("sub")
    # Handle both new org_id and legacy mapping
    org_id = payload.get("org_id") or payload.get("organization_id") or user_id
    email = payload.get("email") or payload.get("user_metadata", {}).get("email")
    return UserContext(user_id=user_id, org_id=org_id, email=email)



from typing import Set, Union

def require_roles(allowed_roles: Union[str, Set[str]]):
    if isinstance(allowed_roles, str):
        allowed_roles = {allowed_roles}
    return RoleChecker(allowed_roles)

# Keep legacy alias for backward compatibility
def require_role(role_name: str):
    return require_roles({role_name})

class RoleChecker:
    def __init__(self, allowed_roles: Set[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, ctx: Optional[UserContext] = Depends(get_current_user), db = Depends(get_db)):
        # Bypass role checks in log-only or disabled modes to prevent disruption during rollout
        if DISABLE_AUTH or AUTH_MODE == "log-only" or (not AUTH_REQUIRED and not ctx):
            if AUTH_MODE == "log-only":
                logger.info(f"AUTH ROLE (Log-only): Bypassing role check for {self.allowed_roles}")
            # Mock context for bypass
            return {"user_id": "bypass", "role": list(self.allowed_roles)[0], "internal_user_id": "bypass"}
        
        if not ctx:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

        import models
        
        # SUPER ADMIN BYPASS
        if ctx.email == "jay@trufflesgroup.com" or ctx.email == "dev@example.com":
             return {
                "user_id": ctx.user_id,
                "role": "admin",
                "internal_user_id": ctx.user_id,
                "org_id": ctx.org_id 
            }

        # Check if user has ANY of the allowed roles
        # We also check for 'admin' as a super-role that can access anything
        roles_to_check = self.allowed_roles.union({"admin"})
        
        user_role = db.query(models.UserRole).filter(
            models.UserRole.user_id == ctx.user_id,
            models.UserRole.role_id.in_(roles_to_check),
            models.UserRole.organization_id == ctx.org_id
        ).first()
        
        if not user_role:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Operation requires one of roles: {self.allowed_roles}"
            )
            
        return {
            "user_id": ctx.user_id,
            "role": user_role.role_id,
            "internal_user_id": ctx.user_id, # Mapping sub to internal_id as no User table exists
            "org_id": ctx.org_id 
        }
