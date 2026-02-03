import requests
import os
import sys

# Script to simulate an upload to localhost to test for 500 errors
# Usage: python simulate_upload.py <path_to_invoice.pdf> [auth_token]

def test_upload(file_path, token=None):
    url = "http://localhost:8000/api/invoices/upload"
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    # Mocking user context headers if needed by auth.py local logic
    # headers["x-organization-id"] = "dev-org" 

    print(f"Uploading {file_path} to {url}...")
    
    with open(file_path, "rb") as f:
        files = {"file": f}
        try:
            response = requests.post(url, files=files, headers=headers)
            print(f"Status Code: {response.status_code}")
            try:
                print("Response JSON:")
                print(response.json())
            except:
                print("Response Text:")
                print(response.text)
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python simulate_upload.py <path_to_invoice.pdf> [token]")
    else:
        file_path = sys.argv[1]
        token = sys.argv[2] if len(sys.argv) > 2 else os.getenv("SUPABASE_SERVICE_KEY")
        test_upload(file_path, token)
