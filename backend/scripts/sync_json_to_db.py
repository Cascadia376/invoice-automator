import asyncio
import os
import sys
import logging
import json
import glob
from dotenv import load_dotenv

load_dotenv()

# Force NullPool for script usage to prevent connection exhaustion
os.environ["DB_POOL_DISABLE"] = "true"

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from services import stellar_service

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('sync_stellar_db.log')
    ]
)
logger = logging.getLogger(__name__)

def sync_data():
    db = SessionLocal() # One session might be fine with NullPool, but let's be safe
    
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "stellar_invoices")
    files = glob.glob(os.path.join(data_dir, "*.json"))
    
    logger.info(f"Starting DB Sync for {len(files)} invoices...")
    
    success_count = 0
    fail_count = 0
    
    # Sort files to process in order
    files.sort()
    
    try:
        for fpath in files:
            try:
                asn = os.path.basename(fpath).replace('.json', '')
                
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Check for error responses stored as JSON
                if "status" in data and not isinstance(data.get("status"), (str, bool)): 
                     # Sometimes API returns {status: 404, message: ...}
                     if data.get("status") != 200 and not data.get("result"):
                         logger.warning(f"Skipping {asn}: Invalid data content")
                         continue

                # Sync using service
                # We use a nested transaction or just commit per item (service does commit)
                invoice = stellar_service.sync_stellar_data_to_db(asn, data, db)
                
                logger.info(f"  Synced {asn} -> inv#{invoice.supplier_invoice_number}")
                success_count += 1
                
            except Exception as e:
                logger.error(f"  Error syncing {fpath}: {e}")
                fail_count += 1
                db.rollback() # Ensure session is clean for next item
                
    finally:
        db.close()
        
    logger.info(f"Sync Complete. Success: {success_count}, Failed: {fail_count}")

if __name__ == "__main__":
    sync_data()
