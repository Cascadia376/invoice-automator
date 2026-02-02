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

async def fetch_one(i, sem, tenant, output_dir):
    async with sem:
        asn = f"SUPL-INV-2026-{i}"
        filepath = os.path.join(output_dir, f"{asn}.json")
        
        if os.path.exists(filepath):
            # logger.info(f"Skipping {asn} (File exists)")
            return "skipped"
            
        logger.info(f"Fetching {asn}...")
        try:
            data = await stellar_service.retrieve_stellar_invoice(asn, tenant)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            # logger.info(f"  SUCCESS: {asn}")
            return "success"
        except stellar_service.StellarError as e:
            if e.status_code == 404:
                return "not_found"
            else:
                logger.error(f"  API ERROR {asn}: {str(e)}")
                return "failed"
        except Exception as e:
            logger.error(f"  ERROR {asn}: {str(e)}")
            return "failed"

async def backfill():
    tenant = os.getenv("STELLAR_TENANT_ID") or "cascadialiquor"
    
    # Range from user request: 17667 to 18367 (Missing chunk)
    start_id = 17667
    end_id = 18367
    
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "stellar_invoices")
    
    logger.info(f"Starting Parallel Stellar Fetch for IDs {start_id} to {end_id}")
    
    sem = asyncio.Semaphore(10) # 10 concurrent requests
    tasks = []
    
    for i in range(start_id, end_id + 1):
        tasks.append(fetch_one(i, sem, tenant, output_dir))
    
    results = await asyncio.gather(*tasks)
    
    success = results.count("success")
    skipped = results.count("skipped")
    failed = results.count("failed")
    not_found = results.count("not_found")
    
    logger.info(f"Fetch Complete. Success: {success}, Skipped: {skipped}, Failed: {failed}, Not Found: {not_found}")

if __name__ == "__main__":
    asyncio.run(backfill())
