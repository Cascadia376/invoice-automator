from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models, schemas, auth
from database import get_db
from pydantic import BaseModel

router = APIRouter(
    prefix="/api",
    tags=["admin"]
)

class RoleUpdate(BaseModel):
    roles: List[str]

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
