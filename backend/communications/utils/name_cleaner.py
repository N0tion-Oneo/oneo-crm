"""
Utility for cleaning display names from email systems
"""
import re


def clean_display_name(display_name: str, email_address: str = None) -> str:
    """
    Clean a display name from an email system.
    
    Some email systems (via UniPile) return problematic display names like:
    - "'email@example.com'" (email wrapped in quotes)
    - "email@example.com" (just the email as the name)
    - "'John Doe (john@example.com)'" (name and email wrapped in quotes)
    
    Args:
        display_name: The display name to clean
        email_address: Optional email address to check against
        
    Returns:
        Cleaned display name, or empty string if it's just the email
    """
    if not display_name:
        return ''
    
    # Remove surrounding quotes (single or double)
    cleaned = display_name.strip()
    
    # Remove surrounding single quotes
    if cleaned.startswith("'") and cleaned.endswith("'"):
        cleaned = cleaned[1:-1]
    
    # Remove surrounding double quotes
    if cleaned.startswith('"') and cleaned.endswith('"'):
        cleaned = cleaned[1:-1]
    
    # Strip again after removing quotes
    cleaned = cleaned.strip()
    
    # If the display name is just the email address, return empty
    if email_address and cleaned.lower() == email_address.lower():
        return ''
    
    # If it looks like just an email address, return empty
    if '@' in cleaned and not ' ' in cleaned and cleaned.count('@') == 1:
        # It's likely just an email address
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, cleaned):
            return ''
    
    return cleaned