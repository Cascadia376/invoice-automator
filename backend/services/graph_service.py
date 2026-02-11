import os
import logging
import msal
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class GraphService:
    def __init__(self):
        self.client_id = os.getenv("AZURE_CLIENT_ID")
        self.client_secret = os.getenv("AZURE_CLIENT_SECRET")
        self.tenant_id = os.getenv("AZURE_TENANT_ID")
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.scopes = ["https://graph.microsoft.com/.default"]
        self._access_token = None
        self._token_expires = 0

    def _get_access_token(self) -> str:
        """Acquire access token using MSAL client credentials flow."""
        # Simple expiration check
        if self._access_token and datetime.utcnow().timestamp() < self._token_expires:
            return self._access_token

        app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret
        )
        
        result = app.acquire_token_silent(self.scopes, account=None)
        if not result:
            result = app.acquire_token_for_client(scopes=self.scopes)

        if "access_token" in result:
            self._access_token = result["access_token"]
            # Set expiration with a 5-minute buffer
            self._token_expires = datetime.utcnow().timestamp() + result.get("expires_in", 3600) - 300
            return self._access_token
        else:
            error = result.get("error")
            error_desc = result.get("error_description")
            raise Exception(f"Failed to acquire Azure token: {error} - {error_desc}")

    def get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json"
        }

    def list_unread_emails_with_attachments(self, user_email: str) -> List[Dict[str, Any]]:
        """List unread emails with attachments for a specific user."""
        url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages"
        params = {
            "$filter": "isRead eq false and hasAttachments eq true",
            "$select": "id,subject,receivedDateTime,from,hasAttachments"
        }
        
        response = requests.get(url, headers=self.get_headers(), params=params)
        response.raise_for_status()
        return response.json().get("value", [])

    def get_message_attachments(self, user_email: str, message_id: str) -> List[Dict[str, Any]]:
        """Get attachments for a specific email message."""
        url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages/{message_id}/attachments"
        response = requests.get(url, headers=self.get_headers())
        response.raise_for_status()
        return response.json().get("value", [])

    def download_attachment(self, user_email: str, message_id: str, attachment_id: str) -> bytes:
        """Download the content of an email attachment."""
        url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages/{message_id}/attachments/{attachment_id}/$value"
        response = requests.get(url, headers=self.get_headers())
        response.raise_for_status()
        return response.content

    def mark_as_read(self, user_email: str, message_id: str):
        """Mark an email message as read."""
        url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages/{message_id}"
        data = {"isRead": True}
        response = requests.patch(url, headers=self.get_headers(), json=data)
        response.raise_for_status()

    def get_drive_delta(self, user_email: str, delta_link: Optional[str] = None) -> Dict[str, Any]:
        """Get changes in OneDrive using Delta Query."""
        if delta_link:
            url = delta_link
        else:
            url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/root/delta"
        
        response = requests.get(url, headers=self.get_headers())
        response.raise_for_status()
        return response.json()

    def download_drive_item(self, user_email: str, item_id: str) -> bytes:
        """Download a file from OneDrive."""
        url = f"https://graph.microsoft.com/v1.0/users/{user_email}/drive/items/{item_id}/content"
        response = requests.get(url, headers=self.get_headers())
        response.raise_for_status()
        return response.content
