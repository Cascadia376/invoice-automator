import pytest
import uuid
import models

def test_get_dashboard_stats_empty(client):
    response = client.get("/api/invoices/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["totalInvoices"] == 0
    assert data["needsReview"] == 0
    assert data["approved"] == 0
    assert data["issueCount"] == 0
    assert data["timeSaved"] == "0.0h"

def test_get_dashboard_stats_with_data(client, db_session):
    # Create some mock invoices
    org_id = "dev-org" # This should match what's used in auth.py's dev bypass
    
    # 1. Approved invoice
    inv1 = models.Invoice(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        invoice_number="INV-001",
        vendor_name="Vendor A",
        date="2026-01-01",
        total_amount=100.0,
        tax_amount=5.0,
        status="approved"
    )
    
    # 2. Pending invoice
    inv2 = models.Invoice(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        invoice_number="INV-002",
        vendor_name="Vendor B",
        date="2026-01-02",
        total_amount=200.0,
        tax_amount=10.0,
        status="needs_review"
    )
    
    # 3. Invoice with issue
    inv3 = models.Invoice(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        invoice_number="INV-003",
        vendor_name="Vendor C",
        date="2026-01-03",
        total_amount=300.0,
        tax_amount=15.0,
        status="needs_review"
    )
    item = models.LineItem(
        id=str(uuid.uuid4()),
        invoice_id=inv3.id,
        description="Damaged item",
        quantity=1,
        unit_cost=10.0,
        amount=10.0,
        issue_type="breakage"
    )
    inv3.line_items.append(item)
    
    db_session.add(inv1)
    db_session.add(inv2)
    db_session.add(inv3)
    db_session.commit()
    
    response = client.get("/api/invoices/stats")
    assert response.status_code == 200
    data = response.json()
    
    assert data["totalInvoices"] == 3
    assert data["needsReview"] == 2
    assert data["approved"] == 1
    assert data["issueCount"] == 1
    assert data["timeSaved"] == "0.2h" # 15/60 = 0.25 -> 0.2 (formatted as .1f)
