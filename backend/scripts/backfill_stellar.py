import asyncio
import os
import sys
import logging
import json
import time
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# We might import stellar_service, but we don't need database right now if just fetching
from services import stellar_service

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('backfill_stellar.log')
    ]
)
logger = logging.getLogger(__name__)

async def backfill():
    tenant = os.getenv("STELLAR_TENANT_ID") or "cascadialiquor"
    
    # Range from user request: 18333 to 18367 (Delta update)
    start_id = 18333
    end_id = 18367
    
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "stellar_invoices")
    
    logger.info(f"Starting Stellar Fetch (Save to JSON) for IDs {start_id} to {end_id}")
    
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    for i in range(start_id, end_id + 1):
        asn = f"SUPL-INV-2026-{i}"
        filepath = os.path.join(output_dir, f"{asn}.json")
        
        if os.path.exists(filepath):
            logger.info(f"Skipping {asn} (File exists)")
            skip_count += 1
            continue
            
        logger.info(f"Fetching {asn} ({i})...")
        
        try:
            # 1. Fetch from Stellar
            data = await stellar_service.retrieve_stellar_invoice(asn, tenant)
            
            # 2. Save to JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"  SUCCESS: Saved to {filepath}")
            success_count += 1
            
            # 3. Sleep to be polite
            await asyncio.sleep(0.5)
            
        except stellar_service.StellarError as e:
            if e.status_code == 404:
                logger.warning(f"  NOT FOUND: {asn} does not exist.")
            else:
                logger.error(f"  API ERROR: {str(e)}")
            fail_count += 1
        except Exception as e:
            logger.error(f"  UNEXPECTED ERROR: {str(e)}")
            fail_count += 1
            
    logger.info(f"Fetch Complete. Success: {success_count}, Skipped: {skip_count}, Failed: {fail_count}")

if __name__ == "__main__":
    asyncio.run(backfill())
