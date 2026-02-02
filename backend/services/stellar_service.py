"""
Stellar POS Integration Service

Handles posting invoices to Stellar POS system via their stock import API.
Uses consistent patterns with Chain Flow Metrics for cross-app compatibility.
"""

import os
import csv
import json
import logging
import httpx
from io import StringIO, BytesIO
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session

import models

logger = logging.getLogger(__name__)

# Configuration - matches Chain Flow Metrics pattern
STELLAR_API_TOKEN = os.getenv("STELLAR_API_TOKEN")
STELLAR_TENANT_ID = os.getenv("STELLAR_TENANT_ID")
STELLAR_LOCATION_ID = os.getenv("STELLAR_LOCATION_ID")
STELLAR_BASE_URL = os.getenv("STELLAR_BASE_URL", "https://stock-import.stellarpos.io")
STELLAR_INVENTORY_URL = os.getenv("STELLAR_INVENTORY_URL", "https://inventorymanagement.stellarpos.io")


class StellarError(Exception):
    """Custom exception for Stellar API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)


def generate_stellar_csv(line_items: List[models.LineItem]) -> BytesIO:
    """
    Generate CSV file from invoice line items in Stellar's expected format.
    
    Stellar expects exactly 3 columns:
    - SKU
    - Receiving Qty (UOM)
    - Confirmed total Cost
    
    Args:
        line_items: List of LineItem objects from the invoice
        
    Returns:
        BytesIO object containing the CSV data
    """
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header row - EXACT format required by Stellar
    writer.writerow(['SKU', 'Receiving Qty (UOM)', 'Confirmed total Cost'])
    
    # Write data rows
    for item in line_items:
        writer.writerow([
            item.sku or '',
            item.quantity or 0,
            item.total_price or 0
        ])
    
    # Convert to bytes
    csv_content = output.getvalue()
    csv_bytes = BytesIO(csv_content.encode('utf-8'))
    csv_bytes.seek(0)
    
    logger.info(f"Generated Stellar CSV with {len(line_items)} line items")
    return csv_bytes


async def post_invoice_to_stellar(
    invoice: models.Invoice,
    db: Session,
    supplier_id: str,
    supplier_name: str,
    tenant_id: Optional[str] = None,
    location_id: Optional[str] = None
) -> Dict:
    """
    Post an invoice to Stellar POS system.
    
    Args:
        invoice: Invoice object to post (must have line_items loaded)
        db: Database session for updating invoice status
        supplier_id: Stellar supplier UUID
        supplier_name: Supplier name as registered in Stellar
        tenant_id: Override default tenant ID (optional)
        location_id: Override default location ID (optional)
        
    Returns:
        Dictionary containing the Stellar API response
        
    Raises:
        StellarError: If the API request fails
    """
    # Validate configuration
    if not STELLAR_API_TOKEN:
        raise StellarError("STELLAR_API_TOKEN not configured")
    
    # Use provided IDs or fall back to env defaults
    tenant = tenant_id or STELLAR_TENANT_ID
    location = location_id or STELLAR_LOCATION_ID
    
    if not tenant:
        raise StellarError("STELLAR_TENANT_ID not configured")
    if not location:
        raise StellarError("STELLAR_LOCATION_ID not configured")
    
    # Validate invoice has line items
    if not invoice.line_items:
        raise StellarError("Invoice has no line items")
    
    # Generate CSV file
    csv_data = generate_stellar_csv(invoice.line_items)
    
    # Try to get store record to find the most accurate display name
    store = db.query(models.Store).filter(
        models.Store.organization_id == invoice.organization_id
    ).first()
    
    # Authoritative ID approach: IDs are stable, names are displayed-only/dynamic
    # We use 'Location {ID}' as the base fallback if no name is known
    display_location_name = f"Location {location[:8]}..." 
    if store:
        display_location_name = store.stellar_location_name or store.name or display_location_name

    form_data = {
        'supplier': supplier_id,
        'location': location,
        'supplier_name': supplier_name,
        'location_name': display_location_name,
        'tax_ids': '',
        'supplierInvoiceNumber': invoice.invoice_number or '',
        # ... other fields if needed
    }
    # Prepare files
    files = {
        'csvFile': ('invoice.csv', csv_data, 'text/csv')
    }
    
    # Prepare headers - matches Chain Flow Metrics pattern
    headers = {
        'Authorization': f'Bearer {STELLAR_API_TOKEN}',
        'tenant': tenant,
        'tenant_id': tenant,
        'Referer': f'https://{tenant}.stellarpos.io/'
    }
    
    # Make API request
    url = f"{STELLAR_BASE_URL}/api/stock/import-asn"
    
    logger.info(f"Posting invoice {invoice.invoice_number} to Stellar")
    logger.debug(f"Stellar API URL: {url}")
    logger.debug(f"Supplier: {supplier_name} ({supplier_id})")
    logger.debug(f"Location: {location}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                files=files,
                data=form_data,
                headers=headers
            )
            
            # Log response for debugging
            logger.info(f"Stellar API response status: {response.status_code}")
            logger.debug(f"Stellar API response: {response.text}")
            
            # Check for errors - matches Chain Flow Metrics error handling
            if not response.is_success:
                error_message = f"Stellar API error: {response.status_code}"
                try:
                    error_data = response.json()
                    error_message = error_data.get('message', error_message)
                except:
                    error_message = response.text or error_message
                
                raise StellarError(
                    error_message,
                    status_code=response.status_code,
                    response_data=response.text
                )
            
            # Parse response
            result = response.json()
            
            # Update invoice with Stellar data
            invoice.stellar_posted_at = datetime.utcnow()
            invoice.stellar_response = json.dumps(result)
            
            # Extract ASN number if available
            if 'asn_number' in result:
                invoice.stellar_asn_number = result['asn_number']
            elif 'id' in result:
                invoice.stellar_asn_number = result['id']
            
            db.commit()
            
            logger.info(f"Successfully posted invoice {invoice.invoice_number} to Stellar")
            return result
            
    except httpx.TimeoutException:
        raise StellarError("Request to Stellar API timed out")
    except httpx.RequestError as e:
        raise StellarError(f"Network error: {str(e)}")
    except StellarError:
        raise
    except Exception as e:
        logger.exception("Unexpected error posting to Stellar")
        raise StellarError(f"Unexpected error: {str(e)}")


def get_stellar_config_for_vendor(vendor_name: str, db: Session) -> Optional[Dict[str, str]]:
    """
    Get Stellar supplier configuration for a vendor.
    
    Args:
        vendor_name: Name of the vendor
        db: Database session
        
    Returns:
        Dictionary with supplier_id and supplier_name, or None if not configured
    """
    vendor = db.query(models.Vendor).filter(
        models.Vendor.name == vendor_name
    ).first()
    
    if not vendor:
        logger.warning(f"Vendor not found: {vendor_name}")
        return None
    
    # Check if vendor has Stellar configuration
    if not hasattr(vendor, 'stellar_supplier_id') or not vendor.stellar_supplier_id:
        logger.debug(f"Vendor {vendor_name} has no Stellar supplier ID configured")
        return None
    
    return {
        'supplier_id': vendor.stellar_supplier_id,
        'supplier_name': getattr(vendor, 'stellar_supplier_name', vendor_name)
    }


async def post_invoice_if_configured(
    invoice: models.Invoice,
    db: Session
) -> Optional[Dict]:
    """
    Post invoice to Stellar if vendor and store are properly configured.
    """
    # Check if Stellar is globally enabled via token
    if not STELLAR_API_TOKEN:
        logger.debug("Stellar integration not configured (missing STELLAR_API_TOKEN)")
        return None
    
    # Get store configuration for overrides
    store = db.query(models.Store).filter(
        models.Store.organization_id == invoice.organization_id
    ).first()
    
    tenant_id = None
    location_id = None
    
    if store:
        # If store specifically disables Stellar, don't post
        if hasattr(store, 'stellar_enabled') and store.stellar_enabled is False:
            logger.debug(f"Stellar specifically disabled for store {store.name}")
            return None
            
        tenant_id = getattr(store, 'stellar_tenant', None)
        location_id = getattr(store, 'stellar_location_id', None)
    
    # Get vendor configuration
    vendor_config = get_stellar_config_for_vendor(invoice.vendor_name, db)
    if not vendor_config:
        logger.info(f"Stellar not configured for vendor {invoice.vendor_name}")
        return None
    
    # Post to Stellar using store overrides if present
    return await post_invoice_to_stellar(
        invoice,
        db,
        supplier_id=vendor_config['supplier_id'],
        supplier_name=vendor_config['supplier_name'],
        tenant_id=tenant_id,
        location_id=location_id
    )


async def search_stellar_suppliers(
    query: str = "",
    tenant_id: Optional[str] = None,
    page: int = 1,
    limit: int = 20
) -> Dict:
    """
    Search for suppliers directly in the Stellar POS system.
    
    Args:
        query: Search string
        tenant_id: Stellar tenant ID
        page: Page number
        limit: Max results per page
        
    Returns:
        JSON response from Stellar API
    """
    if not STELLAR_API_TOKEN:
        raise StellarError("STELLAR_API_TOKEN not configured")
        
    tenant = tenant_id or STELLAR_TENANT_ID
    if not tenant:
        raise StellarError("STELLAR_TENANT_ID not configured")
        
    headers = {
        'Authorization': f'Bearer {STELLAR_API_TOKEN}',
        'tenant': tenant,
        'tenant_id': tenant,
        'accept': 'application/json, text/plain, */*',
        'origin': f'https://{tenant}.stellarpos.io',
        'referer': f'https://{tenant}.stellarpos.io/'
    }
    
    params = {
        'search': query,
        'page': page,
        'limit': limit
    }
    
    # Use inventory URL for search as confirmed in previous probes
    url = f"{STELLAR_INVENTORY_URL}/api/suppliers/retrieve/list"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=headers)
            
            if not response.is_success:
                raise StellarError(
                    f"Stellar Search API error: {response.status_code}",
                    status_code=response.status_code,
                    response_data=response.text
                )
                
            return response.json()
            
    except httpx.RequestError as e:
        raise StellarError(f"Network error during search: {str(e)}")
    except Exception as e:
        logger.exception("Unexpected error searching Stellar suppliers")
        raise StellarError(f"Search failed: {str(e)}")


async def retrieve_stellar_invoice(
    asn_number: str,
    tenant_id: str
) -> Dict:
    """
    Retrieve ASN/Invoice details from Stellar using the ASN number.
    
    Args:
        asn_number: The SUPL-INV-... reference number
        tenant_id: Stellar tenant ID
        
    Returns:
        JSON data from Stellar
    """
    if not STELLAR_API_TOKEN:
        raise StellarError("STELLAR_API_TOKEN not configured")
        
    headers = {
        'Authorization': f'Bearer {STELLAR_API_TOKEN}',
        'tenant': tenant_id,
        'tenant_id': tenant_id,
        'accept': 'application/json, text/plain, */*',
        'origin': f'https://{tenant_id}.stellarpos.io',
        'referer': f'https://{tenant_id}.stellarpos.io/'
    }
    
    # Correct endpoint found via static analysis & probing
    url = f"https://stock-import.stellarpos.io/api/supplier-invoices/{asn_number}"
    
    logger.info(f"Retrieving ASN {asn_number} from Stellar")
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers)
            
            if not response.is_success:
                logger.error(f"Stellar API Error {response.status_code}: {response.text[:200]}")
                raise StellarError(
                    f"Stellar Retrieval API error: {response.status_code}",
                    status_code=response.status_code,
                    response_data=response.text
                )
            
            return response.json()
            
    except httpx.RequestError as e:
        raise StellarError(f"Network error during retrieval: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error retrieving Stellar ASN {asn_number}")
        raise StellarError(f"Retrieval failed: {str(e)}")


def sync_stellar_data_to_db(
    asn_number: str, 
    stellar_data: Dict, 
    db: Session,
    organization_id: Optional[str] = None
) -> models.SupplierInvoice:
    """
    Parse Stellar JSON data and sync it to the supplier_invoices and supplier_invoice_items tables.
    """
    # Unwrap 'result' object if present (structure seen in probe)
    data_source = stellar_data.get('result', stellar_data)
    
    header = data_source.get('supplierInvoice', {})
    if not header and 'id' in data_source:
        # Fallback if structure is flat
        header = data_source
        
    items = data_source.get('supplierInvoiceItems', [])

    # 1. Update or create the Header
    supplier_inv = db.query(models.SupplierInvoice).filter(
        models.SupplierInvoice.invoice_id == asn_number
    ).first()
    
    if not supplier_inv:
        supplier_inv = models.SupplierInvoice(invoice_id=asn_number)
        db.add(supplier_inv)

    # Map header fields
    supplier_inv.supplier_name = header.get('supplier_name')
    supplier_inv.supplier_invoice_number = header.get('supplier_invoice_number') or header.get('invoice_number')
    supplier_inv.original_po_number = header.get('original_po_number')
    supplier_inv.status = header.get('status')
    supplier_inv.store_name = header.get('location_name')
    
    # Financials
    # Note: Stellar uses strings or floats, safest to allow simple casting or checking
    def parse_float(val):
        try:
            return float(val) if val is not None else 0.0
        except:
            return 0.0

    supplier_inv.sub_total = parse_float(header.get('sub_total') or header.get('total_amount_excluded_tax'))
    supplier_inv.total_taxes = parse_float(header.get('total_tax') or header.get('tax_amount'))
    supplier_inv.total_deposits = parse_float(header.get('total_deposit'))
    supplier_inv.invoice_total = parse_float(header.get('total_amount_included_tax') or header.get('grand_total'))
    
    # Timestamps
    for date_field, json_field in [
        ('created_date', 'createdAt'), 
        ('date_received', 'received_date'), 
        ('date_posted', 'updatedAt')
    ]:
        val = header.get(json_field)
        if val:
            try:
                # Handle Stellar's ISO strings
                clean_val = val.replace('Z', '') if isinstance(val, str) else val
                setattr(supplier_inv, date_field, datetime.fromisoformat(clean_val))
            except:
                pass

    supplier_inv.meta_data = json.dumps(data_source) # Store full source for safety
    db.commit()

    # 2. Sync Line Items
    # Clear existing items for this ASN to avoid duplicates on resync
    db.query(models.SupplierInvoiceItem).filter(
        models.SupplierInvoiceItem.invoice_id == asn_number
    ).delete()

    for i, item in enumerate(items):
        db_item = models.SupplierInvoiceItem(
            invoice_id=asn_number,
            line_number=item.get('line_number', i + 1),
            sku=str(item.get('sku') or item.get('product_sku') or ''),
            product_name=item.get('product_name') or item.get('item_name'),
            volume=str(item.get('volume', '')),
            units_ordered=int(item.get('units_ordered') or 0),
            received_quantity=parse_float(item.get('shipped_qty_received') or item.get('received_qty')),
            inventory_fill=item.get('inventory_fill'),
            unit_cost=parse_float(item.get('unit_price') or item.get('unit_cost')),
            avg_cost=parse_float(item.get('average_cost')),
            total_cost=parse_float(item.get('total_cost') or item.get('sub_total')),
            total_deposits=parse_float(item.get('total_deposit')),
            taxes=parse_float(item.get('tax_amount')),
            all_in_cost=parse_float(item.get('all_in_cost') or item.get('total_amount_included_tax')),
            variance_quantity=parse_float(item.get('variance_qty')),
            meta_data=json.dumps(item)
        )
        db.add(db_item)
    
    db.commit()
    db.refresh(supplier_inv)
    
    # 3. Try to link back to our local 'invoices' table
    if organization_id and supplier_inv.supplier_invoice_number:
        local_inv = db.query(models.Invoice).filter(
            models.Invoice.organization_id == organization_id,
            models.Invoice.invoice_number == supplier_inv.supplier_invoice_number
        ).first()
        
        if local_inv:
            local_inv.stellar_asn_number = asn_number
            local_inv.is_posted = True
            db.commit()

    return supplier_inv
