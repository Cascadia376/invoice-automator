from intuitlib.client import AuthClient
from quickbooks import QuickBooks
from quickbooks.objects.bill import Bill
from quickbooks.objects.detailline import DetailLine
from quickbooks.objects.account import Account
from quickbooks.objects.vendor import Vendor
from quickbooks.objects.item import Item
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import models
import os

# Hardcoded for MVP, should be env vars
CLIENT_ID = "ABNgYeOxyxJRABMi1OHc7zL1CpHnQZW87yvypeyPD5upigyM83"
CLIENT_SECRET = "RhtCZdcNVxt2ESR9yHKYSsyLJU8uyI1wf9fJZeTw"
REDIRECT_URI = "http://localhost:8000/api/auth/qbo/callback"
ENVIRONMENT = "sandbox" # or "production"

def get_auth_client():
    return AuthClient(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        environment=ENVIRONMENT,
        redirect_uri=REDIRECT_URI,
    )

def get_auth_url():
    auth_client = get_auth_client()
    scopes = [
        "com.intuit.quickbooks.accounting", 
        "openid", 
        "profile", 
        "email", 
        "phone", 
        "address"
    ]
    return auth_client.get_authorization_url(scopes)

def handle_callback(code: str, realm_id: str, db: Session, org_id: str):
    auth_client = get_auth_client()
    auth_client.get_bearer_token(code, realm_id=realm_id)
    
    # Save to DB
    # Save to DB
    credentials = db.query(models.QBOCredentials).filter(
        models.QBOCredentials.realm_id == realm_id,
        models.QBOCredentials.organization_id == org_id
    ).first()
    if not credentials:
        credentials = models.QBOCredentials(realm_id=realm_id, organization_id=org_id)
        db.add(credentials)
    
    credentials.access_token = auth_client.access_token
    credentials.refresh_token = auth_client.refresh_token
    # QBO tokens expire in 60 mins (access) and 100 days (refresh)
    # We'll set approximate expiry times
    credentials.access_token_expires_at = datetime.utcnow() + timedelta(minutes=55) 
    credentials.refresh_token_expires_at = datetime.utcnow() + timedelta(days=99)
    credentials.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(credentials)
    return credentials

def get_client(realm_id: str, db: Session, org_id: str):
    credentials = db.query(models.QBOCredentials).filter(
        models.QBOCredentials.realm_id == realm_id,
        models.QBOCredentials.organization_id == org_id
    ).first()
    if not credentials:
        raise Exception("No QBO credentials found for this company")
    
    auth_client = get_auth_client()
    
    # Refresh if needed
    if credentials.access_token_expires_at and datetime.utcnow() > credentials.access_token_expires_at:
        try:
            auth_client.refresh(refresh_token=credentials.refresh_token)
            
            credentials.access_token = auth_client.access_token
            credentials.refresh_token = auth_client.refresh_token
            credentials.access_token_expires_at = datetime.utcnow() + timedelta(minutes=55)
            credentials.refresh_token_expires_at = datetime.utcnow() + timedelta(days=99)
            credentials.updated_at = datetime.utcnow()
            db.commit()
        except Exception as e:
            print(f"Error refreshing token: {e}")
            raise Exception("Failed to refresh QBO token. Please reconnect.")
    else:
        auth_client.access_token = credentials.access_token
        auth_client.refresh_token = credentials.refresh_token
        auth_client.realm_id = credentials.realm_id
    
    return QuickBooks(
        auth_client=auth_client,
        refresh_token=credentials.refresh_token,
        company_id=credentials.realm_id,
    )

def create_bill(invoice_id: str, db: Session, org_id: str):
    invoice = db.query(models.Invoice).filter(
        models.Invoice.id == invoice_id,
        models.Invoice.organization_id == org_id
    ).first()
    if not invoice:
        raise Exception("Invoice not found")
    
    # For MVP, we assume there's only one connected QBO company per org
    credentials = db.query(models.QBOCredentials).filter(models.QBOCredentials.organization_id == org_id).first()
    if not credentials:
        raise Exception("Not connected to QuickBooks")
    
    client = get_client(credentials.realm_id, db, org_id)
    
    # 1. Find or Create Vendor
    vendor_name = invoice.vendor_name or "Unknown Vendor"
    vendors = Vendor.filter(Active=True, DisplayName=vendor_name, qb=client)
    if vendors:
        vendor_ref = vendors[0].Id
    else:
        # Create new vendor
        new_vendor = Vendor()
        new_vendor.DisplayName = vendor_name
        new_vendor.save(qb=client)
        vendor_ref = new_vendor.Id
        
    # 2. Create Bill Lines
    lines = []
    for item in invoice.line_items:
        detail_line = DetailLine()
        detail_line.Amount = item.amount
        detail_line.DetailType = "AccountBasedExpenseLineDetail"
        
        # Account Logic
        # If we have a category_gl_code, try to find an account with that Name or Id
        # For MVP, we'll try to match by Name first, then fall back to a default "Uncategorized Expense"
        
        account_ref = None
        if item.category_gl_code:
            # Try to find account by name (e.g. "6010 - Marketing")
            # We might need to parse the code out if QBO expects just the code or name
            # QBO Query: select * from Account where Name = '...'
            accounts = Account.filter(Name=item.category_gl_code, qb=client)
            if accounts:
                account_ref = accounts[0].Id
        
        if not account_ref:
            # Fallback: Find "Uncategorized Expense" or create it
            accounts = Account.filter(Name="Uncategorized Expense", qb=client)
            if accounts:
                account_ref = accounts[0].Id
            else:
                # Create default expense account
                # This is risky without more info, so maybe we just fail or use the first expense account?
                # Let's try to find ANY expense account
                expense_accounts = Account.query("select * from Account where AccountType = 'Expense' MAXRESULTS 1", qb=client)
                if expense_accounts:
                    account_ref = expense_accounts[0].Id
                else:
                    raise Exception("No Expense accounts found in QBO to map to.")

        detail_line.AccountBasedExpenseLineDetail = {
            "AccountRef": {
                "value": account_ref
            },
            "CustomerRef": {
                "value": vendor_ref 
            },
            "BillableStatus": "NotBillable"
        }
        
        # Add description
        detail_line.Description = f"{item.sku or ''} {item.description}"
        lines.append(detail_line)
        
    # 3. Create Bill
    bill = Bill()
    bill.VendorRef = {"value": vendor_ref}
    bill.Line = lines
    bill.DocNumber = invoice.invoice_number
    
    # Date format YYYY-MM-DD
    if invoice.date:
        try:
            # Ensure date is in YYYY-MM-DD
            # If invoice.date is already string YYYY-MM-DD, good.
            # If it's datetime, format it.
            # Our model says String, so we assume it's ISO or similar.
            bill.TxnDate = invoice.date
        except:
            pass
            
    bill.save(qb=client)
    
    return bill
