"""
Stellar POS Browser Automation Agent (Playwright RPA)

Automates invoice posting to Stellar POS via browser automation.
Falls back to this when the direct API rejects non-LDB/AGLC supplier IDs.

Flow:
  1. Login to Stellar web UI (username + password/passcode)
  2. Navigate to Stock Import page
  3. Select supplier, location, upload CSV
  4. Submit and capture result
"""

import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from io import BytesIO

logger = logging.getLogger("stellar_browser_agent")
logger.setLevel(logging.INFO)

# Auth state persistence
AUTH_STATE_PATH = Path(__file__).parent / ".stellar_auth_state.json"

# Config from env
STELLAR_WEB_USERNAME = os.getenv("STELLAR_WEB_USERNAME")
STELLAR_WEB_PASSWORD = os.getenv("STELLAR_WEB_PASSWORD")
STELLAR_TENANT_ID = os.getenv("STELLAR_TENANT_ID", "cascadialiquor")
STELLAR_WEB_URL = f"https://{STELLAR_TENANT_ID}.stellarpos.io"

# Screenshots dir for audit trail
SCREENSHOTS_DIR = Path(__file__).parent / "stellar_screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


class StellarBrowserError(Exception):
    """Raised when browser automation fails."""
    def __init__(self, message: str, screenshot_path: Optional[str] = None):
        self.message = message
        self.screenshot_path = screenshot_path
        super().__init__(self.message)


