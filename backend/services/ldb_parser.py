import pandas as pd
import numpy as np
import re
from datetime import datetime
from typing import Dict, Any, List

def safe_float_ldb(val: Any) -> float:
    if pd.isna(val) or val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    # Handle currency strings like "$1,234.56" or "              $2"
    s = str(val).replace("$", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0

def parse_ldb_xlsx(file_path: str) -> Dict[str, Any]:
    """
    Parses an LDB Invoice XLSX file.
    Expected structure:
    - Row 7: Invoice Number
    - Row 8: Invoice Date
    - Row 13: Headers
    - Row 15+: Data
    """
    try:
        # Read the entire file as an object/dataframe
        # Using header=None to manually find and extract data
        df = pd.read_excel(file_path, header=None)
        
        # 1. Extract Header Information
        # Note: pandas row indexing is 0-based
        invoice_number = None
        invoice_date = None
        
        # Search for Invoice Number and Date in the first 15 rows
        for i in range(15):
             raw_row = df.iloc[i].tolist()
             for j, cell in enumerate(raw_row):
                 if pd.isna(cell): continue
                 cell_str = str(cell).lower()
                 if "invoice number" in cell_str:
                      for k in range(j+1, len(raw_row)):
                          if pd.notna(raw_row[k]):
                              invoice_number = str(raw_row[k])
                              break
                 if "invoice date" in cell_str:
                      for k in range(j+1, len(raw_row)):
                          if pd.notna(raw_row[k]):
                              invoice_date = str(raw_row[k])
                              break

        # 2. Extract Line Items
        # Find the header row (usually 13)
        header_row_idx = 13
        # In case it moves, look for "SKU"
        for i in range(10, 20):
            row = [str(x).lower() for x in df.iloc[i].tolist() if pd.notna(x)]
            if "sku" in row:
                header_row_idx = i
                break
        
        # Define Columns (based on our analysis)
        # We need to map columns to indices because LDB often has 'nan' columns
        cols = df.iloc[header_row_idx].tolist()
        col_map = {}
        for idx, col in enumerate(cols):
            if pd.notna(col):
                col_name = str(col).lower().replace(" ", "_").replace(".", "")
                col_map[col_name] = idx
        
        # Data starts 2 rows after the header (Row 15)
        # Or just start after header and check for numeric SKU
        line_items = []
        subtotal = 0.0
        total_deposit = 0.0
        
        for i in range(header_row_idx + 1, len(df)):
            row = df.iloc[i].tolist()
            sku = row[col_map.get('sku', 0)]
            
            # Stop if we hit an empty row or non-numeric SKU if we expect numeric
            if pd.isna(sku) or str(sku).strip() == "" or "total" in str(sku).lower():
                # Check if it's the Summary section
                continue
            
            # Map values
            description = str(row[col_map.get('product_description', 1)])
            category = str(row[col_map.get('product_category', 2)])
            size_str = str(row[col_map.get('size', 3)]) # e.g., "12 X 1.140 L"
            qty = safe_float_ldb(row[col_map.get('qty', 4)])
            uom = str(row[col_map.get('uom', 5)])
            case_price = safe_float_ldb(row[col_map.get('unit_price', 6)])
            ext_amount = safe_float_ldb(row[col_map.get('ext_amount', 7)])
            deposit = safe_float_ldb(row[col_map.get('deposit', 8)])
            recycle = safe_float_ldb(row[col_map.get('recycle', 10)])
            line_total = safe_float_ldb(row[col_map.get('line_total', 11)])
            
            # Parse Pack Size
            units_per_case = 1.0
            match = re.search(r'(\d+)\s*X', size_str, re.IGNORECASE)
            if match:
                units_per_case = float(match.group(1))
            
            # In LDB invoices, Qty is usually Cases if UOM is 'CS'
            cases = qty if uom == 'CS' else 0.0
            total_units = qty * units_per_case if uom == 'CS' else qty
            
            unit_cost = case_price / units_per_case if units_per_case > 0 else case_price
            
            line_items.append({
                "sku": str(sku),
                "description": description,
                "units_per_case": units_per_case,
                "cases": cases,
                "quantity": total_units,
                "case_cost": case_price,
                "unit_cost": round(unit_cost, 4),
                "amount": ext_amount,
                "category_gl_code": normalize_ldb_category(category),
                "confidence_score": 1.0,
                "issue_type": None,
                "issue_status": "open",
                "notes": f"LDB Size: {size_str}, Line Fees: {deposit+recycle}"
            })
            
            subtotal += ext_amount
            total_deposit += (deposit + recycle)

        # 3. Final Result
        # Add tax if we can find it, otherwise assume 5% GST on subtotal?
        # LDB invoices usually show total. Let's look for a row with 'Total'
        total_amount = subtotal + total_deposit
        
        for i in range(len(df)-1, header_row_idx, -1):
            row_str = " ".join([str(x).lower() for x in df.iloc[i].tolist() if pd.notna(x)])
            if "net invoice total" in row_str:
                # The value is probably in the last non-empty cell of this row or next
                vals = [x for x in df.iloc[i].tolist() if pd.notna(x) and isinstance(x, (int, float))]
                if vals:
                    total_amount = vals[-1]
                    break

        return {
            "invoice_number": invoice_number or "UNKNOWN",
            "vendor_name": "LDB",
            "date": invoice_date,
            "total_amount": total_amount,
            "subtotal": subtotal,
            "deposit_amount": total_deposit,
            "tax_amount": total_amount - subtotal - total_deposit,
            "currency": "CAD",
            "line_items": line_items
        }

    except Exception as e:
        print(f"Error parsing LDB XLSX: {e}")
        raise

def normalize_ldb_category(cat: str) -> str:
    cat = cat.lower()
    if 'spirits' in cat or 'liquor' in cat: return "LIQUOR"
    if 'wine' in cat: return "WINE"
    if 'beer' in cat: return "BEER"
    if 'cooler' in cat: return "COOLERS"
    if 'cider' in cat: return "CIDER"
    return "MISC"
