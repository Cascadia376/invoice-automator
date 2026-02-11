
import os
import sys
import asyncio
import json
from unittest.mock import MagicMock, patch

# Setup pathing for backend imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, 'backend'))

# Set dummy env vars for imports
os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost:5432/db"
os.environ["STELLAR_API_TOKEN"] = "test-token"

from backend.services import stellar_service
from backend import models

async def verify_dynamic_classification():
    print("Verifying Dynamic Stellar Classification Logic...")
    
    # Mock database session
    db = MagicMock()
    
    # Mock invoice
    invoice = models.Invoice(
        id="test-inv",
        invoice_number="INV-123",
        organization_id="org-123"
    )
    invoice.line_items = [models.LineItem(sku="SKU1", quantity=10, amount=100.0)]
    
    # Mock Store
    store = models.Store(
        name="Test Store",
        stellar_location_id="loc-123",
        stellar_location_name="Test Store Location"
    )
    db.query().filter().first.return_value = store
    
    # Test Case 1: Special Supplier (LDB) - should not fetch profile, tax_ids should be blank
    print("\n--- Test Case 1: LDB (Special Supplier) ---")
    with patch('backend.services.stellar_service.stellar_client.get_supplier') as mock_get:
        # We need to mock generate_stellar_csv to avoid real CSV generation
        with patch('backend.services.stellar_service.generate_stellar_csv', return_value=b"test-csv"):
            # Mock httpx client post
            with patch('httpx.AsyncClient.post') as mock_post:
                mock_post.return_value.is_success = True
                mock_post.return_value.json.return_value = {"status": "success"}
                
                result = await stellar_service.post_invoice_to_stellar(
                    invoice, db, "ldb-uuid", "LDB"
                )
                
                mock_get.assert_not_called()
                print("LDB: get_supplier NOT called (Correct)")
                
                # Check form_data sent
                args, kwargs = mock_post.call_args
                form_data = kwargs.get('data', {})
                print(f"LDB tax_ids sent: '{form_data.get('tax_ids')}' (Expected: '')")
                assert form_data.get('tax_ids') == ""

    # Test Case 2: Custom Supplier (Container World) - should fetch profile
    print("\n--- Test Case 2: Container World (Custom Supplier) ---")
    with patch('backend.services.stellar_service.stellar_client.get_supplier') as mock_get:
        mock_get.return_value = {
            "result": {
                "tax_ids": "dynamic-uuid-from-api"
            }
        }
        
        with patch('backend.services.stellar_service.generate_stellar_csv', return_value=b"test-csv"):
            with patch('httpx.AsyncClient.post') as mock_post:
                mock_post.return_value.is_success = True
                mock_post.return_value.json.return_value = {"status": "success"}
                
                result = await stellar_service.post_invoice_to_stellar(
                    invoice, db, "cw-uuid", "Container World"
                )
                
                mock_get.assert_called_once_with("cw-uuid", "cascadialiquor")
                print("Container World: get_supplier CALLED (Correct)")
                
                # Check form_data sent
                args, kwargs = mock_post.call_args
                form_data = kwargs.get('data', {})
                print(f"CW tax_ids sent: '{form_data.get('tax_ids')}' (Expected: 'dynamic-uuid-from-api')")
                assert form_data.get('tax_ids') == "dynamic-uuid-from-api"

    print("\nVerification Complete: All tests passed!")

if __name__ == "__main__":
    asyncio.run(verify_dynamic_classification())
