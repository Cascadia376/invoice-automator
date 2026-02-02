
import csv
import io
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import models

def generate_receiving_summary_csv(db: Session, start_date: datetime, end_date: datetime) -> str:
    # 1. Fetch Invoices in Range
    # We use date_received if available, else created_date
    query = text("""
        SELECT 
            i.invoice_id,
            i.supplier_invoice_number,
            i.supplier_name,
            i.date_received,
            i.store_name,
            i.sub_total,
            i.total_taxes,
            i.total_deposits,
            i.invoice_total
        FROM supplier_invoices i
        WHERE i.date_received >= :start AND i.date_received <= :end
        ORDER BY i.date_received ASC
    """)
    
    invoices = db.execute(query, {"start": start_date, "end": end_date}).fetchall()
    
    if not invoices:
        return ""

    # 2. Fetch Items for these invoices
    invoice_ids = [inv.invoice_id for inv in invoices]
    # Fetch all items
    # We also join with stellar_sku_categories to get category
    # Note: We need to use Raw SQL or Models. 
    # Let's assume we created the table via SQL but didn't make a Model yet.
    # We can join manually or add Model.
    # Using Raw SQL for speed and simple join.
    
    items_query = text("""
        SELECT 
            it.invoice_id,
            it.sku,
            it.total_cost,
            c.category
        FROM supplier_invoice_items it
        LEFT JOIN stellar_sku_categories c ON it.sku = c.sku
        WHERE it.invoice_id = ANY(:ids)
    """)
    
    # Batch if too many? 1300 invoices is okay for ANY(:ids) usually.
    items = db.execute(items_query, {"ids": invoice_ids}).fetchall()
    
    # 3. Group Items by Invoice
    items_by_invoice = {}
    for it in items:
        if it.invoice_id not in items_by_invoice:
            items_by_invoice[it.invoice_id] = []
        items_by_invoice[it.invoice_id].append(it)
        
    # 4. Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    headers = [
        "System ID", "Supplier Invoice #", "Supplier", "Store", "Received Date",
        "Beer", "Wine", "Spirits", "Refreshment", "Other",
        "Subtotal", "Tax", "Deposit", "Total"
    ]
    writer.writerow(headers)
    
    grand_total_sum = 0.0
    
    for inv in invoices:
        inv_items = items_by_invoice.get(inv.invoice_id, [])
        
        # Calculate Category Totals
        cat_totals = {
            "Beer": 0.0,
            "Wine": 0.0,
            "Spirits": 0.0,
            "Refreshment": 0.0,
            "Other": 0.0
        }
        
        for item in inv_items:
            cost = float(item.total_cost or 0.0)
            cat = (item.category or "UNKNOWN").upper()
            
            if "BEER" in cat:
                cat_totals["Beer"] += cost
            elif "WINE" in cat:
                cat_totals["Wine"] += cost
            elif "LIQUOR" in cat or "SPIRITS" in cat:
                cat_totals["Spirits"] += cost
            elif "COOLERS" in cat or "CIDER" in cat or "REFRESHMENT" in cat:
                cat_totals["Refreshment"] += cost
            else:
                cat_totals["Other"] += cost
        
        # Prepare Row
        rec_date = inv.date_received.strftime('%Y-%m-%d %H:%M') if inv.date_received else ""
        
        row = [
            inv.invoice_id,
            inv.supplier_invoice_number,
            inv.supplier_name,
            inv.store_name,
            rec_date,
            f"{cat_totals['Beer']:.2f}",
            f"{cat_totals['Wine']:.2f}",
            f"{cat_totals['Spirits']:.2f}",
            f"{cat_totals['Refreshment']:.2f}",
            f"{cat_totals['Other']:.2f}",
            f"{inv.sub_total or 0:.2f}",
            f"{inv.total_taxes or 0:.2f}",
            f"{inv.total_deposits or 0:.2f}",
            f"{inv.invoice_total or 0:.2f}"
        ]
        
        writer.writerow(row)
        grand_total_sum += (inv.invoice_total or 0.0)
        
    return output.getvalue()
