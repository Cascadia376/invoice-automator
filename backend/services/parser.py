import os
import json
import re
import pdfplumber
import fitz # PyMuPDF
import base64
from datetime import datetime
from openai import OpenAI
import shutil
import uuid
from invoice2data import extract_data
from invoice2data.extract.loader import read_templates
from database import SessionLocal
import models
from services import textract_service

def normalize_currency(currency: str) -> str:
    """Always return CAD for this implementation."""
    return "CAD"

def safe_float(value, default=0.0):
    """Safely convert value to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
def extract_invoice_data(file_path: str, org_id: str, s3_key: str = None, s3_bucket: str = None):
    """
    Hybrid extraction strategy:
    1. Try invoice2data with existing templates (Fast, Free, Deterministic)
    2. If fails, use LLM to extract data AND generate a new template (Fallback + Learning)
    """
    
    # 1. Try invoice2data
    print(f"Attempting extraction with invoice2data for {file_path}")
    try:
        templates = get_templates_from_db(org_id)
        
        # invoice2data extraction
        result = extract_data(file_path, templates=templates)
        
        if result:
            # Check if we have meaningful data, especially line items
            mapped_result = map_to_schema(result)
            has_line_items = mapped_result.get('line_items') and len(mapped_result['line_items']) > 0
            
            if has_line_items:
                print(f"Successfully extracted using template: {result.get('issuer', 'Unknown')}")
                return mapped_result
            else:
                print(f"Template matched but no line items found. Falling back to LLM.")
            
    except Exception as e:
        print(f"invoice2data extraction failed: {e}")

    # 2. Fallback to LLM (and learn)
    print("No template matched or incomplete data. Falling back to LLM extraction and template generation...")
    return extract_with_llm_and_learn(file_path, org_id, s3_key, s3_bucket)

def extract_with_llm_and_learn(file_path: str, org_id: str, s3_key: str = None, s3_bucket: str = None):
    # Extract text for LLM
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Warning: OPENAI_API_KEY not found. Returning empty data.")
        return empty_invoice_data()

    try:
        client = OpenAI(api_key=api_key)
        
        # Check if text is sufficient, otherwise use OCR
        is_scanned = len(text.strip()) < 50
        messages = []
        
        if is_scanned:
            print("DEBUG: PDF appears to be scanned.")
            
            # TRY TEXTRACT FIRST (if S3 info provided)
            if s3_key and s3_bucket:
                print("DEBUG: Attempting Textract extraction...")
                textract_data = textract_service.extract_invoice_with_textract(s3_bucket, s3_key)
                
                if textract_data:
                    # Quality check on Textract results
                    is_high_quality = True
                    
                    if textract_data.get("total_amount") == 0.0 and not textract_data.get("line_items"):
                        is_high_quality = False
                        print("Textract Quality Check Failed: No total amount or line items")
                    
                    if textract_data.get("vendor_name") == "Unknown Vendor":
                        is_high_quality = False
                        print("Textract Quality Check Failed: Vendor name unknown")
                    
                    if is_high_quality:
                        print("✅ Textract extraction successful and high quality!")
                        return textract_data
                    else:
                        print("⚠️ Textract quality low, falling back to GPT-4o Vision...")
                else:
                    print("⚠️ Textract extraction failed, falling back to GPT-4o Vision...")
            else:
                print("DEBUG: No S3 info provided, skipping Textract. Using Vision extraction...")
            
            # FALLBACK TO VISION API
            print("DEBUG: Using Vision extraction...")
            
            # Convert PDF pages to images
            doc = fitz.open(file_path)
            image_contents = []
            
            # Process ONLY first page to reduce memory usage (most invoices are 1 page)
            for i in range(min(len(doc), 1)):
                page = doc.load_page(i)
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)) # Reduced from 2x to 1.5x to save memory
                img_data = pix.tobytes("png")
                base64_image = base64.b64encode(img_data).decode('utf-8')
                print(f"DEBUG: Processed page {i+1} image. Size: {len(base64_image)} chars")
                image_contents.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                })
                
            messages = [
                {"role": "system", "content": "You are an expert invoice parser. Extract structured data from the invoice image."},
                {"role": "user", "content": [
                    {"type": "text", "text": "Extract data from this invoice:"},
                    *image_contents
                ]}
            ]
        else:
            print("DEBUG: PDF appears to be text-based.")
            messages = [
                {"role": "system", "content": "You are an expert invoice parser. Extract structured data from the invoice text."},
                {"role": "user", "content": f"Invoice Text:\n\n{text[:15000]}"}
            ]

        system_prompt = """You are an expert invoice parser. Your goal is to:
