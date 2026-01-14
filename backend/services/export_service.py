import csv
import io
from models import Invoice

def generate_csv(invoice: Invoice) -> str:
    """
    Generates a CSV string for the given invoice.
    Format: Standard Import (SKU, Qty, Cost, Total)
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow([
        "SKU", 
        "Receiving Qty (UOM)", 
        "Confirmed total"
    ])
    
    for item in invoice.line_items:
        writer.writerow([
            item.sku or "",
            item.quantity,
            f"{item.amount:.2f}" if item.amount is not None else ""
        ])
        
    return output.getvalue()
