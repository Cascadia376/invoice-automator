import sys
import os

# Set dummy DATABASE_URL for verification (avoids import error in database.py)
os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost/dbname"
os.environ["AWS_BUCKET_NAME"] = "test-bucket" # Avoid warning loop

# Explicitly add the invoice-automator backend to path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
print(f"VERIFY: Adding {backend_path} to sys.path")
sys.path.append(backend_path)

try:
    print("VERIFY: Importing new modules...")
    import jobs
    import stellar_client
    from services import storage
    
    print("VERIFY: Checking Job Manager...")
    if not hasattr(jobs.job_manager, 'enqueue'):
        raise Exception("Job Manager missing 'enqueue' method")
        
    print("VERIFY: Checking Stellar Client...")
    if not hasattr(stellar_client.stellar_client, 'post_invoice'):
        raise Exception("Stellar Client missing 'post_invoice' method")
        
    print("VERIFY: Checking Storage Client...")
    if not hasattr(storage.storage_client, 'upload'):
        raise Exception("Storage Client missing 'upload' method")
        
    print("VERIFY: Checking Backward Compatibility...")
    if not hasattr(storage, 'upload_file'):
        raise Exception("Storage module missing legacy 'upload_file' function")

    print("SUCCESS: All new modules verified.")
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)
