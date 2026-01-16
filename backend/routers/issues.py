
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
import uuid
from datetime import datetime

import models, schemas, auth
from database import get_db

router = APIRouter(
    prefix="/api/issues",
    tags=["issues"]
)

@router.get("", response_model=List[schemas.Issue])
def read_issues(
    status: str = None,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    query = db.query(models.Issue).join(models.Invoice).filter(models.Issue.organization_id == ctx.org_id)
    
    if status:
        query = query.filter(models.Issue.status == status)
        
    issues = query.all()
    
    # Enrich with invoice/vendor info for the dashboard
    for issue in issues:
        issue.vendor_name = issue.invoice.vendor_name
        issue.invoice_number = issue.invoice.invoice_number
        
    return issues

@router.post("", response_model=schemas.Issue)
def create_issue(
    issue: schemas.IssueCreate,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    # Verify invoice belongs to org
    invoice = db.query(models.Invoice).filter(
        models.Invoice.id == issue.invoice_id,
        models.Invoice.organization_id == ctx.org_id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    db_issue = models.Issue(
        id=str(uuid.uuid4()),
        organization_id=ctx.org_id,
        invoice_id=issue.invoice_id,
        vendor_id=issue.vendor_id or invoice.vendor_id,
        type=issue.type,
        status=issue.status,
        description=issue.description,
        resolution_status=issue.resolution_status
    )
    
    # Link line items
    if issue.line_item_ids:
        line_items = db.query(models.LineItem).filter(
            models.LineItem.id.in_(issue.line_item_ids),
            models.LineItem.invoice_id == issue.invoice_id
        ).all()
        db_issue.line_items = line_items
    
    db.add(db_issue)
    db.commit()
    db.refresh(db_issue)
    return db_issue

@router.get("/{issue_id}", response_model=schemas.Issue)
def read_issue(
    issue_id: str,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    issue = db.query(models.Issue).filter(
        models.Issue.id == issue_id,
        models.Issue.organization_id == ctx.org_id
    ).first()
    
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
        
    issue.vendor_name = issue.invoice.vendor_name
    issue.invoice_number = issue.invoice.invoice_number
    return issue

@router.put("/{issue_id}", response_model=schemas.Issue)
def update_issue(
    issue_id: str,
    issue_update: schemas.IssueUpdate,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    db_issue = db.query(models.Issue).filter(
        models.Issue.id == issue_id,
        models.Issue.organization_id == ctx.org_id
    ).first()
    
    if not db_issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    update_data = issue_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_issue, key, value)
        
    if issue_update.status == "resolved" and not db_issue.resolved_at:
        db_issue.resolved_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_issue)
    return db_issue

@router.post("/{issue_id}/communications", response_model=schemas.IssueCommunication)
def add_communication(
    issue_id: str,
    comm: schemas.IssueCommunicationCreate,
    db: Session = Depends(get_db),
    ctx: auth.UserContext = Depends(auth.get_current_user)
):
    db_issue = db.query(models.Issue).filter(
        models.Issue.id == issue_id,
        models.Issue.organization_id == ctx.org_id
    ).first()
    
    if not db_issue:
        raise HTTPException(status_code=404, detail="Issue not found")
        
    db_comm = models.IssueCommunication(
        id=str(uuid.uuid4()),
        issue_id=issue_id,
        organization_id=ctx.org_id,
        type=comm.type,
        content=comm.content,
        recipient=comm.recipient,
        created_by=ctx.user_id
    )
    
    db.add(db_comm)
    db.commit()
    db.refresh(db_comm)
    return db_comm
