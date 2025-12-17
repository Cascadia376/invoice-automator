from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import os

import models, auth
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
