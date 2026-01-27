from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models, schemas, auth
from database import get_db
from pydantic import BaseModel
import os
from supabase import create_client, Client

router = APIRouter(
    prefix="/api",
    tags=["admin"]
)

class RoleUpdate(BaseModel):
    roles: List[str]

class UserInvite(BaseModel):
    email: str
    role: str
    target_org_ids: List[str] = []

@router.get("/users/me/roles")
def get_my_roles(
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """Get roles for the current user in the current context"""
    user_roles = db.query(models.UserRole).filter(
        models.UserRole.user_id == ctx.user_id,
        models.UserRole.organization_id == ctx.org_id
    ).all()
    
    return {"roles": [ur.role_id for ur in user_roles]}

@router.get("/admin/organizations", dependencies=[Depends(auth.require_role("admin"))], response_model=List[schemas.StoreSchema])
def list_all_organizations(
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """List ALL organizations (Stores) in the system"""
    stores = db.query(models.Store).all()
    # Map store_id (int) to id (str) for frontend
    return [{"id": str(s.store_id), "name": s.name} for s in stores]

@router.get("/admin/users", dependencies=[Depends(auth.require_role("admin"))])
def list_users(
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """List all users in the organization (and their roles)"""
    # Note: Since users are in Supabase, we can only list users who have interacted with our DB 
    # OR we need to use Supabase Admin API to list all.
    # For now, we'll list users present in user_roles table or distinct users from invoices/tables?
    # Better approach for MVP: List users from UserRoles table + maybe query invoices for unique user_ids?
    # Cleanest: Just query UserRoles joined with Roles.
    
    # Ideally, we should have a 'users' table sync, but we don't. 
    # So we will return a list of users found in the UserRole table.
    
    user_roles = db.query(models.UserRole).filter(
        models.UserRole.organization_id == ctx.org_id
    ).all()
    
    # Group by user_id
    users = {}
    for ur in user_roles:
        if ur.user_id not in users:
            users[ur.user_id] = {"user_id": ur.user_id, "roles": []}
        users[ur.user_id]["roles"].append(ur.role_id)
        
    return list(users.values())

@router.put("/admin/users/{user_id}/roles", dependencies=[Depends(auth.require_role("admin"))])
def update_user_roles(
    user_id: str,
    role_data: RoleUpdate,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """Assign roles to a user"""
    # 1. Clear existing roles for this org
    db.query(models.UserRole).filter(
        models.UserRole.user_id == user_id,
        models.UserRole.organization_id == ctx.org_id
    ).delete()
    
    # 2. Add new roles
    for role_id in role_data.roles:
        new_role = models.UserRole(
            user_id=user_id,
            role_id=role_id,
            organization_id=ctx.org_id
        )
        db.add(new_role)
        
    db.commit()
    return {"status": "success", "roles": role_data.roles}

@router.post("/admin/users", dependencies=[Depends(auth.require_role("admin"))])
def invite_user(
    invite_data: UserInvite,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """Invite a new user via Supabase and assign a role"""
    
    # 1. Initialize Supabase Admin Client
    # Only initialize if we have the service key
    supabase_url = os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL") # Fallback to VITE_ var if shared env
    supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_service_key:
        print("ERROR: Missing SUPABASE_SERVICE_ROLE_KEY")
        raise HTTPException(
            status_code=500, 
            detail="Server configuration error: Missing Supabase Admin Keys"
        )
        
    try:
        supabase: Client = create_client(supabase_url, supabase_service_key)
        
        # 2. Invite User
        # This sends a magic link to the user
        print(f"Inviting user: {invite_data.email}")
        response = supabase.auth.admin.invite_user_by_email(invite_data.email)
        user = response.user
        
        if not user:
             raise Exception("No user returned from invite request")

    except Exception as e:
        print(f"Supabase Invite Error: {e}")
        # Fallback: Check if we can get the user by email (maybe they already exist?)
        # Only if the error suggests they exist, but for now just fail safely
        raise HTTPException(status_code=400, detail=f"Failed to invite user: {str(e)}")

        raise HTTPException(status_code=400, detail=f"Failed to invite user: {str(e)}")

    # 3. Add Roles for each Target Org
    # If target_org_ids is empty, default to current org
    target_orgs = invite_data.target_org_ids if invite_data.target_org_ids else [ctx.org_id]
    
    # NOTE: User requested to see/assign to ALL organizations.
    # We are relaxing the check that the requester must be an admin of the target org.
    # Any admin of the *current* org can now assign users to *any* org.
    
    results = []
    
    for org_id in target_orgs:
        # Check if role exists for this user in this org
        existing_role = db.query(models.UserRole).filter(
            models.UserRole.user_id == user.id,
            models.UserRole.organization_id == org_id
        ).first()
        
        if existing_role:
            existing_role.role_id = invite_data.role
            results.append(f"Updated {org_id}")
        else:
            new_role = models.UserRole(
                user_id=user.id,
                role_id=invite_data.role,
                organization_id=org_id
            )
            db.add(new_role)
            results.append(f"Added to {org_id}")
    
    db.commit()
    
    return {
        "status": "success", 
        "message": f"User invited. Actions: {', '.join(results)}", 
        "user": {"id": user.id, "email": user.email}
    }
