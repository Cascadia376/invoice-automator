import boto3
import os
from typing import Dict, List, Optional

# Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-2")

def get_textract_client():
    return boto3.client(
        'textract',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )

def parse_float(value: str) -> float:
    """Parse a string to float, handling commas, dollar signs, and empty strings."""
    if not value:
        return 0.0
    try:
        # Remove currency symbols, commas, and whitespace, then convert
        cleaned = str(value).replace('$', '').replace(',', '').replace('€', '').replace('£', '').strip()
        return float(cleaned) if cleaned else 0.0
    except (ValueError, AttributeError):
        return 0.0

def parse_date(date_str: str) -> str:
    """Convert various date formats to YYYY-MM-DD."""
    if not date_str:
        return ''
    
    try:
        from dateparser import parse
        parsed = parse(date_str)
        if parsed:
            return parsed.strftime('%Y-%m-%d')
    except:
        pass
    
    return date_str  # Return original if parsing fails

def clean_text(text: str) -> str:
    """Clean text by removing newlines and extra whitespace."""
    if not text:
        return ''
    # Replace newlines with spaces, then collapse multiple spaces
    return ' '.join(text.replace('\n', ' ').split())

def extract_invoice_with_textract(s3_bucket: str, s3_key: str) -> Optional[Dict]:
    """
    Extract invoice data using AWS Textract AnalyzeExpense API.
    
    Args:
        s3_bucket: S3 bucket name
        s3_key: S3 object key
        
    Returns:
        Extracted invoice data in our schema format, or None if extraction fails
    """
    try:
        client = get_textract_client()
        
        print(f"DEBUG: Calling Textract AnalyzeExpense for s3://{s3_bucket}/{s3_key}")
        
        response = client.analyze_expense(
            Document={
                'S3Object': {
                    'Bucket': s3_bucket,
                    'Name': s3_key
                }
            }
        )
        
        # Parse Textract response
        if not response.get('ExpenseDocuments'):
            print("WARNING: Textract returned no expense documents")
            return None
            
        expense_doc = response['ExpenseDocuments'][0]
        
        # Extract summary fields (vendor, total, date, etc.)
        summary_fields = {}
        for field in expense_doc.get('SummaryFields', []):
            field_type = field.get('Type', {}).get('Text', '')
            value_detection = field.get('ValueDetection', {})
            value = value_detection.get('Text', '')
            confidence = value_detection.get('Confidence', 0)
            
            summary_fields[field_type] = {
                'value': value,
                'confidence': confidence
            }
        
        # DEBUG: Log summary fields
        print(f"DEBUG: Textract summary fields: {list(summary_fields.keys())}")
        print(f"DEBUG: TOTAL value: '{summary_fields.get('TOTAL', {}).get('value')}'")
        print(f"DEBUG: SUBTOTAL value: '{summary_fields.get('SUBTOTAL', {}).get('value')}'")
        print(f"DEBUG: TAX value: '{summary_fields.get('TAX', {}).get('value')}'")
        print(f"DEBUG: AMOUNT_PAID value: '{summary_fields.get('AMOUNT_PAID', {}).get('value')}'")
        
        # Extract line items
        line_items = []
        for line_item_group in expense_doc.get('LineItemGroups', []):
            for line_item in line_item_group.get('LineItems', []):
                item_data = {}
                for field in line_item.get('LineItemExpenseFields', []):
                    field_type = field.get('Type', {}).get('Text', '')
                    value_detection = field.get('ValueDetection', {})
                    value = value_detection.get('Text', '')
                    confidence = value_detection.get('Confidence', 0)
                    
                    item_data[field_type] = {
                        'value': value,
                        'confidence': confidence
                    }
                
                # DEBUG: Log what fields Textract found (only first item to avoid spam)
                if len(line_items) == 0:
                    print(f"DEBUG: Textract line item fields: {list(item_data.keys())}")
                
                # Map Textract fields to our schema (with safe number parsing)
                # Textract field names can vary: ITEM, PRODUCT_CODE, DESCRIPTION, etc.
                sku = (
                    item_data.get('PRODUCT_CODE', {}).get('value') or
                    item_data.get('ITEM_CODE', {}).get('value') or
                    item_data.get('SKU', {}).get('value') or
                    None
                )
                
                description = (
                    item_data.get('DESCRIPTION', {}).get('value') or
                    item_data.get('ITEM', {}).get('value') or
                    item_data.get('PRODUCT_NAME', {}).get('value') or
                    'Item'
                )
                
                line_items.append({
                    'sku': sku,
                    'description': description,
                    'quantity': parse_float(item_data.get('QUANTITY', {}).get('value', '1.0')),
                    'unit_cost': parse_float(item_data.get('UNIT_PRICE', {}).get('value', '0.0')),
                    'amount': parse_float(item_data.get('PRICE', {}).get('value', '0.0')),
                    'units_per_case': 1.0,
                    'cases': 0.0,
                    'confidence_score': min(
                        item_data.get('QUANTITY', {}).get('confidence', 100),
                        item_data.get('PRICE', {}).get('confidence', 100)
                    ) / 100.0
                })
        
        # Parse summary amounts
        total_amount = parse_float(summary_fields.get('TOTAL', {}).get('value', '0.0'))
        subtotal = parse_float(summary_fields.get('SUBTOTAL', {}).get('value', '0.0'))
        tax_amount = parse_float(summary_fields.get('TAX', {}).get('value', '0.0'))
        
        # Deposit can be labeled many ways - try all possibilities
        deposit_amount = (
            parse_float(summary_fields.get('AMOUNT_PAID', {}).get('value', '0.0')) or
            parse_float(summary_fields.get('DEPOSIT', {}).get('value', '0.0')) or
            parse_float(summary_fields.get('DEPOSIT_AMOUNT', {}).get('value', '0.0')) or
            parse_float(summary_fields.get('PAYMENT', {}).get('value', '0.0')) or
            0.0
        )
        
        print(f"DEBUG: Extracted amounts - Total: {total_amount}, Subtotal: {subtotal}, Tax: {tax_amount}, Deposit: {deposit_amount}")
        
        # If total is still missing after parsing, calculate from line items as fallback
        if total_amount == 0.0 and line_items:
            calculated_subtotal = sum(item['amount'] for item in line_items)
            print(f"DEBUG: Total missing from Textract. Calculated subtotal from line items: {calculated_subtotal}")
            subtotal = calculated_subtotal
            total_amount = calculated_subtotal + tax_amount + deposit_amount
        
        # Map to our schema (with safe number parsing and text cleanup)
        extracted_data = {
            'invoice_number': summary_fields.get('INVOICE_RECEIPT_ID', {}).get('value', 'UNKNOWN'),
            'vendor_name': clean_text(summary_fields.get('VENDOR_NAME', {}).get('value', 'Unknown Vendor')),
            'date': parse_date(summary_fields.get('INVOICE_RECEIPT_DATE', {}).get('value', '')),
            'total_amount': total_amount,
            'subtotal': subtotal,
            'tax_amount': tax_amount,
            'deposit_amount': deposit_amount,
            'shipping_amount': 0.0,
            'discount_amount': 0.0,
            'currency': 'CAD',
            'line_items': line_items
        }
        
        # Calculate average confidence
        all_confidences = [summary_fields.get(k, {}).get('confidence', 0) for k in summary_fields]
        avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0
        
        print(f"DEBUG: Textract extraction complete. Vendor={extracted_data['vendor_name']}, Total={extracted_data['total_amount']}, LineItems={len(line_items)}, AvgConfidence={avg_confidence:.2f}%")
        
        return extracted_data
        
    except Exception as e:
        print(f"ERROR: Textract extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None
