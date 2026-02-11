import os
import logging
import tempfile
from sqlalchemy.orm import Session
from datetime import datetime
from services.graph_service import GraphService
from services.ingestion_service import process_invoice
import models

logger = logging.getLogger(__name__)

class AutomationService:
    def __init__(self, db: Session):
        self.db = db
        self.graph = GraphService()
        # In a real app, these would come from organization settings in DB
        self.watched_email = os.getenv("WATCHED_EMAIL") 
        self.org_id = os.getenv("DEFAULT_ORG_ID", "dev-org")
        self.user_id = os.getenv("DEFAULT_USER_ID", "system")

    def sync_email_invoices(self):
        """Watch inbox for emails with PDF attachments."""
        if not self.watched_email:
            logger.warning("No WATCHED_EMAIL configured.")
            return

        logger.info(f"Syncing email invoices for {self.watched_email}...")
        try:
            messages = self.graph.list_unread_emails_with_attachments(self.watched_email)
            for msg in messages:
                logger.info(f"Processing email: {msg['subject']}")
                attachments = self.graph.get_message_attachments(self.watched_email, msg['id'])
                
                for attachment in attachments:
                    if attachment.get('contentType') == 'application/pdf' or attachment.get('name', '').lower().endswith('.pdf'):
                        self._process_graph_attachment(msg, attachment)
                
                # Mark as read after processing all attachments
                self.graph.mark_as_read(self.watched_email, msg['id'])
        except Exception as e:
            logger.error(f"Error syncing emails: {e}")

    def sync_onedrive_invoices(self):
        """Watch OneDrive for new PDF files via Delta Query."""
        if not self.watched_email:
            logger.warning("No WATCHED_EMAIL (for OneDrive user) configured.")
            return

        logger.info(f"Syncing OneDrive invoices for {self.watched_email}...")
        
        # Get last delta link for this org
        sync_state = self.db.query(models.SyncState).filter(
            models.SyncState.id == "onedrive_invoices",
            models.SyncState.organization_id == self.org_id
        ).first()

        delta_link = sync_state.delta_token if sync_state else None

        try:
            delta_result = self.graph.get_drive_delta(self.watched_email, delta_link)
            
            items = delta_result.get("value", [])
            for item in items:
                # Skip folders and deletions
                if "folder" in item or "deleted" in item:
                    continue
                
                # Only process PDFs
                if item.get("name", "").lower().endswith(".pdf"):
                    logger.info(f"Found new OneDrive invoice: {item['name']}")
                    self._process_drive_item(item)

            # Save next delta link
            next_link = delta_result.get("@odata.deltaLink")
            if next_link:
                if not sync_state:
                    sync_state = models.SyncState(
                        id="onedrive_invoices", 
                        organization_id=self.org_id,
                        delta_token=next_link
                    )
                    self.db.add(sync_state)
                else:
                    sync_state.delta_token = next_link
                    sync_state.last_sync_at = datetime.utcnow()
                
                self.db.commit()

        except Exception as e:
            logger.error(f"Error syncing OneDrive: {e}")

    def _process_graph_attachment(self, msg: dict, attachment: dict):
        """Download and ingest an email attachment."""
        content = self.graph.download_attachment(self.watched_email, msg['id'], attachment['id'])
        self._ingest_bytes(content, attachment.get('name', 'invoice.pdf'))

    def _process_drive_item(self, item: dict):
        """Download and ingest a OneDrive item."""
        content = self.graph.download_drive_item(self.watched_email, item['id'])
        self._ingest_bytes(content, item.get('name', 'invoice.pdf'))

    def _ingest_bytes(self, content: bytes, filename: str):
        """Common logic to save bytes to temp file and call ingestion service."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            process_invoice(
                self.db,
                tmp_path,
                self.org_id,
                self.user_id,
                original_filename=filename
            )
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
