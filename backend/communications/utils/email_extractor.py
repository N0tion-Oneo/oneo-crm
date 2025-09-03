"""
Email extraction utilities from raw webhook data
Following the same pattern as phone_extractor.py for WhatsApp
"""
import re
import logging

logger = logging.getLogger(__name__)


def extract_email_from_webhook(webhook_data: dict, our_email: str = '') -> str:
    """
    DEPRECATED: Use extract_email_sender_info() and extract_email_recipients_info() instead
    
    Extract contact email address from raw email webhook data
    For backward compatibility only - returns sender's email
    
    Args:
        webhook_data: Raw webhook data from UniPile
        our_email: Our business email address to distinguish direction
        
    Returns:
        Clean email address or empty string
    """
    if not isinstance(webhook_data, dict):
        return ''
    
    # Always return sender's email for backward compatibility
    sender_info = extract_email_sender_info(webhook_data)
    if isinstance(sender_info, dict):
        return sender_info.get('email', '')
    
    return ''


def extract_email_subject_from_webhook(webhook_data: dict) -> str:
    """
    Extract email subject from webhook data
    
    Args:
        webhook_data: Raw webhook data
        
    Returns:
        Email subject or empty string
    """
    if not isinstance(webhook_data, dict):
        return ''
    
    # Primary: Use subject field
    subject = webhook_data.get('subject', '')
    if subject and subject.strip():
        return subject.strip()
    
    # Fallback: check headers
    headers = webhook_data.get('headers', {})
    if isinstance(headers, dict):
        header_subject = headers.get('Subject', headers.get('subject', ''))
        if header_subject and header_subject.strip():
            return header_subject.strip()
    
    return ''


def extract_email_name_from_webhook(webhook_data: dict, our_email: str = '') -> str:
    """
    Extract contact display name from email webhook data
    
    For inbound emails: Returns the sender's display name
    For outbound emails: Returns the primary recipient's display name
    
    Args:
        webhook_data: Raw webhook data
        our_email: Our business email address
        
    Returns:
        Contact display name or empty string
    """
    if not isinstance(webhook_data, dict):
        return ''
    
    # Determine direction to know which name to extract
    direction = determine_email_direction(webhook_data, our_email)
    
    if direction == 'inbound':
        # INBOUND: Extract sender's name
        from_attendee = webhook_data.get('from_attendee', {})
        if isinstance(from_attendee, dict):
            sender_name = from_attendee.get('display_name', '')
            sender_email = from_attendee.get('identifier', '')
            
            # Only return name if it's different from email address
            if sender_name and sender_name.strip() and sender_name != sender_email:
                return sender_name.strip()
        
        # Fallback: try other sender name fields
        name_fields = ['from_name', 'sender_name', 'sender_display_name']
        for field in name_fields:
            name = webhook_data.get(field, '')
            if name and isinstance(name, str) and name.strip():
                return name.strip()
    
    else:
        # OUTBOUND: Extract primary recipient's name
        to_attendees = webhook_data.get('to_attendees', [])
        if isinstance(to_attendees, list) and len(to_attendees) > 0:
            first_recipient = to_attendees[0]
            if isinstance(first_recipient, dict):
                recipient_name = first_recipient.get('display_name', '')
                recipient_email = first_recipient.get('identifier', '')
                
                # Only return name if it's different from email address
                if recipient_name and recipient_name.strip() and recipient_name != recipient_email:
                    return recipient_name.strip()
        
        # Fallback: try other recipient name fields
        name_fields = ['to_name', 'recipient_name', 'recipient_display_name']
        for field in name_fields:
            name = webhook_data.get(field, '')
            if name and isinstance(name, str) and name.strip():
                return name.strip()
    
    return ''


