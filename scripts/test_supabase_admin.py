import os
import sys
from supabase import create_client, Client
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_supabase_connection():
    print("\n--- Supabase Admin Connection Test ---\n")
    
    # 1. Get Credentials
    url = input("Enter SUPABASE_URL: ").strip()
    if not url:
        print("Error: URL is required.")
        return

    key = input("Enter SUPABASE_SERVICE_ROLE_KEY (hidden input not supported here, just paste it): ").strip()
    if not key:
        print("Error: Key is required.")
        return

    print("\n[INFO] Initializing Supabase Client...")
    
    try:
        supabase: Client = create_client(url, key)
        
        print("[INFO] Client initialized. Attempting to list users...")
        
        # 2. Fetch Users
        # Try different pagination methods to be robust against library versions
        try:
            response = supabase.auth.admin.list_users(page=1, per_page=10)
            
            # Identify response structure
            if isinstance(response, list):
                users = response
            elif hasattr(response, 'users'):
                users = response.users
            else:
                print(f"[WARN] Unknown response type: {type(response)}")
                print(f"[DEBUG] Response: {response}")
                users = []

            print(f"\n[SUCCESS] Connection Successful!")
            print(f"[INFO] Found {len(users)} users in the response (page 1).")
            
            if len(users) == 0:
                print("[WARN] User list is EMPTY. This explains why the dashboard is empty.")
                print("       - Are you sure this is the correct project?")
                print("       - Did you create users in the 'Authentication' tab of this specific Supabase project?")
            else:
                print("\nCannot display full list for privacy, but here are the first 3 Emails:")
                for i, u in enumerate(users[:3]):
                    print(f"  {i+1}. {u.email} (ID: {u.id})")

        except Exception as api_error:
            print(f"\n[FATAL] API Call Failed: {api_error}")
            print("       - This often means the SERVICE_ROLE_KEY is invalid or lacks permissions.")

    except Exception as e:
        print(f"\n[FATAL] Client Initialization Failed: {e}")

if __name__ == "__main__":
    try:
        test_supabase_connection()
    except KeyboardInterrupt:
        print("\nTest cancelled.")
