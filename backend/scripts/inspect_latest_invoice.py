import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load env from root
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(root_dir, ".env"))

from database import SessionLocal
import models
from sqlalchemy import desc

def inspect_latest():
    db = SessionLocal()
    try:
        # Get latest invoice
        invoice = db.query(models.Invoice).order_by(desc(models.Invoice.created_at)).first()
        if not invoice:
            print("No invoices found.")
            return

        print(f"=== Latest Invoice: {invoice.invoice_number} ===")
        print(f"ID: {invoice.id}")
        print(f"Vendor: {invoice.vendor_name}")
        print(f"Organization: {invoice.organization_id}")
        print(f"Date: {invoice.date}")
        print(f"Status: {invoice.status}")
        print(f"Is Posted: {invoice.is_posted}")
        print(f"Stellar ASN: {invoice.stellar_asn_number}")
        print(f"Line Items: {len(invoice.line_items)}")
        
        # Check Vendor Config
        vendor = db.query(models.Vendor).filter(models.Vendor.name == invoice.vendor_name).first()
        print(f"\n=== Vendor Config: {invoice.vendor_name} ===")
        if vendor:
            print(f"Vendor ID: {vendor.id}")
            print(f"Stellar Supplier ID: {vendor.stellar_supplier_id}")
            print(f"Stellar Supplier Name: {vendor.stellar_supplier_name}")
        else:
            print("VENDOR RECORD NOT FOUND")

        # Check Store Config
        store = db.query(models.Store).filter(models.Store.organization_id == invoice.organization_id).first()
        print(f"\n=== Store Config ({invoice.organization_id}) ===")
        if store:
            print(f"Store Name: {store.name}")
            print(f"Stellar Tenant: {store.stellar_tenant}")
            print(f"Stellar Location ID: {store.stellar_location_id}")
            print(f"Stellar Enabled: {store.stellar_enabled}")
        else:
            print("STORE RECORD NOT FOUND")

    finally:
        db.close()

if __name__ == "__main__":
    inspect_latest()
