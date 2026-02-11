import os
import httpx
import logging
import csv
import json
from io import StringIO, BytesIO
from typing import Optional, Dict, List, Union, Any

logger = logging.getLogger("stellar_client")
logger.setLevel(logging.INFO)

class StellarError(Exception):
    """Custom exception for Stellar API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)

class StellarClient:
    """
    Dedicated client for interacting with Stellar POS API.
    Handles authentication, configuration, and shared HTTP session logic.
    """
    
    def __init__(self, api_token: Optional[str] = None, base_url: Optional[str] = None):
        self.api_token = api_token or os.getenv("STELLAR_API_TOKEN")
        self.base_url = base_url or os.getenv("STELLAR_BASE_URL", "https://stock-import.stellarpos.io")
        self.inventory_url = os.getenv("STELLAR_INVENTORY_URL", "https://inventorymanagement.stellarpos.io")
        
        if not self.api_token:
            logger.warning("StellarClient initialized without API Token.")

    def _get_headers(self, tenant_id: str) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.api_token}',
            'tenant': tenant_id,
            'tenant_id': tenant_id,
            'Referer': f'https://{tenant_id}.stellarpos.io/',
            'accept': 'application/json, text/plain, */*'
        }

    async def post_invoice(
        self, 
        tenant_id: str, 
        location_id: str, 
        supplier_id: str,
        supplier_name: str,
        location_name: str, 
        invoice_number: str,
        csv_file: Any, # BytesIO or similar file-like object
        tax_ids: Optional[str] = None
    ) -> Dict:
        """
        Post an invoice CSV to Stellar.
        """
        if not self.api_token:
            raise StellarError("Stellar API Token not configured")

        url = f"{self.base_url}/api/stock/import-asn"
        
        headers = self._get_headers(tenant_id)
        
        form_data = {
            'supplier': supplier_id,
            'location': location_id,
            'supplier_name': supplier_name,
            'location_name': location_name,
            'supplierInvoiceNumber': invoice_number,
            'tax_ids': tax_ids
        }
        
        files = {
            'csvFile': ('invoice.csv', csv_file, 'text/csv')
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, files=files, data=form_data, headers=headers)
                
                if not response.is_success:
                    raise StellarError(
                        f"Stellar POST Failed: {response.status_code}",
                        status_code=response.status_code,
                        response_data=response.text
                    )
                
                return response.json()
            except httpx.RequestError as e:
                raise StellarError(f"Network error: {str(e)}")

    async def search_suppliers(self, query: str, tenant_id: str, page: int = 1, limit: int = 20) -> Dict:
        """
        Search for suppliers in Stellar.
        """
        if not self.api_token:
            raise StellarError("Stellar API Token not configured")

        url = f"{self.inventory_url}/api/suppliers/retrieve/list"
        headers = self._get_headers(tenant_id)
        params = {'search': query, 'page': page, 'limit': limit}

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url, params=params, headers=headers)
                
                if not response.is_success:
                    raise StellarError(f"Stellar Search Failed: {response.status_code}", status_code=response.status_code)
                
                return response.json()
            except httpx.RequestError as e:
                raise StellarError(f"Network error: {str(e)}")

    async def get_supplier(self, supplier_id: str, tenant_id: str) -> Dict:
        """
        Fetch a specific supplier's details from Stellar.
        """
        if not self.api_token:
            raise StellarError("Stellar API Token not configured")

        # Standard Stellar pattern for single retrieval
        url = f"{self.inventory_url}/api/suppliers/retrieve/{supplier_id}"
        headers = self._get_headers(tenant_id)

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url, headers=headers)
                
                if not response.is_success:
                    raise StellarError(f"Stellar Supplier Retrieval Failed: {response.status_code}", status_code=response.status_code)
                
                return response.json()
            except httpx.RequestError as e:
                raise StellarError(f"Network error: {str(e)}")

    @staticmethod
    def generate_csv(line_items: List[Dict]) -> BytesIO:
        """
        Helper to generate the format Stellar expects.
        line_items should be a list of dicts with 'sku', 'quantity', 'total_price'.
        """
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['SKU', 'Receiving Qty (UOM)', 'Confirmed total Cost'])
        
        for item in line_items:
            writer.writerow([
                item.get('sku', ''),
                item.get('quantity', 0),
                item.get('total_price', 0)
            ])
            
        csv_content = output.getvalue()
        csv_bytes = BytesIO(csv_content.encode('utf-8'))
        csv_bytes.seek(0)
        return csv_bytes

# Global instance for easy import
stellar_client = StellarClient()
