from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import os

import models, auth, migrate
from database import get_db
from services import demo_service

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
