from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_invoice(filename):
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    # Header
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, height - 50, "INVOICE")
    
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 80, "Vendor: Test Supply Co.")
    c.drawString(50, height - 100, "Date: 2025-01-15")
    c.drawString(50, height - 120, "Invoice #: INV-9999")

    # Line Items Header
    y = height - 160
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Description")
    c.drawString(300, y, "Qty")
    c.drawString(400, y, "Unit Cost")
    c.drawString(500, y, "Total")
    
    # Line Items
    items = [
        ("Widget A", 10, 5.00),
        ("Gadget B", 2, 12.50),
        ("Thingamajig C", 5, 2.00)
    ]
    
    y -= 25
    c.setFont("Helvetica", 12)
    total = 0
    for desc, qty, cost in items:
        line_total = qty * cost
        total += line_total
        
        c.drawString(50, y, desc)
        c.drawString(300, y, str(qty))
        c.drawString(400, y, f"${cost:.2f}")
        c.drawString(500, y, f"${line_total:.2f}")
        y -= 20

    # Summary
    y -= 20
    c.line(50, y, 550, y)
    y -= 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(400, y, "Subtotal:")
    c.drawString(500, y, f"${total:.2f}")
    
    gst = total * 0.05
    y -= 20
    c.drawString(400, y, "GST (5%):")
    c.drawString(500, y, f"${gst:.2f}")
    
    grand_total = total + gst
    y -= 20
    c.setFont("Helvetica-Bold", 14)
    c.drawString(400, y, "TOTAL:")
    c.drawString(500, y, f"${grand_total:.2f}")

    c.save()
    print(f"Created {filename}")

if __name__ == "__main__":
    create_invoice("test_invoice.pdf")
