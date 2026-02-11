import unittest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
import models
from services.automation_service import AutomationService

class TestAutomationService(unittest.TestCase):
    def setUp(self):
        # Use in-memory SQLite for testing
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()
        
        # Patch dependencies
        self.patcher_graph = patch('services.automation_service.GraphService')
        self.patcher_ingest = patch('services.automation_service.process_invoice')
        
        self.mock_graph = self.patcher_graph.start()
        self.mock_ingest = self.patcher_ingest.start()
        
        # Setup environment variables
        with patch.dict('os.environ', {
            'WATCHED_EMAIL': 'test@example.com',
            'AZURE_CLIENT_ID': 'fake-id',
            'AZURE_CLIENT_SECRET': 'fake-secret',
            'AZURE_TENANT_ID': 'fake-tenant'
        }):
            self.service = AutomationService(self.db)

    def tearDown(self):
        self.patcher_graph.stop()
        self.patcher_ingest.stop()
        self.db.close()

    def test_sync_email_invoices(self):
        # Mock Graph response
        self.service.graph.list_unread_emails_with_attachments.return_value = [
            {'id': 'msg1', 'subject': 'Invoice 123'}
        ]
        self.service.graph.get_message_attachments.return_value = [
            {'id': 'att1', 'name': 'invoice.pdf', 'contentType': 'application/pdf'}
        ]
        self.service.graph.download_attachment.return_value = b"%PDF-1.4 mock content"

        # Run sync
        self.service.sync_email_invoices()

        # Verify
        self.service.graph.list_unread_emails_with_attachments.assert_called_once()
        self.service.graph.download_attachment.assert_called_once_with('test@example.com', 'msg1', 'att1')
        self.mock_ingest.assert_called_once()
        self.service.graph.mark_as_read.assert_called_once_with('test@example.com', 'msg1')

    def test_sync_onedrive_invoices(self):
        # Mock Graph response for Delta Query
        self.service.graph.get_drive_delta.return_value = {
            'value': [
                {'id': 'file1', 'name': 'new_invoice.pdf'}
            ],
            '@odata.deltaLink': 'https://graph.microsoft.com/v1.0/delta/next'
        }
        self.service.graph.download_drive_item.return_value = b"%PDF-1.4 mock content"

        # Run sync
        self.service.sync_onedrive_invoices()

        # Verify
        self.service.graph.get_drive_delta.assert_called_once()
        self.service.graph.download_drive_item.assert_called_once_with('test@example.com', 'file1')
        self.mock_ingest.assert_called_once()
        
        # Check SyncState in DB
        state = self.db.query(models.SyncState).first()
        self.assertIsNotNone(state)
        self.assertEqual(state.delta_token, 'https://graph.microsoft.com/v1.0/delta/next')

if __name__ == "__main__":
    unittest.main()
