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
    
    # Authoritative ID approach: IDs are stable, names are display-only/dynamic
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
        ...
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
