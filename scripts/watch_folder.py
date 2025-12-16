import sys
import time
import os
import requests
import shutil
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv

# Load config
load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000/api")
API_KEY = os.getenv("SERVICE_API_KEY")
WATCH_DIR = os.getenv("WATCH_DIR", str(Path.home() / "Documents/Invoices/Input"))
PROCESSED_DIR = os.getenv("PROCESSED_DIR", str(Path.home() / "Documents/Invoices/Processed"))
ERROR_DIR = os.getenv("ERROR_DIR", str(Path.home() / "Documents/Invoices/Error"))

if not API_KEY:
    print("Error: SERVICE_API_KEY not found in environment variables.")
    print("Please create a .env file with SERVICE_API_KEY defined.")
    sys.exit(1)

class InvoiceHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        
        filename = event.src_path
        if filename.lower().endswith('.pdf') or filename.lower().endswith('.png') or filename.lower().endswith('.jpg'):
            print(f"New file file detected: {filename}")
            self.process_file(filename)

    def process_file(self, filepath):
        # Wait a moment for file copy to complete
        time.sleep(1)
        
        file_path = Path(filepath)
        print(f"Uploading {file_path.name}...")

        try:
            with open(file_path, 'rb') as f:
                response = requests.post(
                    f"{API_URL}/invoices/upload",
                    headers={"X-API-Key": API_KEY},
                    files={"file": f}
                )

            if response.status_code == 200:
                print(f"✅ Upload Success! Invoice ID: {response.json().get('id')}")
                self.move_file(file_path, PROCESSED_DIR)
            else:
                print(f"❌ Upload Failed: {response.text}")
                self.move_file(file_path, ERROR_DIR)

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            self.move_file(file_path, ERROR_DIR)

    def move_file(self, src_path: Path, dest_dir: str):
        Path(dest_dir).mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(src_path), os.path.join(dest_dir, src_path.name))
            print(f"-> Moved to {dest_dir}")
        except Exception as e:
            print(f"-> Failed to move file: {e}")

if __name__ == "__main__":
    print(f"📂 Swift Invoice Zen - Folder Watcher")
    print(f"-------------------------------------")
    print(f"Watching:  {WATCH_DIR}")
    print(f"Processed: {PROCESSED_DIR}")
    print(f"Target:    {API_URL}")
    print(f"-------------------------------------")

    # Ensure directories exist
    Path(WATCH_DIR).mkdir(parents=True, exist_ok=True)
    Path(PROCESSED_DIR).mkdir(parents=True, exist_ok=True)
    Path(ERROR_DIR).mkdir(parents=True, exist_ok=True)

    event_handler = InvoiceHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
