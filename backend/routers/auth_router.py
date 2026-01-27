from fastapi import APIRouter, Depends
from typing import Optional
import auth

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"]
)

@router.get("/whoami")
async def whoami(ctx: Optional[auth.UserContext] = Depends(auth.get_current_user)):
    """
    Returns the current user's ID and whether authentication is strictly enforced.
    This helps the frontend and scripts determine if they are properly authenticated.
    """
    return {
        "user_id": ctx.user_id if ctx else None,
        "email": ctx.email if ctx else None,
        "org_id": ctx.org_id if ctx else None,
        "auth_required": auth.AUTH_REQUIRED,
        "authenticated": ctx is not None
    }