1. Extract structured data from the invoice with HIGH ACCURACY.
2. Assign a confidence score (0.0-1.0) to each line item based on how certain you are about the extracted data.
3. Generate a YAML template compatible with the 'invoice2data' Python library to parse this vendor's invoices in the future.

CRITICAL INSTRUCTIONS FOR LINE ITEMS:
- Each line item MUST have a UNIQUE SKU. If SKUs are not visible, use null.
- DO NOT repeat the same SKU for multiple line items unless they are truly identical products.
- Extract the EXACT quantity from each line. Common patterns:
  * "Qty" or "Quantity" column
  * Number before "x" (e.g., "5 x Product" means quantity=5)
  * "Cases" or "Units" columns
- If you see both "cases" and "units_per_case", calculate: quantity = cases × units_per_case
- Pay close attention to decimal points in quantities and prices
- Extract unit_cost (price per single unit) and amount (total line price) separately
- **PO NUMBER**: Look specifically for "PO", "P.O.", "Purchase Order", or "Order #". Extract this into the `po_number` field.
- **LIQUOR INDUSTRY DEPOSITS**: Search aggressively for Bottle Deposits (Btl Dep), Recycling Fees (Env Fee), and Container Deposits. 
- If these are hidden in line items, extract them. If they are in the summary, extract them.
- If you find multiple different fees (e.g. Deposit + Recycling), SUM THEM into the `deposit_amount` field.
- If a line item description contains "Deposit" or "Recycling", but has a negative or small value, treat it as a deposit component.
- **MATH VALIDATION**: Strictly ensure that `quantity * unit_cost = amount` for every line item. If the invoice shows a total that doesn't match the calculation, flag it in the description or notes.

Return a JSON object with two keys: "data" and "template".

"data" must match this structure:
{
    "invoice_number": "str",
    "po_number": "str",
    "date": "str (YYYY-MM-DD)",
    "vendor_name": "str",
    "vendor_address": "str",
    "total_amount": "float",
    "subtotal": "float",
    "tax_amount": "float",
    "deposit_amount": "float",
    "currency": "str (default CAD)",
    "line_items": [{
        "sku": "str or null (MUST be unique per line item)",
        "description": "str",
        "units_per_case": "float (default 1.0 if not specified)",
        "cases": "float (default 0.0 if not specified)",
        "quantity": "float (REQUIRED - extract carefully)",
        "unit_cost": "float (price per unit)",
        "amount": "float (total for this line)",
        "confidence_score": "float (0.0-1.0, where 1.0 = very confident, 0.5 = uncertain, 0.0 = guessing)"
    }]
}

Confidence score guidelines:
- 1.0: Data is clearly visible and unambiguous
- 0.7-0.9: Data is visible but formatting is unclear or partially obscured
- 0.4-0.6: Data is difficult to read or requires inference
- 0.0-0.3: Data is missing or completely illegible, you're guessing

"template" must be a valid YAML string for invoice2data, like:
issuer: Vendor Name
keywords:
  - Keyword1
fields:
  amount: Total\\s+([\\d,]+\\.\\d{2})
  invoice_number: Invoice\\s+#(\\d+)
  date: Date\\s+(\\d{4}-\\d{2}-\\d{2})
options:
  currency: CAD
