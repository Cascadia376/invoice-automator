import os
import json
import csv
import glob
from datetime import datetime

def generate_report():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "stellar_invoices")
    output_file = "receiving_summary_jan_2026_v3.csv"
    
    files = glob.glob(os.path.join(data_dir, "*.json"))
    print(f"Found {len(files)} invoice files.")
    
    # Load Category Map
    cat_map_file = os.path.join(data_dir, "sku_categories.json")
    sku_map = {}
    if os.path.exists(cat_map_file):
        with open(cat_map_file, 'r') as f:
            sku_map = json.load(f)
            
    print(f"Loaded {len(sku_map)} SKU categories.")
    
    invoices = []
    grand_total_sum = 0.0
    
    # Category Buckets
    # BEER, WINE, LIQUOR, COOLERS+CIDER, OTHER
    
    for fpath in files:
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Unwrap
            result = data.get('result', {})
            inv = result.get('supplierInvoice', {})
            items = result.get('supplierInvoiceItems', [])
            
            # Extract fields
            sys_id = inv.get('name', os.path.basename(fpath).replace('.json',''))
            supp_inv_no = inv.get('supplier_invoice_no') or inv.get('supplierInvoiceNumber') or ""
            supplier = inv.get('supplier_name', "Unknown")
            
            # Dates
            rec_date = inv.get('lastReceivedAt') or inv.get('completedAt') or inv.get('createdAt')
            if rec_date:
                try:
                    dt = datetime.fromisoformat(rec_date.replace('Z', '+00:00'))
                    rec_date = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
            
            subtotal = float(inv.get('subTotal') or 0.0)
            taxes = float(inv.get('totalTaxes') or inv.get('total_tax') or 0.0)
            deposits = float(inv.get('totalDeposits') or inv.get('total_deposit') or 0.0)
            total = float(inv.get('grandTotal') or inv.get('invoice_total') or 0.0)
            
            grand_total_sum += total
            
            # Calculate Category Subtotals
            cat_totals = {
                "Beer": 0.0,
                "Wine": 0.0,
                "Spirits": 0.0,
                "Refreshment": 0.0,
                "Other": 0.0
            }
            
            for item in items:
                # Calculate cost manually as total_cost field is missing
                qty = float(item.get('shipped_qty_received') or item.get('shipped_qty') or 0.0)
                price = float(item.get('unit_price_received') or item.get('unit_price') or 0.0)
                cost = qty * price
                
                sku = str(item.get('sku') or '')
                cat = sku_map.get(sku, "UNKNOWN").upper()
                
                if cat == "BEER":
                    cat_totals["Beer"] += cost
                elif cat == "WINE":
                    cat_totals["Wine"] += cost
                elif cat in ["LIQUOR", "SPIRITS"]:
                    cat_totals["Spirits"] += cost
                elif cat in ["COOLERS", "CIDER"]:
                    cat_totals["Refreshment"] += cost
                else:
                    cat_totals["Other"] += cost
            
            row = {
                "System ID": sys_id,
                "Supplier Invoice #": supp_inv_no,
                "Supplier": supplier,
                "Received Date": rec_date,
                "Store": inv.get('target_warehouse_address') or inv.get('location_name') or "",
                
                "Beer": cat_totals["Beer"],
                "Wine": cat_totals["Wine"],
                "Spirits": cat_totals["Spirits"],
                "Refreshment": cat_totals["Refreshment"],
                "Other": cat_totals["Other"],
                
                "Subtotal": subtotal,
                "Tax": taxes,
                "Deposit": deposits,
                "Total": total
            }
            
            invoices.append(row)
            
        except Exception as e:
            print(f"Error processing {fpath}: {e}")

    # Sort by System ID
    invoices.sort(key=lambda x: x['System ID'])
    
    # Write CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            "System ID", "Supplier Invoice #", "Supplier", "Store", "Received Date", 
            "Beer", "Wine", "Spirits", "Refreshment", "Other",
            "Subtotal", "Tax", "Deposit", "Total"
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for row in invoices:
            writer.writerow(row)
            
    print(f"Generated {output_file} with {len(invoices)} rows.")
    print(f"Total Value: ${grand_total_sum:,.2f}")

if __name__ == "__main__":
    generate_report()
