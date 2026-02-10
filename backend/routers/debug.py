from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import os

import models, auth, migrate
from database import get_db
from services import demo_service, storage, stellar_service


router = APIRouter(
    tags=["debug"]
)

@router.get("/api/debug/templates")
def list_templates(
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """Debug endpoint to list all learned templates"""
    templates = db.query(models.Template).filter(models.Template.organization_id == ctx.org_id).all()
    
    return {
        "count": len(templates),
        "templates": [
            {
                "id": t.id,
                "vendor_name": t.vendor_name,
                "created_at": t.created_at,
                "content_preview": t.content[:50] + "..." if t.content else ""
            }
            for t in templates
        ],
        "source": "database"
    }

@router.get("/api/debug/db-info")
def get_db_info():
    """Debug endpoint to check which database is being used"""
    db_url = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")
    is_sqlite = "sqlite" in db_url
    return {
        "database_type": "sqlite" if is_sqlite else "postgres",
        "database_url_masked": db_url.split("@")[-1] if "@" in db_url else "sqlite_local"
    }

@router.get("/api/debug/health")
def database_health(db: Session = Depends(get_db)):
    """Deep health check that verifies DB query and environment"""
    try:
        # 1. Try a simple query
        count = db.query(models.Invoice).count()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
        count = -1

    return {
        "db_status": db_status,
        "invoice_count": count,
        "env": {
            "SUPABASE_JWT_SECRET_SET": bool(os.getenv("SUPABASE_JWT_SECRET")),
            "SUPABASE_JWT_AUD": os.getenv("SUPABASE_JWT_AUD", "authenticated"),
            "DATABASE_URL_SET": bool(os.getenv("DATABASE_URL")),
            "AWS_BUCKET_NAME": os.getenv("AWS_BUCKET_NAME")
        }
    }

@router.post("/api/seed/demo")
def seed_demo_invoice(
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """
    Generate and inject a Stark Industries demo invoice.
    """
    invoice = demo_service.seed_demo_data(db, ctx.org_id)
    return {"message": "Demo invoice created", "invoice_id": invoice.id}

@router.post("/api/debug/migrate")
def trigger_migration():
    """
    Manually trigger database migration to ensure schema consistency.
    Useful for environments like Render where shell access might be limited.
    """
    try:
        migrate.migrate()
        return {"status": "success", "message": "Migration completed successfully"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}

@router.get("/api/debug/schema")
def inspect_schema(db: Session = Depends(get_db)):
    """
    Inspect the database schema to verify columns exist.
    """
    from sqlalchemy import inspect
    inspector = inspect(db.get_bind())
    
    tables = inspector.get_table_names()
    schema_info = {}
    
    for table in tables:
        columns = [col["name"] for col in inspector.get_columns(table)]
        schema_info[table] = columns
        
    return {
        "tables": tables,
        "schema": schema_info
    }

from pydantic import BaseModel

class SQLRequest(BaseModel):
    query: str

@router.post("/api/debug/sql")
def execute_raw_sql(
    sql_req: SQLRequest,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """
    Emergency endpoint to run raw SQL. 
    Use with EXTREME CAUTION.
    """
    from sqlalchemy import text
    try:
        result = db.execute(text(sql_req.query))
        db.commit()
        
        # Try to fetch results if it's a SELECT
        try:
            keys = result.keys()
            rows = [dict(zip(keys, row)) for row in result.fetchall()]
            return {"status": "success", "rows": rows}
        except:
            return {"status": "success", "message": "Command executed, no rows returned"}
            
    except Exception as e:
        import traceback
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}

@router.post("/api/debug/bootstrap-admin")
def bootstrap_admin_role(
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """
    Emergency endpoint to promote the CURRENT user to admin.
    Does NOT require admin role (obviously).
    """
    try:
        # Check if already has admin role
        existing = db.query(models.UserRole).filter(
            models.UserRole.user_id == ctx.user_id,
            models.UserRole.role_id == "admin",
            models.UserRole.organization_id == ctx.org_id
        ).first()

        if existing:
            return {"status": "success", "message": "User is already admin", "user_id": ctx.user_id}

        # Insert admin role
        new_role = models.UserRole(
            user_id=ctx.user_id,
            role_id="admin",
            organization_id=ctx.org_id
        )
        db.add(new_role)
        db.commit()
        return {"status": "success", "message": "User promoted to admin", "user_id": ctx.user_id}
    except Exception as e:
        import traceback
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}

@router.get("/api/debug/org-context")
def debug_org_context(
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """
    Diagnostic endpoint to show:
    - Current user's organization context
    - All unique organization_ids in invoices table
    - Count of invoices per organization
    """
    from sqlalchemy import func
    
    # Get invoice counts by organization
    org_counts = db.query(
        models.Invoice.organization_id,
        func.count(models.Invoice.id).label('count')
    ).group_by(models.Invoice.organization_id).all()
    
    # Get user roles
    user_roles = db.query(models.UserRole).filter(
        models.UserRole.user_id == ctx.user_id
    ).all()
    
    return {
        "current_context": {
            "user_id": ctx.user_id,
            "org_id": ctx.org_id,
            "email": ctx.email
        },
        "invoice_organizations": [
            {"organization_id": org_id, "invoice_count": count}
            for org_id, count in org_counts
        ],
        "user_roles": [
            {
                "organization_id": role.organization_id,
                "role_id": role.role_id
            }
            for role in user_roles
        ],
        "diagnosis": {
            "message": "If your org_id doesn't match any invoice organization_id, that's why you can't see invoices",
            "suggestion": "Check if invoices need to be migrated to the correct organization_id"
        }
    }


@router.get("/api/debug/diagnostics")
async def diagnostics(
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    """
    Comprehensive diagnostics for deployment issues.
    Checks: Env Vars, Database, S3 Storage, Stellar API.
    """
    import os
    results = {
        "environment": {},
        "storage": {"status": "unknown"},
        "stellar": {"status": "unknown"},
        "database": {"status": "connected"} # If we got here, DB is likely fine via Depends
    }
    
    # 1. Environment Variables
    results["environment"] = {
        "AWS_BUCKET_NAME": os.getenv("AWS_BUCKET_NAME"),
        "STELLAR_API_TOKEN": "SET" if os.getenv("STELLAR_API_TOKEN") else "MISSING",
        "STELLAR_TENANT_ID": os.getenv("STELLAR_TENANT_ID"),
        "STELLAR_INVENTORY_URL": os.getenv("STELLAR_INVENTORY_URL", "DEFAULT"),
        "PDF_GENERATION_ENABLED": os.getenv("PDF_GENERATION_ENABLED", "True")
    }
    
    # 2. Check Storage (S3)
    try:
        if not storage.AWS_BUCKET_NAME:
            results["storage"] = {"status": "error", "message": "AWS_BUCKET_NAME not set"}
        else:
            # Try to list 1 object to verify permissions/connectivity
            s3 = storage.storage_client._get_client() # Access internal client
            s3.list_objects_v2(Bucket=storage.AWS_BUCKET_NAME, MaxKeys=1)
            results["storage"] = {"status": "ok", "bucket": storage.AWS_BUCKET_NAME}
    except Exception as e:
        results["storage"] = {"status": "error", "message": str(e)}
        
    # 3. Check Stellar
    try:
        # We can't easily ping without a tenant, but we can check if token is present
        if not stellar_service.STELLAR_API_TOKEN:
             results["stellar"] = {"status": "error", "message": "STELLAR_API_TOKEN not set"}
        else:
            # Maybe try a lightweight call if a tenant is linked to the store?
            store = db.query(models.Store).filter(models.Store.organization_id == ctx.org_id).first()
            if store and store.stellar_tenant:
                results["stellar"]["tenant_linked"] = store.stellar_tenant
                results["stellar"]["status"] = "configured"
            else:
                results["stellar"] = {"status": "warning", "message": "No Stellar Tenant linked to this Organization"}
    except Exception as e:
        results["stellar"] = {"status": "error", "message": str(e)}

    # 4. Check Tables
    from sqlalchemy import inspect
    inspector = inspect(db.get_bind())
    tables = inspector.get_table_names()
    results["database"]["tables"] = tables
    results["database"]["has_stellar_suppliers"] = "stellar_suppliers" in tables
        
    return results

@router.post("/api/debug/fix-db")
def fix_database_schema(db: Session = Depends(get_db), ctx: auth.UserContext = Depends(auth.require_role("admin"))):
    """
    Force create missing tables.
    """
    try:
        models.Base.metadata.create_all(bind=db.get_bind())
        return {"status": "success", "message": "Database schema updated (create_all ran)"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

