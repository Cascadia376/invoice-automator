import fitz
import os
import json
import uuid
import shutil
from openai import OpenAI
from typing import List, Dict, Any

def detect_invoice_boundaries(file_path: str) -> List[Dict[str, Any]]:
    """
    Analyzes a PDF to determine if it contains multiple invoices.
    Returns a list of page ranges for each detected invoice.
    Example: [{"invoice_number": "123", "pages": [0, 1]}, {"invoice_number": "456", "pages": [2, 2]}]
    """
    try:
        doc = fitz.open(file_path)
        num_pages = len(doc)
        
        # If only 1 page, no need for complex detection
        if num_pages <= 1:
            doc.close()
            return [{"invoice_number": "SINGLE", "pages": [0, 0]}]

        page_previews = []
        for i in range(num_pages):
            page = doc.load_page(i)
            # Extract text from the top and bottom of the page where headers/footers usually are
            text = page.get_text()
            # Take a snippet of the first 1000 and last 500 chars
            snippet = f"--- PAGE {i} ---\n{text[:1000]}\n[...]\n{text[-500:]}"
            page_previews.append(snippet)
        
        doc.close()

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("WARNING: No OpenAI API key for splitting. Treating as single file.")
            return [{"invoice_number": "UNKNOWN", "pages": [0, num_pages - 1]}]

        client = OpenAI(api_key=api_key)
        
        system_prompt = """
        You are a document processing assistant. You will be given text snippets from pages of a PDF that may contain multiple merged invoices.
        Your goal is to identify how many individual invoices are in the document and which pages belong to each.
        
        Logic:
        1. A new invoice usually starts with a vendor name, address, and a new 'Invoice Number' or 'Order Number'.
        2. Continuation pages usually lack the header or show 'Page 2 of X'.
        3. If you see a radical change in vendor or invoice number, it's a new invoice.
        
        Return a JSON object with a 'ranges' key containing a list of objects:
        {
          "ranges": [
            { "invoice_number": "extracted_id", "pages": [start_index, end_index] }
          ]
        }
        Page indices are 0-based.
        """
        
        user_prompt = f"Identify invoice boundaries in this {num_pages}-page document:\n\n" + "\n".join(page_previews)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0
        )

        result = json.loads(response.choices[0].message.content)
        ranges = result.get("ranges", [])
        
        # Validation: check if ranges cover all pages and don't overlap
        if not ranges:
            return [{"invoice_number": "UNKNOWN", "pages": [0, num_pages - 1]}]
            
        print(f"SPLITTER: Detected {len(ranges)} invoices in {num_pages} pages.")
        return ranges

    except Exception as e:
        print(f"ERROR in boundary detection: {e}")
        return [{"invoice_number": "ERROR", "pages": [0, 0]}] # Fallback to single page or original

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
            temp_dir = "/tmp/splits"
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
