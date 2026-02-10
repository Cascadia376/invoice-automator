
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import os

# Set dummy DB URL before importing database module to avoid connection errors
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["DB_POOL_DISABLE"] = "true"

from services import stellar_service
import models

@pytest.mark.asyncio
async def test_sync_stellar_suppliers():
    # Mock search_stellar_suppliers to return 2 pages of results
    mock_items_page1 = [
        {"id": "sup-1", "name": "Supplier A", "code": "A001"},
        {"id": "sup-2", "name": "Supplier B", "code": "B002"}
    ]
    mock_items_page2 = [] # Empty second page to stop loop

    # Mock the DB session
    mock_db = MagicMock()
    
    # Mock existing supplier check (return None to simulate new)
    mock_db.query.return_value.filter.return_value.first.return_value = None

    # Patch the search function
    with patch("services.stellar_service.search_stellar_suppliers", new_callable=AsyncMock) as mock_search:
        mock_search.side_effect = [mock_items_page1, mock_items_page2]
        
        # Patch config to avoid error
        with patch("services.stellar_service.STELLAR_API_TOKEN", "fake-token"):
            
            stats = await stellar_service.sync_stellar_suppliers(mock_db, "test-tenant")
            
            # Assertions
            assert stats["added"] == 2
            assert stats["total"] == 2
            
            # Verify DB adds
            assert mock_db.add.call_count == 2
            # Check first call arg
            args, _ = mock_db.add.call_args_list[0]
            supplier = args[0]
            assert isinstance(supplier, models.StellarSupplier)
            assert supplier.id == "sup-1"
            assert supplier.name == "Supplier A"
            assert supplier.tenant_id == "test-tenant"

            # Verify commit called
            assert mock_db.commit.call_count >= 1
