import requests
import os

def upload_invoice():
    url = "http://localhost:8001/api/invoices/upload"
    files = {'file': open('test_invoice.pdf', 'rb')}
    
    print(f"Uploading to {url}...")
    try:
        response = requests.post(url, files=files)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Failed to upload: {e}")

if __name__ == "__main__":
    upload_invoice()
