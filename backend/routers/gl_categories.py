from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from datetime import datetime
import models, schemas, auth
from database import get_db

router = APIRouter(
    tags=["gl_categories"]
)

@router.get("/api/gl-categories", response_model=List[schemas.GLCategory])
def get_gl_categories(
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    categories = db.query(models.GLCategory).filter(models.GLCategory.organization_id == ctx.org_id).all()
    
    if not categories:
        # Default seed for new organizations
        defaults = ["BEER", "WINE", "LIQUOR", "COOLERS", "CIDER", "TOBACCO", "LOTTERY", "MISC", "MIX & CONFEC"]
        return [
            models.GLCategory(
                id=str(uuid.uuid4()), 
                organization_id=ctx.org_id, 
                code=c, 
                name=c, 
                full_name=c,
                created_at=datetime.utcnow()
            ) for c in defaults
        ]
        
    return categories

@router.post("/api/gl-categories", response_model=schemas.GLCategory)
def create_gl_category(
    category: schemas.GLCategoryCreate, 
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    db_category = models.GLCategory(
        id=str(uuid.uuid4()),
        organization_id=ctx.org_id,
        code=category.code,
        name=category.name,
        full_name=category.full_name
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

@router.put("/api/gl-categories/{category_id}", response_model=schemas.GLCategory)
def update_gl_category(
    category_id: str, 
    category: schemas.GLCategoryCreate, 
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    db_category = db.query(models.GLCategory).filter(
        models.GLCategory.id == category_id,
        models.GLCategory.organization_id == ctx.org_id
    ).first()
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    
    db_category.code = category.code
    db_category.name = category.name
    db_category.full_name = category.full_name
    db.commit()
    db.refresh(db_category)
    return db_category

@router.delete("/api/gl-categories/{category_id}")
def delete_gl_category(
    category_id: str, 
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    db_category = db.query(models.GLCategory).filter(
        models.GLCategory.id == category_id,
        models.GLCategory.organization_id == ctx.org_id
    ).first()
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    
    db.delete(db_category)
    db.commit()
    return {"status": "success", "message": "Category deleted"}

@router.get("/api/sku-mappings/{sku}")
def get_sku_category(
    sku: str, 
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    mapping = db.query(models.SKUCategoryMapping).filter(
        models.SKUCategoryMapping.sku == sku,
        models.SKUCategoryMapping.organization_id == ctx.org_id
    ).order_by(models.SKUCategoryMapping.usage_count.desc()).first()
    
    if mapping:
        return {"sku": sku, "category_gl_code": mapping.category_gl_code, "usage_count": mapping.usage_count}
    return {"sku": sku, "category_gl_code": None}
