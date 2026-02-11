import os
import sys
import uuid
import json
from unittest.mock import MagicMock, patch

# Add backend to path
sys.path.append(os.path.join(os.getcwd()))

# Set dummy DATABASE_URL if missing for testing
if not os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from database import SessionLocal, engine, Base
import models
from services import ingestion_service

def test_multi_invoice_ingestion():
    # Create tables in test DB
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    org_id = "test-org-id"
    user_id = "test-user-id"
    
    # Mock data for two invoices
    mock_extracted_data = [
        {
            "invoice_number": "INV-001",
            "vendor_name": "Vendor A",
            "total_amount": 100.0,
            "line_items": [{"description": "Item 1", "amount": 100.0, "quantity": 1}],
            "raw_extraction_results": json.dumps({"vendor": "A"})
        },
        {
            "invoice_number": "INV-002",
            "vendor_name": "Vendor B",
            "total_amount": 200.0,
            "line_items": [{"description": "Item 2", "amount": 200.0, "quantity": 1}],
            "raw_extraction_results": json.dumps({"vendor": "B"})
        }
    ]
    
    print("Testing multi-invoice ingestion with 2 mocks...")
    
    # Mocking parser and storage to avoid real S3/OpenAI calls
    with patch('services.parser.extract_invoice_data', return_value=mock_extracted_data), \
         patch('services.storage.upload_file', return_value=True), \
         patch('services.storage.get_presigned_url', return_value="https://mock-url.com"), \
         patch('services.vendor_service.get_or_create_vendor') as mock_vendor, \
         patch('services.vendor_service.apply_vendor_corrections', side_effect=lambda db, data, v: data), \
         patch('services.store_routing_service.resolve_store', return_value=(None, None)):
        
        # Setup mock vendor objects
        mock_v_a = MagicMock()
        mock_v_a.id = "v-a"
        mock_v_a.name = "Vendor A"
        
        mock_v_b = MagicMock()
        mock_v_b.id = "v-b"
        mock_v_b.name = "Vendor B"
        
        mock_vendor.side_effect = [mock_v_a, mock_v_b]
        
        # Call ingestion
        invoices = ingestion_service.process_invoice(
            db=db,
            file_path="mock_path.pdf",
            org_id=org_id,
            user_id=user_id,
            original_filename="multi_invoice.pdf"
        )
        
        print(f"Result: Created {len(invoices)} invoices.")
        
        assert len(invoices) == 2
        assert invoices[0].invoice_number == "INV-001"
        assert invoices[1].invoice_number == "INV-002"
        assert invoices[0].vendor_id == "v-a"
        assert invoices[1].vendor_id == "v-b"
        
        print("✅ Multi-invoice ingestion test passed!")
        
        # Clean up created invoices in DB
        for inv in invoices:
            db.delete(inv)
        db.commit()

if __name__ == "__main__":
    try:
        test_multi_invoice_ingestion()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
