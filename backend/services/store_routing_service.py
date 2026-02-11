"""
Store Routing Service

Resolves the destination store for an invoice based on extracted
license number and/or store name from the invoice header.
"""

import re
import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session

import models

logger = logging.getLogger(__name__)

# License numbers are 6 digits, typically starting with 19
LICENSE_PATTERN = re.compile(r'\b(1[89]\d{4})\b')

# Common label patterns that precede a license number
LICENSE_LABEL_PATTERNS = [
    r'(?:LRS|Lic|License|Licensee|Licence)[\s#:.]*(\d{5,6})',
    r'(?:Permit|Reg)[\s#:.]*(\d{5,6})',
]


def extract_license_from_text(text: str) -> Optional[str]:
    """
    Extract a license number from arbitrary text.
    Tries labeled patterns first (e.g., "LRS# 195074"), 
    then falls back to bare 6-digit pattern.
    
    Args:
        text: Any text that might contain a license number
        
    Returns:
        License number string, or None
    """
    if not text:
        return None
    
    # Try labeled patterns first (higher confidence)
    for pattern in LICENSE_LABEL_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            num = match.group(1)
            # Pad to 6 digits if needed
            if len(num) == 5:
                num = '1' + num  # Unlikely but safe
            logger.info(f"License found via label pattern: {num}")
            return num
    
    # Fall back to bare pattern
    match = LICENSE_PATTERN.search(text)
    if match:
        logger.info(f"License found via bare pattern: {match.group(1)}")
        return match.group(1)
    
    return None


def resolve_store_from_license(
    db: Session, 
    license_number: str
) -> Optional[models.Store]:
    """
    Look up a store by its license number.
    
    Args:
        db: Database session
        license_number: 6-digit license number
        
    Returns:
        Store object if found, None otherwise
    """
    store = db.query(models.Store).filter(
        models.Store.license_number == license_number,
        models.Store.status == 'active'
    ).first()
    
    if store:
        logger.info(f"Store resolved: {store.name} (ID: {store.store_id}) from license {license_number}")
    else:
        logger.warning(f"No store found for license number: {license_number}")
    
    return store


def resolve_store(
    db: Session,
    extracted_fields: dict,
    organization_id: str = None
) -> Tuple[Optional[models.Store], Optional[str]]:
    """
    Resolve the destination store from extracted invoice fields.
    
    Searches through all available text fields for a license number,
    then cross-validates with store name if available.
    
    Args:
        db: Database session
        extracted_fields: Dict of extracted Textract summary fields
        organization_id: Optional org filter
        
    Returns:
        Tuple of (Store object or None, license_number or None)
    """
    license_number = None
    store_name_hint = None
    
    # Fields that might contain the license number (ordered by likelihood)
    fields_to_check = [
        'RECEIVER_NAME',
        'RECEIVER_ADDRESS', 
        'receiver_name',
        'receiver_address',
        'vendor_address',  # Sometimes Textract mislabels receiver as vendor
        'OTHER',
    ]
    
    # Also check raw_extraction_results keys
    for field_name in fields_to_check:
        value = extracted_fields.get(field_name, '')
        if isinstance(value, dict):
            value = value.get('value', '')
        if value:
            found = extract_license_from_text(str(value))
            if found:
                license_number = found
                logger.info(f"License {found} extracted from field: {field_name}")
                break
    
    # If not found in specific fields, search ALL field values
    if not license_number:
        for key, value in extracted_fields.items():
            if isinstance(value, dict):
                value = value.get('value', '')
            if value:
                found = extract_license_from_text(str(value))
                if found:
                    license_number = found
                    logger.info(f"License {found} extracted from fallback field: {key}")
                    break
    
    if not license_number:
        logger.info("No license number found in any extracted fields")
        return None, None
    
    # Look up store
    store = resolve_store_from_license(db, license_number)
    
    # Cross-validate with store name if available
    if store:
        receiver_name = (
            extracted_fields.get('RECEIVER_NAME', '') or 
            extracted_fields.get('receiver_name', '')
        )
        if isinstance(receiver_name, dict):
            receiver_name = receiver_name.get('value', '')
        
        if receiver_name and store.name:
            # Simple containment check (e.g., "Cascadia Liquor Port Alberni" contains "Port Alberni")
            store_name_lower = store.name.lower()
            receiver_lower = receiver_name.lower()
            if store_name_lower in receiver_lower or any(
                word in receiver_lower for word in store_name_lower.split() if len(word) > 3
            ):
                logger.info(f"Cross-validation passed: receiver '{receiver_name}' matches store '{store.name}'")
            else:
                logger.warning(f"Cross-validation mismatch: receiver '{receiver_name}' vs store '{store.name}' - using license match anyway")
    
    return store, license_number
