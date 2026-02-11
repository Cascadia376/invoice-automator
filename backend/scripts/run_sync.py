"""
Manual script to trigger external automation sync.
"""
import os
import sys
import logging
from database import SessionLocal
from services.automation_service import AutomationService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_sync():
    db = SessionLocal()
    try:
        service = AutomationService(db)
        logger.info("Starting Manual Email Sync...")
        service.sync_email_invoices()
        
        logger.info("Starting Manual OneDrive Sync...")
        service.sync_onedrive_invoices()
        
        logger.info("Sync Complete.")
    finally:
        db.close()

if __name__ == "__main__":
    run_sync()
