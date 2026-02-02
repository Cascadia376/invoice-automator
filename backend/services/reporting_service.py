from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Optional
from datetime import datetime
import csv
from io import StringIO

import models

def generate_receiving_summary(
    db: Session,
    start_date: datetime,
    end_date: datetime,
    store_name: Optional[str] = None
) -> List[Dict]:
    """
    Generate the 'Receiving Summary' data based on Stellar sync results.
    Matches the user-provided Excel format.
    """
    query = db.query(models.SupplierInvoice).filter(
        models.SupplierInvoice.date_posted >= start_date,
        models.SupplierInvoice.date_posted <= end_date
    )
    
    if store_name:
        query = query.filter(models.SupplierInvoice.store_name == store_name)
        
    invoices = query.order_by(models.SupplierInvoice.date_posted).all()
    
    report_data = []
    for inv in invoices:
        report_data.append({
            "Supplier": inv.supplier_name,
            "Reference": inv.supplier_invoice_number,
            "Date": inv.date_posted.strftime("%Y-%m-%d") if inv.date_posted else "",
            "Subtotal": inv.sub_total or 0.0,
            "Non Line Item": inv.freight_fees or 0.0, # Mapping freight/fees to 'Non Line Item'
            "Deposit": inv.total_deposits or 0.0,
            "Tax": inv.total_taxes or 0.0,
            "Grand Total": inv.invoice_total or 0.0
        })
        
    return report_data

def export_summary_to_csv(data: List[Dict]) -> str:
    """Export the summary data to a CSV string."""
    if not data:
        return ""
        
    output = StringIO()
    keys = data[0].keys()
    writer = csv.DictWriter(output, fieldnames=keys)
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()
