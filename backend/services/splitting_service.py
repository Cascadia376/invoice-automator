import fitz
import os
import json
import uuid
import shutil
from openai import OpenAI
from typing import List, Dict, Any
import tempfile
import base64

def detect_invoice_boundaries(file_path: str) -> List[Dict[str, Any]]:
    """
    Analyzes a PDF to determine if it contains multiple invoices.
    Supports both text-based and image-based (scanned) PDFs.
    """
    try:
        doc = fitz.open(file_path)
        num_pages = len(doc)
        
        if num_pages <= 1:
            doc.close()
            return [{"invoice_number": "SINGLE", "pages": [0, 0], "is_invoice": True}]

        # 1. Detect if it's a scan (low text density)
        full_text = ""
        page_previews = []
        for i in range(num_pages):
            page = doc.load_page(i)
            text = page.get_text()
            full_text += text
            page_previews.append(f"--- PAGE {i} ---\n{text[:800]}")
        
        is_scanned = len(full_text.strip()) < (50 * num_pages)
        print(f"SPLITTER: Scan detection - is_scanned={is_scanned}, text_len={len(full_text)}")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("WARNING: No OpenAI API key for splitting. Treating as single file.")
            doc.close()
            return [{"invoice_number": "UNKNOWN", "pages": [0, num_pages - 1], "is_invoice": True}]

        client = OpenAI(api_key=api_key)
        
        system_prompt = """
        You are a document processing assistant. You will be given content from pages of a PDF that may contain:
        1. Merged invoices (multiple invoices in one file).
        2. Non-invoice pages (Cover pages, fax headers, bank confirmations).
        
        Your goal is to identify the page ranges for each INDIVIDUAL invoice.
        
        CRITICAL RULES:
        1. Identify "Cover Pages" or any page that is NOT part of an invoice. 
        2. For the 'is_invoice' flag: set to true ONLY if the range contains a valid invoice.
        3. A new invoice start is indicated by a new Vendor Name, Date, and Invoice Number.
        4. If a page just looks like a continuation of the previous invoice (no new header), keep it in the same range.
        
        Return a JSON object:
        {
          "ranges": [
            { 
              "invoice_number": "extracted_id or description", 
              "pages": [start_index, end_index],
              "is_invoice": true/false 
            }
          ]
        }
        Page indices are 0-based.
        """

        if is_scanned:
            # 2. Vision-based splitting for scans
            print(f"SPLITTER: Using Vision for {num_pages} scanned pages...")
            content = [{"type": "text", "text": f"Identify invoice boundaries in this {num_pages}-page scanned document. Some pages might be cover letters."}]
            
            # Convert all pages to thumbnails for Vision
            for i in range(num_pages):
                page = doc.load_page(i)
                # Keep resolution low (72 dpi) for splitting to save tokens/speed
                pix = page.get_pixmap(matrix=fitz.Matrix(0.8, 0.8)) 
                img_data = pix.tobytes("png")
                base64_image = base64.b64encode(img_data).decode('utf-8')
                
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}",
                        "detail": "low"
                    }
                })
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ]
        else:
            # 2. Text-based splitting
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Identify invoice boundaries in this {num_pages}-page document:\n\n" + "\n".join(page_previews)}
            ]

        doc.close()

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0
        )

        result = json.loads(response.choices[0].message.content)
        ranges = result.get("ranges", [])
        
        # Filter out non-invoice pages (like cover pages)
        invoices_only = [r for r in ranges if r.get("is_invoice", True)]
        
        if not invoices_only:
            print("WARNING: Splitting logic returned no valid invoices. Defaulting to full range.")
            return [{"invoice_number": "UNKNOWN", "pages": [0, num_pages - 1], "is_invoice": True}]
            
        print(f"SPLITTER: Detected {len(invoices_only)} invoices (skipped {len(ranges) - len(invoices_only)} non-invoice pages).")
        return invoices_only

    except Exception as e:
        print(f"ERROR in boundary detection: {e}")
        import traceback
        traceback.print_exc()
        return [{"invoice_number": "ERROR", "pages": [0, num_pages - 1 if 'num_pages' in locals() else 0], "is_invoice": True}]

def split_pdf_into_files(original_file_path: str, ranges: List[Dict[str, Any]]) -> List[str]:
    """
    Splits the original PDF into multiple files based on ranges.
    Returns a list of temporary file paths.
    """
    split_files = []
    try:
        for idx, r in enumerate(ranges):
            start, end = r["pages"]
            
            # Create a new PDF for this range
            doc = fitz.open(original_file_path)
            new_doc = fitz.open()
            
            # fitz.insert_pdf is better for preserving quality/metadata
            new_doc.insert_pdf(doc, from_page=start, to_page=end)
            
            # Save to temporary path
            temp_dir = os.path.join(tempfile.gettempdir(), "splits")
            os.makedirs(temp_dir, exist_ok=True)
            
            file_id = str(uuid.uuid4())
            new_path = os.path.join(temp_dir, f"{file_id}.pdf")
            new_doc.save(new_path)
            
            new_doc.close()
            doc.close()
            
            split_files.append(new_path)
            
        return split_files
    except Exception as e:
        print(f"ERROR splitting PDF: {e}")
        return [original_file_path] # Fallback to original if splitting fails
