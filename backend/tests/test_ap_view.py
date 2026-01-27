import pytest
import uuid
import models

def test_post_to_pos(client, db_session):
    # Create an invoice
    inv_id = str(uuid.uuid4())
    db_invoice = models.Invoice(
        id=inv_id,
        organization_id="dev-org",
        invoice_number="INV-123",
        vendor_name="Test Vendor",
        date="2024-01-01",
        status="approved",
        is_posted=False,
        total_amount=100.0,
        tax_amount=5.0
    )
    db_session.add(db_invoice)
    db_session.commit()

    # Call endpoint (patch)
    response = client.patch(f"/api/invoices/{inv_id}/post")
    
    assert response.status_code == 200
    assert response.json()["isPosted"] is True
    
    # Check DB
    db_session.refresh(db_invoice)
    assert db_invoice.is_posted is True

def test_category_summary(client, db_session):
    # Create an approved and posted invoice with line items
    # Use a unique month to avoid interference from other tests (e.g. test_post_to_pos)
    org_id = "dev-org"
    inv_id = str(uuid.uuid4())
    db_invoice = models.Invoice(
        id=inv_id,
        organization_id=org_id,
        invoice_number="INV-SUMMARY-UNIQUE",
        date="2024-02-15",
        status="approved",
        is_posted=True,
        total_amount=150.0,
        tax_amount=10.0,
        deposit_amount=2.0
    )
    db_session.add(db_invoice)
    
    item1 = models.LineItem(
        id=str(uuid.uuid4()),
        invoice_id=inv_id,
        description="Beer Item",
        amount=100.0,
        category_gl_code="BEER"
    )
    item2 = models.LineItem(
        id=str(uuid.uuid4()),
        invoice_id=inv_id,
        description="Wine Item",
        amount=38.0,
        category_gl_code="WINE"
    )
    db_session.add(item1)
    db_session.add(item2)
    db_session.commit()

    # Call summary endpoint for February
    response = client.get("/api/invoices/stats/category-summary", params={"month": "2024-02"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["invoice_count"] == 1
    assert data["total_amount"] == 150.0
    assert data["total_tax"] == 10.0
    assert data["total_deposit"] == 2.0
    assert data["category_totals"]["BEER"] == 100.0
    assert data["category_totals"]["WINE"] == 38.0
