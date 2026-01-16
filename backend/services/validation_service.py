from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Dict, List, Any
import models
import statistics

def validate_invoice(db: Session, invoice: models.Invoice) -> Dict[str, Any]:
    """
    Validates an invoice against historical data for the same vendor.
    Returns a dictionary of warnings.
    """
    warnings = {
        "global_warnings": [],
        "line_item_warnings": {} # key: line_item_id, value: list of warning strings
    }
    
    if not invoice or not invoice.vendor_name:
        return warnings

    # 1. Fetch History (Last 10 approved/processed invoices for this vendor)
    # We use vendor_name relative to organization to group.
    # Note: Ideally usage of vendor_id FK would be better, but assuming name matching for now based on current schema.
    history_query = db.query(models.Invoice).filter(
        models.Invoice.organization_id == invoice.organization_id,
        models.Invoice.vendor_name == invoice.vendor_name,
        models.Invoice.id != invoice.id, # Exclude current
        # models.Invoice.status == "processed" # Optional: only compare against finalized ones? For now, use all to have more data.
    ).order_by(desc(models.Invoice.created_at)).limit(20).all()

    if not history_query:
        # No history, cannot validate
        return warnings

    # --- Deterministic Validation (Math Checks) ---
    
    # 1. Footing Check (Lines Sum vs Subtotal)
    # Use subtotal if available, otherwise total_amount - tax - deposit
    target_total = invoice.subtotal if (invoice.subtotal and invoice.subtotal > 0) else invoice.total_amount
    
    calc_subtotal = sum([item.amount for item in invoice.line_items if item.amount is not None])
    
    if target_total and target_total > 0:
        diff = abs(calc_subtotal - target_total)
        # Allow small rounding tolerance (e.g. 0.05)
        if diff > 0.05:
            warnings["global_warnings"].append(
                f"Subtotal Mismatch: Line items sum to ${calc_subtotal:,.2f}, but invoice says ${target_total:,.2f} (Diff: ${diff:,.2f})"
            )

    # --- Historical/Statistical Validation ---
    historical_totals = [inv.total_amount for inv in history_query if inv.total_amount]
    if historical_totals:
        avg_total = statistics.mean(historical_totals)
        # Rule: Alert if > 2x average
        if invoice.total_amount and invoice.total_amount > (avg_total * 2.0) and invoice.total_amount > 100: # Threshold of $100 to avoid noise on small items
            percent_diff = int(((invoice.total_amount - avg_total) / avg_total) * 100)
            warnings["global_warnings"].append(
                f"High Invoice Total: ${invoice.total_amount:,.2f} is {percent_diff}% higher than average (${avg_total:,.2f})"
            )

    # --- Line Item Validation ---
    
    # Pre-fetch historical line items to build stats map
    # We need to map SKU (or Description if SKU is missing) to historical costs/quantities
    # Map: key -> { costs: [], quantities: [] }
    item_stats = {}
    
    for hist_inv in history_query:
        for item in hist_inv.line_items:
            # Key: SKU preferred, else Description
            key = item.sku if item.sku else item.description
            if not key:
                continue
            
            if key not in item_stats:
                item_stats[key] = {"costs": [], "quantities": []}
            
            if item.unit_cost is not None:
                item_stats[key]["costs"].append(item.unit_cost)
            if item.quantity is not None:
                item_stats[key]["quantities"].append(item.quantity)

    for item in invoice.line_items:
        item_key = item.sku if item.sku else item.description
        if not item_key:
            continue
            
        item_warnings = []
        
        # --- Deterministic Math Check ---
        if item.quantity is not None and item.unit_cost is not None and item.amount is not None:
             expected = item.quantity * item.unit_cost
             if abs(expected - item.amount) > 0.03: # 3 cents tolerance
                 item_warnings.append(f"Math Error: {item.quantity} x ${item.unit_cost:.2f} = ${expected:.2f}, but line says ${item.amount:.2f}")

        # --- LDB Specific: Case Quantity Consistency ---
        if item.cases and item.units_per_case and item.quantity:
             if abs((item.cases * item.units_per_case) - item.quantity) > 0.01:
                 item_warnings.append(f"Case Qty Error: {item.cases} cases x {item.units_per_case} units/case = {item.cases * item.units_per_case}, but quantity is {item.quantity}")

        # Check if new item (never seen before in last 20 invoices)
        if item_key not in item_stats:
            # Only flag as new if we actually have some history
            if len(history_query) >= 3:
                item_warnings.append("New Item: First time seeing this SKU/Description")
        else:
            stats = item_stats[item_key]
            
            # Rule: Cost Spike (> 50% higher)
            if stats["costs"] and item.unit_cost:
                avg_cost = statistics.mean(stats["costs"])
                if avg_cost > 0 and item.unit_cost > (avg_cost * 1.5):
                    diff = int(((item.unit_cost - avg_cost) / avg_cost) * 100)
                    item_warnings.append(f"Price Spike: ${item.unit_cost:,.2f} is {diff}% vs avg ${avg_cost:,.2f}")
            
            # Rule: Quantity Spike (> 3x average)
            if stats["quantities"] and item.quantity:
                avg_qty = statistics.mean(stats["quantities"])
                if avg_qty > 0 and item.quantity > (avg_qty * 3.0) and item.quantity > 5: # Threshold of 5 to avoid noise
                    item_warnings.append(f"High Quantity: {item.quantity} vs avg {avg_qty:.1f}")

        if item_warnings:
            warnings["line_item_warnings"][item.id] = item_warnings

    return warnings
