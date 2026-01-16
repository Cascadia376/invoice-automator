
import os
import logging

# Configure logging for mock emails
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EmailService")

def send_vendor_email(to_email: str, subject: str, body: str, attachments: list = None):
    """
    Mock function to send emails. 
    In production, this would use SMTP, SendGrid, Amazon SES, or Resend.
    """
    logger.info(f"--- MOCK EMAIL START ---")
    logger.info(f"To: {to_email}")
    logger.info(f"Subject: {subject}")
    logger.info(f"Body: {body}")
    if attachments:
        for attachment in attachments:
            logger.info(f"Attachment: {attachment.get('filename')} ({len(attachment.get('content', ''))} bytes)")
    logger.info(f"--- MOCK EMAIL END ---")
    
    # Return True to simulate success
    return True

def format_issue_email(vendor_name: str, invoice_number: str, issue_type: str, details: str):
    """
    Format a standardized email for reporting invoice issues to vendors.
    """
    subject = f"Issue Reported: Invoice #{invoice_number} - {vendor_name}"
    body = f"""Dear {vendor_name} Team,

We are reporting an issue with Invoice #{invoice_number}.

Issue Type: {issue_type.replace('_', ' ').capitalize()}
Details: {details}

Please let us know how you plan to resolve this (e.g., replacement, credit note).

Thank you,
Cascadia Inventory Team
"""
    return subject, body