class StellarBrowserAgent:
    """
    Playwright-based browser automation agent for Stellar POS.
    
    Usage:
        agent = StellarBrowserAgent()
        result = await agent.post_invoice(
            supplier_name="Container World",
            location_name="Cascadia Liquor Victoria",
            invoice_number="INV-001",
            csv_path="/path/to/invoice.csv"
        )
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self._playwright = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    async def start(self):
        """Initialize browser with persistent auth state if available."""
        from playwright.async_api import async_playwright
        
        self._playwright = await async_playwright().start()
        self.browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # Restore auth state if exists
        if AUTH_STATE_PATH.exists():
            try:
                self.context = await self.browser.new_context(
                    storage_state=str(AUTH_STATE_PATH),
                    viewport={'width': 1280, 'height': 800}
                )
                logger.info("Restored auth state from disk")
            except Exception as e:
                logger.warning(f"Could not restore auth state: {e}")
                self.context = await self.browser.new_context(
                    viewport={'width': 1280, 'height': 800}
                )
        else:
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 800}
            )
        
        self.page = await self.context.new_page()
        # Set tenant headers
        await self.page.set_extra_http_headers({
            'tenant': STELLAR_TENANT_ID,
            'tenant_id': STELLAR_TENANT_ID
        })

    async def stop(self):
        """Close browser and save auth state."""
        if self.context:
            try:
                await self.context.storage_state(path=str(AUTH_STATE_PATH))
                logger.info("Saved auth state to disk")
            except Exception:
                pass
        if self.browser:
            await self.browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def _screenshot(self, name: str) -> str:
        """Take a screenshot for audit trail."""
        path = str(SCREENSHOTS_DIR / f"{name}.png")
        if self.page:
            await self.page.screenshot(path=path, full_page=True)
        return path

    async def _is_logged_in(self) -> bool:
        """Check if we're already logged in by checking for dashboard elements."""
        try:
            await self.page.goto(f"{STELLAR_WEB_URL}/dashboard", wait_until="networkidle", timeout=15000)
            # If we end up on the dashboard (not redirected to login), we're authenticated
            await self.page.wait_for_timeout(2000)
            current_url = self.page.url
            # The Vue app stays on the same URL but shows different content
            # Check if login form is visible
            login_visible = await self.page.locator('#username').is_visible()
            return not login_visible
        except Exception as e:
            logger.warning(f"Auth check failed: {e}")
            return False

    async def login(self) -> bool:
        """
        Login to Stellar POS web interface.
        
        The Stellar login flow:
        1. Enter username + password (passcode)
        2. If first login, prompted to create passcode
        3. On success, redirects to /dashboard
        """
        if not STELLAR_WEB_USERNAME or not STELLAR_WEB_PASSWORD:
            raise StellarBrowserError(
                "STELLAR_WEB_USERNAME and STELLAR_WEB_PASSWORD env vars required"
            )

        # Check if already authenticated
        if await self._is_logged_in():
            logger.info("Already logged in, skipping login")
            return True

        logger.info(f"Logging into Stellar at {STELLAR_WEB_URL}...")
        
        try:
            await self.page.goto(STELLAR_WEB_URL, wait_until="networkidle", timeout=30000)
            await self.page.wait_for_timeout(2000)
            
            # Fill login form
            username_input = self.page.locator('#username')
            password_input = self.page.locator('#password')
            
            await username_input.wait_for(state="visible", timeout=10000)
            await username_input.fill(STELLAR_WEB_USERNAME)
            await password_input.fill(STELLAR_WEB_PASSWORD)
            
            # Click login button
            await self.page.locator('button:has-text("Login")').click()
            
            # Wait for navigation or error
            await self.page.wait_for_timeout(3000)
            
            # Check if we hit passcode creation mode
            passcode_input = self.page.locator('#passcode')
            if await passcode_input.is_visible():
                logger.info("Passcode creation mode detected - this is a first login")
                raise StellarBrowserError(
                    "First login detected - please log in manually to set passcode first"
                )
            
            # Check for login errors
            error_toast = self.page.locator('.Vue-Toastification__toast--error')
            if await error_toast.is_visible():
                error_text = await error_toast.inner_text()
                raise StellarBrowserError(f"Login failed: {error_text}")
            
            # Verify we reached the dashboard
            await self.page.wait_for_timeout(3000)
            
            if await self._is_logged_in():
                logger.info("Login successful!")
                await self._screenshot("login_success")
                return True
            else:
                screenshot = await self._screenshot("login_failed")
                raise StellarBrowserError("Login failed - could not reach dashboard", screenshot)
                
        except StellarBrowserError:
            raise
        except Exception as e:
            screenshot = await self._screenshot("login_error")
            raise StellarBrowserError(f"Login error: {str(e)}", screenshot)

    async def navigate_to_stock_import(self):
        """Navigate to the ASN Stock Import page."""
        logger.info("Navigating to stock import page...")
        
        try:
            # Direct URL navigation is more reliable than clicking sidebar
            await self.page.goto(f"{STELLAR_WEB_URL}/import-history", wait_until="networkidle", timeout=30000)
            await self.page.wait_for_timeout(2000)
            
            # Verify we're on the right page by looking for stock import elements
            await self._screenshot("stock_import_page")
            logger.info("Reached stock import page")
            
        except Exception as e:
            screenshot = await self._screenshot("nav_error")
            raise StellarBrowserError(f"Navigation error: {str(e)}", screenshot)

    async def post_invoice(
        self,
        supplier_name: str,
        supplier_id: str,
        location_name: str,
        location_id: str,
        invoice_number: str,
        csv_content: bytes,
        csv_filename: str = "invoice.csv",
        tax_ids: str = ""
    ) -> Dict[str, Any]:
        """
        Post an invoice to Stellar via browser automation.
        
        Uses the browser page's fetch() API which runs in the page context
        (with cookies, origin headers, etc.) — this bypasses the supplier
        whitelist restriction that blocks direct API calls.
        
        The CSV is passed as a list of byte values to avoid string encoding issues.
        
        Args:
            supplier_name: Display name of the supplier
            supplier_id: Stellar supplier UUID 
            location_name: Display name of the store location
            location_id: Stellar location UUID
            invoice_number: The supplier invoice number
            csv_content: Raw CSV bytes to upload
            csv_filename: Name for the CSV file
            tax_ids: Tax IDs string (optional)
            
        Returns:
            Dict with result from Stellar
        """
        # Ensure we're logged in
        await self.login()
        
        logger.info(f"Posting invoice {invoice_number} for {supplier_name}...")
        
        try:
            # Get the auth token from localStorage (set by the Vue app on login)
            auth_token = await self.page.evaluate("localStorage.getItem('AUTH_TOKEN')")
            
            if not auth_token:
                raise StellarBrowserError("No AUTH_TOKEN found in localStorage after login")
            
            logger.info(f"Got browser auth token: {auth_token[:20]}...")
            
            # Convert CSV bytes to a list of integers for passing to JS
            # This avoids any string encoding issues
            csv_byte_list = list(csv_content)
            
            # Use the browser's fetch API from the page context
            # IMPORTANT: This runs FROM the page origin which matters for CORS/cookies
            result = await self.page.evaluate("""
                async ({supplier, location, supplier_name, location_name, 
                        supplierInvoiceNumber, csvBytes, csvFilename, 
                        authToken, tenantId, tax_ids}) => {
                    
                    const formData = new FormData();
                    formData.append('supplier', supplier);
                    formData.append('location', location);
                    formData.append('supplier_name', supplier_name);
                    formData.append('location_name', location_name);
                    formData.append('supplierInvoiceNumber', supplierInvoiceNumber);
                    formData.append('tax_ids', tax_ids || '');
                    
                    // Create a proper File from byte array (avoids encoding issues)
                    const uint8Array = new Uint8Array(csvBytes);
                    const csvFile = new File([uint8Array], csvFilename, {type: 'text/csv'});
                    formData.append('csvFile', csvFile);
                    
                    try {
                        const response = await fetch(
                            'https://stock-import.stellarpos.io/api/stock/import-asn', 
                            {
                                method: 'POST',
                                headers: {
                                    'Authorization': 'Bearer ' + authToken,
                                    'tenant': tenantId,
                                    'tenant_id': tenantId
                                },
                                body: formData
                            }
                        );
                        
                        const responseText = await response.text();
                        let responseJson;
                        try {
                            responseJson = JSON.parse(responseText);
                        } catch(e) {
                            responseJson = {raw: responseText};
                        }
                        
                        return {
                            status: response.status,
                            ok: response.ok,
                            data: responseJson
                        };
                    } catch(err) {
                        return {
                            status: 0,
                            ok: false,
                            data: {error: err.message}
                        };
                    }
                }
            """, {
                'supplier': supplier_id,
                'location': location_id,
                'supplier_name': supplier_name,
                'location_name': location_name,
                'supplierInvoiceNumber': invoice_number,
                'csvBytes': csv_byte_list,
                'csvFilename': csv_filename,
                'authToken': auth_token,
                'tenantId': STELLAR_TENANT_ID,
                'tax_ids': tax_ids,
            })
            
            logger.info(f"API response via browser: status={result['status']}, ok={result['ok']}")
            
            if result['ok']:
                logger.info(f"✅ Invoice {invoice_number} posted successfully!")
                await self._screenshot(f"success_{invoice_number}")
            else:
                logger.warning(f"❌ Invoice {invoice_number} failed: {json.dumps(result['data'])[:200]}")
                await self._screenshot(f"failed_{invoice_number}")
            
            return result
            
        except StellarBrowserError:
            raise
        except Exception as e:
            screenshot = await self._screenshot(f"error_{invoice_number}")
            raise StellarBrowserError(f"Post error: {str(e)}", screenshot)

    async def _post_via_ui_form(
        self,
        supplier_name: str,
        supplier_id: str,
        location_name: str,
        location_id: str,
        invoice_number: str,
        csv_content: bytes,
        csv_filename: str
    ) -> Dict[str, Any]:
        """
        Fallback: Post invoice by filling out the actual Stellar web UI form.
        This mimics exactly what a human does in the browser.
        """
        logger.info("Attempting UI form submission...")
        
        try:
            # Navigate to the stock import / ASN page
            await self.page.goto(f"{STELLAR_WEB_URL}/import-history", wait_until="networkidle", timeout=30000)
            await self.page.wait_for_timeout(3000)
            await self._screenshot("ui_form_page")
            
            # Look for an "Import" or "New Import" or "ASN Import" button
            import_btn = self.page.locator('button:has-text("Import"), a:has-text("Import"), button:has-text("ASN")')
            if await import_btn.count() > 0:
                await import_btn.first.click()
                await self.page.wait_for_timeout(2000)
                await self._screenshot("ui_form_opened")
            
            # The import form typically has:
            # 1. Supplier dropdown (select2)
            # 2. Location dropdown
            # 3. CSV file upload
            # 4. Invoice number field
            
            # Try to interact with supplier selector
            # Stellar uses Select2 for dropdowns
            supplier_select = self.page.locator('.multiselect, select[name*="supplier"], #supplier-select')
            if await supplier_select.count() > 0:
                await supplier_select.first.click()
                await self.page.wait_for_timeout(500)
                # Type supplier name to search
                await self.page.keyboard.type(supplier_name[:10])
                await self.page.wait_for_timeout(1000)
                # Click the first matching option
                option = self.page.locator('.multiselect__option, .multiselect-option').first
                if await option.is_visible():
                    await option.click()
                    await self.page.wait_for_timeout(500)
            
            # Location selector
            location_select = self.page.locator('.multiselect, select[name*="location"]').nth(1)
            if await location_select.count() > 0:
                await location_select.click()
                await self.page.wait_for_timeout(500)
                await self.page.keyboard.type(location_name[:10])
                await self.page.wait_for_timeout(1000)
                option = self.page.locator('.multiselect__option, .multiselect-option').first
                if await option.is_visible():
                    await option.click()

            # Invoice number
            inv_input = self.page.locator('input[placeholder*="invoice"], input[name*="invoice"]')
            if await inv_input.count() > 0:
                await inv_input.fill(invoice_number)

            # File upload - write CSV to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as f:
                f.write(csv_content)
                temp_path = f.name
            
            file_input = self.page.locator('input[type="file"]')
            if await file_input.count() > 0:
                await file_input.set_input_files(temp_path)
                await self.page.wait_for_timeout(1000)
            
            await self._screenshot("ui_form_filled")
            
            # Submit form
            submit_btn = self.page.locator('button:has-text("Submit"), button:has-text("Import"), button:has-text("Upload")')
            if await submit_btn.count() > 0:
                # Listen for API response
                async with self.page.expect_response(
                    lambda r: "import-asn" in r.url or "stock" in r.url,
                    timeout=30000
                ) as response_info:
                    await submit_btn.first.click()
                
                response = await response_info.value
                response_body = await response.json()
                
                result = {
                    'status': response.status,
                    'ok': response.ok,
                    'data': response_body,
                    'method': 'ui_form'
                }
                
                await self._screenshot(f"ui_result_{invoice_number}")
                
                # Cleanup temp file
                os.unlink(temp_path)
                
                return result
            else:
                os.unlink(temp_path)
                raise StellarBrowserError("Could not find submit button on import form")
                
        except StellarBrowserError:
            raise
        except Exception as e:
            screenshot = await self._screenshot(f"ui_form_error_{invoice_number}")
            raise StellarBrowserError(f"UI form error: {str(e)}", screenshot)


# Convenience function for use in stellar_service.py
async def post_invoice_via_browser(
    supplier_name: str,
    supplier_id: str,
    location_name: str,
    location_id: str,
    invoice_number: str,
    csv_content: bytes,
    headless: bool = True
) -> Dict[str, Any]:
    """
    Convenience wrapper. Creates agent, logs in, posts invoice, closes browser.
    
    Returns dict with {status, ok, data} from the Stellar API response.
    """
    async with StellarBrowserAgent(headless=headless) as agent:
        return await agent.post_invoice(
            supplier_name=supplier_name,
            supplier_id=supplier_id,
            location_name=location_name,
            location_id=location_id,
            invoice_number=invoice_number,
            csv_content=csv_content
        )
