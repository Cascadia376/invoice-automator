import pytest
import uuid
import models

def test_bulk_post_invoices(client, db_session):
    # Create two approved invoices
    inv_id1 = str(uuid.uuid4())
    inv_id2 = str(uuid.uuid4())
    
    db_session.add(models.Invoice(
        id=inv_id1,
        organization_id="dev-org",
        invoice_number="INV-B1",
        vendor_name="Bulk 1",
        date="2024-01-01",
        status="approved",
        is_posted=False,
        total_amount=100.0
    ))
    db_session.add(models.Invoice(
        id=inv_id2,
        organization_id="dev-org",
        invoice_number="INV-B2",
        vendor_name="Bulk 2",
        date="2024-01-02",
        status="approved",
        is_posted=False,
        total_amount=200.0
    ))
    db_session.commit()

    # Call bulk post endpoint
    response = client.patch("/api/invoices/bulk-post", json=[inv_id1, inv_id2])
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # Verify in DB
    inv1 = db_session.query(models.Invoice).filter(models.Invoice.id == inv_id1).first()
    inv2 = db_session.query(models.Invoice).filter(models.Invoice.id == inv_id2).first()
    
    assert inv1.is_posted is True
    assert inv2.is_posted is True