"""

        # Prepend system prompt to messages
        messages.insert(0, {"role": "system", "content": system_prompt})

        # CASCADE STRATEGY: Try gpt-4o-mini first, then fallback to gpt-4o
        model_to_use = "gpt-4o-mini"
        if not is_scanned:
             # For text-based, mini is usually sufficient, but we can stick to mini
             model_to_use = "gpt-4o-mini"
        
        print(f"Attempting extraction with model: {model_to_use}")
        
        response = client.chat.completions.create(
            model=model_to_use,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0
        )
        
        content = response.choices[0].message.content
        print(f"DEBUG: LLM Response: {content[:500]}...") # Log first 500 chars
        result = json.loads(content)
        data = result.get("data", {})
        
        # Quality Check
        is_high_quality = True
        
        # Check 1: Critical fields present?
        if data.get("total_amount") == 0.0 and not data.get("line_items"):
            is_high_quality = False
            print("Quality Check Failed: No total amount or line items found.")
            
        if data.get("vendor_name") == "UNKNOWN" or not data.get("vendor_name"):
             is_high_quality = False
             print("Quality Check Failed: Vendor name unknown.")

        # Check 2: Confidence scores (if available)
        avg_score = 0.0
        if data.get("line_items"):
            scores = [item.get("confidence_score", 0) for item in data["line_items"]]
            avg_score = sum(scores) / len(scores) if scores else 0
            if avg_score < 0.7:
                is_high_quality = False
                print(f"Quality Check Failed: Low average confidence score ({avg_score:.2f})")
        
        # Log quality check results
        print(f"Quality Check: total_amount={data.get('total_amount')}, vendor={data.get('vendor_name')}, line_items={len(data.get('line_items', []))}, avg_confidence={avg_score:.2f}, is_high_quality={is_high_quality}")

        # RETRY with GPT-4o if quality is low AND it was a scanned doc (vision)
        # (For text-based, switching models might not help as much as vision)
        if not is_high_quality and is_scanned:
            print("⚠️ Extraction quality low. Retrying with GPT-4o (High Cost Model)...")
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0
            )
            content = response.choices[0].message.content
            result = json.loads(content)
            print("GPT-4o extraction complete.")

        if "template" in result and result["template"]:
            save_new_template(result["template"], result["data"].get("vendor_name", "unknown"), org_id)
            
        final_data = result.get("data", {})
        final_data["currency"] = normalize_currency(final_data.get("currency"))
        final_data["raw_extraction_results"] = json.dumps(result.get("data", {})) # Store for learning
        
        # --- MATH VALIDATION ---
        for item in final_data.get("line_items", []):
            qty = safe_float(item.get("quantity"))
            cost = safe_float(item.get("unit_cost"))
            amt = safe_float(item.get("amount"))
            
            # Allow for tiny rounding differences (±0.02)
            if abs((qty * cost) - amt) > 0.02:
                print(f"DEBUG: Math mismatch on {item.get('description')}: {qty} * {cost} = {qty*cost} (Invoice says {amt})")
                # Automatically fix the amount if it's clearly a parsing error and cost/qty look reliable
                # Or just mark it for user review if it's suspicious. For now, we trust the math.
                item["amount"] = round(qty * cost, 2)
        
        return final_data

    except Exception as e:
        print(f"LLM Extraction failed: {e}")
        return empty_invoice_data()

def save_new_template(template_content: str, vendor_name: str, org_id: str):
    db = SessionLocal()
    try:
        # Sanitize content (remove control characters that break YAML)
        sanitized_content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', template_content)
        
        # Check if exists
        existing = db.query(models.Template).filter(
            models.Template.vendor_name == vendor_name,
            models.Template.organization_id == org_id
        ).first()
        if existing:
            existing.content = sanitized_content
            existing.updated_at = datetime.utcnow()
            print(f"Updated existing template in DB for {vendor_name}")
        else:
            new_template = models.Template(
                id=str(uuid.uuid4()),
                vendor_name=vendor_name,
                organization_id=org_id,
                content=sanitized_content
            )
            db.add(new_template)
            print(f"Saved new template to DB for {vendor_name}")
            
        db.commit()
    except Exception as e:
        print(f"Failed to save template to DB: {e}")
    finally:
        db.close()

def map_to_schema(data):
    return {
        "invoice_number": str(data.get('invoice_number', 'UNKNOWN')),
        "vendor_name": data.get('issuer', 'UNKNOWN'),
        "date": str(data.get('date', datetime.now().strftime("%Y-%m-%d"))),
        "total_amount": float(data.get('amount', 0.0)),
        "subtotal": float(data.get('subtotal', 0.0)),
        "shipping_amount": float(data.get('shipping_amount', 0.0)),
        "discount_amount": safe_float(data.get('discount_amount')),
        "tax_amount": 0.0,
        "currency": "CAD",
        "line_items": data.get('lines', []) # Map invoice2data 'lines' to our 'line_items'
    }

def refine_template_with_feedback(file_path: str, corrected_data: dict, org_id: str):
    """
    Refines the invoice2data template based on user feedback.
    """
    print(f"Refining template for {file_path} with feedback")
    
    # Extract text
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
            
    vendor_name = corrected_data.get("vendor_name", "unknown")
    
    db = SessionLocal()
    existing_template = ""
    try:
        template_record = db.query(models.Template).filter(
            models.Template.vendor_name == vendor_name,
            models.Template.organization_id == org_id
        ).first()
        if template_record:
            existing_template = template_record.content
    finally:
        db.close()
            
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Warning: OPENAI_API_KEY not found. Cannot refine template.")
        return

    try:
        client = OpenAI(api_key=api_key)
        
        system_prompt = """You are an expert regex engineer for invoice parsing. 
        The user has provided a corrected value for a field that was missed or extracted incorrectly.
        Your job is to UPDATE the YAML template to correctly extract this value using Regex.
        
        Return ONLY the updated YAML template string.
        """
        
        user_prompt = f"""
        Invoice Text:
        {text[:15000]}
        
        Existing Template:
        {existing_template}
        
        Corrected Data from User:
        {json.dumps(corrected_data, indent=2)}
        
        Please generate the improved YAML template. Ensure it handles the corrected fields specifically.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0
        )
        
        new_template = response.choices[0].message.content
        # Strip markdown code blocks if present
        if new_template.startswith("```yaml"):
            new_template = new_template.replace("```yaml", "").replace("```", "")
        elif new_template.startswith("```"):
            new_template = new_template.replace("```", "")
            
        save_new_template(new_template.strip(), vendor_name, org_id)
        print("Template refined and saved successfully.")

    except Exception as e:
        print(f"Template refinement failed: {e}")