def determine_email_direction(webhook_data: dict, our_email: str = '') -> str:
    """
    Determine email direction from webhook data
    
    Args:
        webhook_data: Raw webhook data
        our_email: Our business email address (account owner's email)
        
    Returns:
        'inbound' or 'outbound'
    """
    if not isinstance(webhook_data, dict):
        return 'inbound'
    
    # Check event type first (most reliable for webhooks)
    event_type = webhook_data.get('event', '').lower()
    if 'sent' in event_type or 'outbound' in event_type:
        logger.debug(f"Direction from event type '{event_type}': outbound")
        return 'outbound'
    elif 'received' in event_type or 'inbound' in event_type:
        logger.debug(f"Direction from event type '{event_type}': inbound")
        return 'inbound'
    
    # Check explicit direction field
    direction_field = webhook_data.get('direction', '').lower()
    if direction_field in ['inbound', 'in', 'incoming']:
        return 'inbound'
    elif direction_field in ['outbound', 'out', 'outgoing']:
        return 'outbound'
    
    # Extract sender email - try both formats
    sender_email = ''
    
    # Try from_attendee format first
    from_attendee = webhook_data.get('from_attendee', {})
    if isinstance(from_attendee, dict):
        sender_email = from_attendee.get('identifier', '').lower()
    
    # Try direct 'from' field (UniPile format)
    if not sender_email:
        from_field = webhook_data.get('from', {})
        if isinstance(from_field, dict):
            sender_email = from_field.get('email', from_field.get('identifier', '')).lower()
    
    # If sender is our email, it's outbound
    if sender_email and sender_email == our_email.lower():
        logger.debug(f"Outbound: sender ({sender_email}) is our email")
        return 'outbound'
    
    # Check if our email is in recipients (inbound) - try both formats
    
    # Try to_attendees format
    to_attendees = webhook_data.get('to_attendees', [])
    if isinstance(to_attendees, list):
        for recipient in to_attendees:
            if isinstance(recipient, dict):
                recipient_email = recipient.get('identifier', '').lower()
                if recipient_email == our_email.lower():
                    logger.debug(f"Inbound: our email ({our_email}) is in to_attendees")
                    return 'inbound'
    
    # Try direct 'to' field (UniPile format)
    to_field = webhook_data.get('to', [])
    if isinstance(to_field, list):
        for recipient in to_field:
            if isinstance(recipient, dict):
                recipient_email = recipient.get('email', recipient.get('identifier', '')).lower()
                if recipient_email == our_email.lower():
                    logger.debug(f"Inbound: our email ({our_email}) is in 'to' field")
                    return 'inbound'
    
    # Default to inbound if we can't determine
    logger.debug(f"Could not determine direction - defaulting to inbound. Sender: {sender_email}, Our email: {our_email}")
    return 'inbound'


def extract_email_thread_id(webhook_data: dict) -> str:
    """
    Extract conversation/thread ID from email webhook data
    
    Args:
        webhook_data: Raw webhook data
        
    Returns:
        Thread ID or fallback ID
    """
    if not isinstance(webhook_data, dict):
        return ''
    
    # Priority order for thread ID fields
    thread_fields = [
        'thread_id',         # Most reliable for email threading
        'conversation_id',   # Alternative threading ID
        'message_id',        # Email message ID
        'id'                 # Generic ID
    ]
    
    for field in thread_fields:
        value = webhook_data.get(field)
        if value:
            return str(value)
    
    # Fallback: create ID from subject or timestamp
    subject = webhook_data.get('subject', '')
    if subject:
        # Create a simple hash from subject for threading
        import hashlib
        return f"subj_{hashlib.md5(subject.encode()).hexdigest()[:8]}"
    
    # Last resort: use timestamp
    import time
    return f"email_{int(time.time())}"


def extract_email_message_id(webhook_data: dict) -> str:
    """
    Extract unique message ID from email webhook data
    
    Args:
        webhook_data: Raw webhook data
        
    Returns:
        Unique message ID
    """
    if not isinstance(webhook_data, dict):
        return ''
    
    # Priority order for message ID fields
    # IMPORTANT: email_id is checked first to ensure webhook and sync use same UniPile ID
    id_fields = [
        'email_id',          # UniPile email ID (used in webhooks)
        'id',                # UniPile message ID (used in sync)
        'message_id',        # Standard email Message-ID header (Gmail/Outlook)
        'external_id',       # External system ID
        'uid'                # UID from email server
    ]
    
    for field in id_fields:
        value = webhook_data.get(field)
        if value:
            return str(value)
    
    # Check headers for Message-ID
    headers = webhook_data.get('headers', {})
    if isinstance(headers, dict):
        message_id = headers.get('Message-ID', headers.get('message-id', ''))
        if message_id:
            return str(message_id)
    
    # Last resort: generate ID from timestamp
    import time
    return f"msg_{int(time.time())}"


def extract_email_attachments(webhook_data: dict) -> list:
    """
    Extract attachment information from email webhook data
    
    Args:
        webhook_data: Raw webhook data
        
    Returns:
        List of attachment dictionaries
    """
    if not isinstance(webhook_data, dict):
        return []
    
    attachments = webhook_data.get('attachments', [])
    if not isinstance(attachments, list):
        return []
    
    processed_attachments = []
    for attachment in attachments:
        if isinstance(attachment, dict):
            processed_attachments.append({
                'filename': attachment.get('filename', 'attachment'),
                'content_type': attachment.get('content_type', attachment.get('mime_type', 'application/octet-stream')),
                'size': attachment.get('size', 0),
                'attachment_id': attachment.get('id', attachment.get('attachment_id')),
                'download_url': attachment.get('download_url', attachment.get('url'))
            })
    
    return processed_attachments


def extract_email_folder_labels(webhook_data: dict) -> dict:
    """
    Extract folder and label information from email webhook data
    
    Args:
        webhook_data: Raw webhook data
        
    Returns:
        Dictionary with folder and labels info including read status
    """
    if not isinstance(webhook_data, dict):
        return {'folder': '', 'labels': [], 'read': False}
    
    # Check read status based on read_date field
    # read_date is null for unread emails, has timestamp for read emails
    read_date = webhook_data.get('read_date')
    is_read = read_date is not None
    
    # Also get folders (note: it's 'folders' not 'folder' in the webhook)
    folders = webhook_data.get('folders', [])
    folder = folders[0] if folders else ''
    
    return {
        'folder': folder,
        'labels': webhook_data.get('labels', []),
        'read': is_read,
        'read_date': read_date  # Include the actual read date for reference
    }


