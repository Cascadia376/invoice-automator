from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models, schemas, auth
from database import get_db
from pydantic import BaseModel
import os
from supabase import create_client, Client

def get_supabase_admin() -> Client:
    supabase_url = os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_service_key:
        raise HTTPException(
            status_code=500, 
            detail="Server configuration error: Missing Supabase Admin Keys"
        )
    return create_client(supabase_url, supabase_service_key)


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

@router.get("/admin/users", dependencies=[Depends(auth.require_role("admin"))], response_model=List[schemas.UserResponse])
def list_users(
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """List all users with rich details from Supabase Auth"""
    # 1. Fetch all users from Supabase Auth
    try:
        supabase = get_supabase_admin()
        # Fetch up to 1000 users for now
        response = supabase.auth.admin.list_users(page=1, per_page=1000)
        auth_users = response if isinstance(response, list) else response.users # Handle different client versions
    except Exception as e:
        # Propagate error so frontend sees it
        raise HTTPException(
            status_code=500,
            detail=f"Supabase Admin API Error: {str(e)}"
        )

    # 2. Fetch all roles/store mappings from DB
    user_roles = db.query(models.UserRole).all()
    
    # 3. Fetch all stores to map IDs to names
    all_stores = db.query(models.Store).all()
    store_map = {str(s.store_id): s.name for s in all_stores}

    # Group roles by user_id
    # user_roles_map = { user_id: { roles: set(), store_ids: [] } }
    user_roles_map = {}
    for ur in user_roles:
        if ur.user_id not in user_roles_map:
            user_roles_map[ur.user_id] = {"roles": set(), "store_ids": set()}
        
        user_roles_map[ur.user_id]["roles"].add(ur.role_id)
        user_roles_map[ur.user_id]["store_ids"].add(ur.organization_id)

    # 4. Merge Data
    result = []
    for u in auth_users:
        uid = u.id
        
        # Get DB Data
        db_data = user_roles_map.get(uid, {"roles": [], "store_ids": []})
        
        # Format Stores
        relevant_stores = []
        for sid in db_data["store_ids"]:
            if sid in store_map:
                relevant_stores.append(schemas.StoreSchema(id=sid, name=store_map[sid]))
            else:
                relevant_stores.append(schemas.StoreSchema(id=sid, name="Unknown Store"))
        
        # Extract Metadata
        meta = u.user_metadata or {}
        
        result.append(schemas.UserResponse(
            id=uid,
            email=u.email or "",
            first_name=meta.get("first_name") or meta.get("firstName"),
            last_name=meta.get("last_name") or meta.get("lastName"),
            roles=list(db_data["roles"]),
            stores=relevant_stores,
            created_at=datetime.fromisoformat(u.created_at.replace('Z', '+00:00')) if u.created_at else None
        ))
        
    return result

@router.put("/admin/users/{user_id}", dependencies=[Depends(auth.require_role("admin"))])
def update_user(
    user_id: str,
    user_data: schemas.UserUpdate,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """Update user details and store/role assignments"""
    supabase = get_supabase_admin()
    
    # 1. Update Supabase Auth (Email, Metadata)
    updates = {}
    if user_data.email:
        updates["email"] = user_data.email
    
    meta_updates = {}
    if user_data.first_name:
        meta_updates["first_name"] = user_data.first_name
    if user_data.last_name:
        meta_updates["last_name"] = user_data.last_name
        
    if updates or meta_updates:
        if meta_updates:
            updates["user_metadata"] = meta_updates
        try:
            supabase.auth.admin.update_user_by_id(user_id, updates)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to update Supabase user: {e}")

    # 2. Update Roles/Stores (if provided)
    # Strategy: If target_org_ids is provided, existing roles are replaced.
    if user_data.target_org_ids is not None:
        # Validate Role (required if changing stores)
        role_to_assign = user_data.role
        if not role_to_assign:
            # Try to infer role from existing (safe fallback: 'staff')
            existing = db.query(models.UserRole).filter(models.UserRole.user_id == user_id).first()
            role_to_assign = existing.role_id if existing else "staff"

        # Wipe existing roles
        db.query(models.UserRole).filter(models.UserRole.user_id == user_id).delete()
        
        # Create new roles
        for org_id in user_data.target_org_ids:
            new_role = models.UserRole(
                user_id=user_id,
                role_id=role_to_assign,
                organization_id=org_id
            )
            db.add(new_role)
        db.commit()
    
    return {"status": "success"}

@router.delete("/admin/users/{user_id}", dependencies=[Depends(auth.require_role("admin"))])
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """Delete a user from Keycloak/Supabase and DB"""
    # Prevent deleting yourself
    if user_id == ctx.user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    supabase = get_supabase_admin()

    # 1. Delete from Supabase
    try:
        supabase.auth.admin.delete_user(user_id)
    except Exception as e:
        print(f"Warning: Failed to delete from Supabase (might not exist): {e}")

    # 2. Delete from DB (Roles)
    db.query(models.UserRole).filter(models.UserRole.user_id == user_id).delete()
    db.commit()

    return {"status": "success"}

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
@router.get("/admin/connection-status", dependencies=[Depends(auth.require_role("admin"))])
def check_connection(
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """
    Diagnostic endpoint to verify Supabase Admin connectivity from the backend.
    """
    supabase_url = os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    status_report = {
        "env": {
            "SUPABASE_URL": "Set" if supabase_url else "MISSING",
            "SUPABASE_SERVICE_ROLE_KEY": "Set" if supabase_service_key else "MISSING",
        },
        "connection": "Unknown",
        "user_count": -1,
        "error": None
    }

    try:
        supabase = get_supabase_admin()
        status_report["connection"] = "Client Initialized"
        
        # Try specific fetch
        response = supabase.auth.admin.list_users(page=1, per_page=5)
        users = response if isinstance(response, list) else response.users
        
        status_report["connection"] = "Success"
        status_report["user_count"] = len(users)
        
    except Exception as e:
        status_report["connection"] = "Failed"
        status_report["error"] = str(e)
        
    return status_report
