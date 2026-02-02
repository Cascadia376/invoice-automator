
import os
import requests
from dotenv import load_dotenv

# Load from correct path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(root_dir, '.env'))

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Range": "0-0",
    "Prefer": "count=exact"
}

resp = requests.get(f"{url}/rest/v1/stellar_sku_categories", headers=headers)
print(f"Status: {resp.status_code}")
print(f"Content-Range: {resp.headers.get('Content-Range')}")