def get_display_name_or_email(contact_name: str, email_address: str) -> str:
    """
    Get display name for contact, fallback to email address
    
    Args:
        contact_name: Contact display name (may be empty)
        email_address: Email address (should not be empty)
        
    Returns:
        Contact name if available, otherwise email address
    """
    if contact_name and contact_name.strip():
        # Don't return name if it's the same as email
        if contact_name.strip() != email_address:
            return contact_name.strip()
    
    if email_address:
        return email_address.strip()
    
    return "Unknown Contact"


def extract_email_recipients_info(webhook_data: dict) -> dict:
    """
    Extract all recipient information (to, cc, bcc) from email webhook data
    
    Args:
        webhook_data: Raw webhook data
        
    Returns:
        Dictionary with recipient lists
    """
    if not isinstance(webhook_data, dict):
        return {'to': [], 'cc': [], 'bcc': []}
    
    def extract_attendee_list(attendees):
        """Extract list of attendees with name and email"""
        if not isinstance(attendees, list):
            return []
        
        result = []
        for attendee in attendees:
            if isinstance(attendee, dict):
                # Handle both formats: to_attendees and to
                email = attendee.get('identifier', attendee.get('email', ''))
                name = attendee.get('display_name', attendee.get('name', ''))
                if email:
                    result.append({
                        'email': email,
                        'name': name
                    })
        return result
    
    # Try both field formats
    to_recipients = webhook_data.get('to_attendees', webhook_data.get('to', []))
    cc_recipients = webhook_data.get('cc_attendees', webhook_data.get('cc', []))
    bcc_recipients = webhook_data.get('bcc_attendees', webhook_data.get('bcc', []))
    
    return {
        'to': extract_attendee_list(to_recipients),
        'cc': extract_attendee_list(cc_recipients),
        'bcc': extract_attendee_list(bcc_recipients)
    }


# Helper functions

def _clean_email_address(email: str) -> str:
    """Clean and validate email address"""
    if not email:
        return ''
    
    email = str(email).strip().lower()
    
    # Basic email validation
    if '@' not in email or '.' not in email.split('@')[-1]:
        logger.warning(f"Invalid email format: {email}")
        return ''
    
    return email


def _extract_email_from_field(field_value) -> str:
    """Extract email from various field formats"""
    if not field_value:
        return ''
    
    # Handle dictionary format
    if isinstance(field_value, dict):
        return _clean_email_address(field_value.get('identifier', field_value.get('email', '')))
    
    # Handle string format - look for email pattern
    if isinstance(field_value, str):
        # Simple email regex
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', field_value)
        if email_match:
            return _clean_email_address(email_match.group())
    
    return ''


def extract_email_sender_info(webhook_data: dict) -> dict:
    """
    Extract complete sender information for email messages
    
    Returns:
        Dict with sender info: {
            'name': str,
            'email': str,
            'identifier': str,
            'is_business_email': bool
        }
    """
    if not isinstance(webhook_data, dict):
        return {
            'name': 'Unknown Sender',
            'email': '',
            'identifier': '',
            'is_business_email': False
        }
    
    # Try both formats: from_attendee and from
    from_attendee = webhook_data.get('from_attendee', {})
    from_field = webhook_data.get('from', {})
    
    # Extract sender details
    sender_name = 'Unknown Sender'
    sender_email = ''
    sender_identifier = ''
    
    # Try from_attendee format first
    if isinstance(from_attendee, dict) and from_attendee:
        sender_identifier = from_attendee.get('identifier', '')
        sender_email = _clean_email_address(sender_identifier)
        sender_name = from_attendee.get('display_name', '')
    # Try from field format
    elif isinstance(from_field, dict) and from_field:
        sender_email = _clean_email_address(from_field.get('email', from_field.get('identifier', '')))
        sender_identifier = sender_email
        sender_name = from_field.get('name', from_field.get('display_name', ''))
    
    # If display name is same as email or empty, try to extract name from email
    if not sender_name or sender_name == sender_email:
        if sender_email:
            # Extract name part from email (before @)
            sender_name = sender_email.split('@')[0].replace('.', ' ').title()
    
    # Determine if this looks like a business email
    is_business = False
    if sender_email:
        business_indicators = ['noreply', 'no-reply', 'support', 'info', 'admin', 'notifications']
        email_local = sender_email.split('@')[0].lower()
        is_business = any(indicator in email_local for indicator in business_indicators)
    
    result = {
        'name': sender_name,
        'email': sender_email,
        'identifier': sender_identifier,
        'is_business_email': is_business
    }
    
    return result