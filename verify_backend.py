import sys
import subprocess
import time
import requests

def install_dependencies():
    print("Installing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "backend/requirements.txt"])

def start_backend():
    print("Starting backend...")
    # Start uvicorn in background
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return proc

def check_health():
    print("Checking API health...")
    for _ in range(10):
        try:
            response = requests.get("http://localhost:8000/api/invoices")
            if response.status_code == 200:
                print("Backend is up and running!")
                return True
        except requests.ConnectionError:
            time.sleep(1)
    return False

if __name__ == "__main__":
    try:
        install_dependencies()
        proc = start_backend()
        if check_health():
            print("Verification Successful")
        else:
            print("Verification Failed: Backend did not start")
        proc.terminate()
    except Exception as e:
        print(f"Verification Failed: {e}")
