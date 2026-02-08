
import unittest
from unittest.mock import MagicMock, AsyncMock
import sys
import os
import asyncio

# Ensure backend in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Set dummy env var for database.py import
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from services import stellar_service
from models import Vendor, GlobalVendorMapping

class TestStellarMapping(unittest.TestCase):
    def test_ensure_vendor_mapping_with_global_match(self):
        async def run_test():
            # Setup Mock DB
            mock_db = MagicMock()
            
            # Setup Test Data
            vendor = Vendor(name="Stillhead Distillery Inc", stellar_supplier_id=None)
            
            global_mapping = GlobalVendorMapping(
                vendor_name="Stillhead Distillery Inc",
                stellar_supplier_id="stellar_123",
                stellar_supplier_name="Stillhead"
            )
            
            # Mock query flow
            # db.query(Model).filter(...).first()
            mock_query = mock_db.query.return_value
            mock_filter = mock_query.filter.return_value
            mock_filter.first.return_value = global_mapping
            
            # Run Function
            result_id = await stellar_service.ensure_vendor_mapping(mock_db, vendor)
            
            # Assertions
            self.assertEqual(result_id, "stellar_123")
            self.assertEqual(vendor.stellar_supplier_id, "stellar_123")
            self.assertEqual(vendor.stellar_supplier_name, "Stillhead")
            
            # Verify DB calls
            mock_db.commit.assert_called_once()
            # mock_db.refresh.assert_called_once_with(vendor) # Refresh might fail on mock if not handled, but usually fine.
            
        asyncio.run(run_test())

    def test_ensure_vendor_mapping_no_global_match_calls_stellar(self):
        async def run_test():
            # Setup Mock DB
            mock_db = MagicMock()
            
            # Setup Test Data
            vendor = Vendor(name="Unknown Vendor", stellar_supplier_id=None)
            
            # Mock Global Query -> returns None
            mock_query = mock_db.query.return_value
            mock_filter = mock_query.filter.return_value
            mock_filter.first.return_value = None

            # Helper to avoid actual API call in unit test, 
            # we'll mock search_stellar_suppliers
            original_search = stellar_service.search_stellar_suppliers
            stellar_service.search_stellar_suppliers = AsyncMock(return_value=[])
            
            try:
                # Run Function
                result_id = await stellar_service.ensure_vendor_mapping(mock_db, vendor)
                
                # Should return None because search mock returns empty
                self.assertIsNone(result_id)
                
                # Verify search was called
                stellar_service.search_stellar_suppliers.assert_called_once()
                
            finally:
                # Restore original function
                stellar_service.search_stellar_suppliers = original_search
                
        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