def empty_invoice_data():
    return {
        "invoice_number": "UNKNOWN",
        "vendor_name": "UNKNOWN",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "total_amount": 0.0,
        "tax_amount": 0.0,
        "currency": "CAD",
        "line_items": []
    }

def get_templates_from_db(org_id: str):
    db = SessionLocal()
    try:
        db_templates = db.query(models.Template).filter(models.Template.organization_id == org_id).all()
        
        # Create temp dir for invoice2data
        temp_dir = '/tmp/invoice_templates'
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        
        # Write DB templates to files
        for t in db_templates:
            safe_name = re.sub(r'[^a-zA-Z0-9]', '_', t.vendor_name).lower()
            filename = f"{safe_name}_{t.id}.yml"
            with open(os.path.join(temp_dir, filename), 'w') as f:
                f.write(t.content)
                
        # Copy local generic template if it exists
        local_template_dir = os.path.join(os.path.dirname(__file__), '../templates')
        if os.path.exists(local_template_dir):
             for f in os.listdir(local_template_dir):
                 if f.endswith('.yml'):
                     shutil.copy(os.path.join(local_template_dir, f), temp_dir)
        
        return read_templates(temp_dir)
    except Exception as e:
        print(f"Error loading templates from DB: {e}")
        return []
    finally:
        db.close()
