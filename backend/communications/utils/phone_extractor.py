"""
Simple phone number extraction from raw webhook data
"""
import re
import logging

logger = logging.getLogger(__name__)


def extract_whatsapp_phone_from_webhook(webhook_data: dict) -> str:
    """
    Extract phone number from raw WhatsApp webhook data
    
    For 1-on-1 chats: Returns the contact's phone number
    For group chats: Returns empty string (groups don't have individual phone numbers)
    
    Args:
        webhook_data: Raw webhook data from UniPile
        
    Returns:
        Clean phone number or empty string
    """
    if not isinstance(webhook_data, dict):
        return ''
    
    # Check if this is a group chat
    is_group = webhook_data.get('is_group', False)
    
    if is_group:
        # GROUP CHAT: No individual phone number - return empty
        # Groups use group IDs like "27720720045-1419774108@g.us"
        logger.debug("Group chat detected - not extracting individual phone number")
        return ''
    
    # 1-ON-1 CHAT: Extract contact phone using provider_chat_id logic
    phone = ''
    
    # Primary: Use provider_chat_id (always the contact we're speaking to)
    provider_chat_id = webhook_data.get('provider_chat_id', '')
    if provider_chat_id:
        phone = str(provider_chat_id)
        logger.debug(f"Extracted contact phone from provider_chat_id: {phone}")
    
    # Fallback 1: Try attendees array 
    if not phone:
        attendees = webhook_data.get('attendees', [])
        if attendees and isinstance(attendees, list) and len(attendees) > 0:
            first_attendee = attendees[0]
            if isinstance(first_attendee, dict):
                attendee_provider_id = first_attendee.get('attendee_provider_id')
                if attendee_provider_id:
                    phone = str(attendee_provider_id)
                    logger.debug(f"Extracted contact phone from attendees: {phone}")
    
    # Fallback 2: Try sender (for backward compatibility)
    if not phone:
        sender = webhook_data.get('sender', {})
        if isinstance(sender, dict):
            attendee_provider_id = sender.get('attendee_provider_id')
            if attendee_provider_id:
                phone = str(attendee_provider_id)
                logger.debug(f"Extracted contact phone from sender: {phone}")
    
    # Fallback 3: Try other fields
    if not phone:
        phone_fields = [
            'provider_chat_id',   # The contact we're speaking to
            'from',               # Generic sender JID
            'participant',        # Group messages
            'phone',              # Direct phone field
            'contact_phone',      # Contact info
            'to',                 # For outbound messages
            'recipient'           # Alternative recipient
        ]
        
        for field in phone_fields:
            value = webhook_data.get(field, '')
            if value:
                phone = str(value)
                logger.debug(f"Fallback: found phone in field '{field}': {phone}")
                break
    
    if not phone:
        logger.debug("No phone found in webhook data")
        return ''
    
    # Handle WhatsApp JID format: phone@s.whatsapp.net
    if '@s.whatsapp.net' in phone:
        phone = phone.split('@s.whatsapp.net')[0]
        logger.debug(f"Extracted phone from JID: {phone}")
    elif '@g.us' in phone:
        # This is a group ID, not an individual phone number
        logger.debug("Group ID detected in phone field - rejecting")
        return ''
    
    # Clean the phone number - remove non-digits
    cleaned_phone = ''.join(c for c in phone if c.isdigit())
    
    # Validate phone number length (typical mobile numbers are 7-15 digits)
    if len(cleaned_phone) < 7:
        logger.warning(f"Phone '{cleaned_phone}' too short ({len(cleaned_phone)} digits) - rejecting")
        return ''
    elif len(cleaned_phone) > 15:
        logger.warning(f"Phone '{cleaned_phone}' too long ({len(cleaned_phone)} digits) - rejecting")
        return ''
    
    # Format with country code (add + prefix since these include country codes)
    return f"+{cleaned_phone}"


def determine_whatsapp_direction(webhook_data: dict, business_number: str = '27720720047') -> str:
    """
    Determine message direction from WhatsApp webhook data using provider_chat_id logic
    
    The key insight: provider_chat_id represents the contact we're speaking to.
    - If sender == provider_chat_id: inbound (contact sending TO us)
    - If sender != provider_chat_id: outbound (we're sending TO the contact)
    
    Args:
        webhook_data: Raw webhook data
        business_number: Our business WhatsApp number
        
    Returns:
        'inbound' or 'outbound'
    """
    if not isinstance(webhook_data, dict):
        return 'inbound'
    
    # Check explicit direction field first
    direction_field = webhook_data.get('direction', '').lower()
    if direction_field in ['inbound', 'in', 'incoming']:
        return 'inbound'
    elif direction_field in ['outbound', 'out', 'outgoing']:
        return 'outbound'
    
    # Extract sender phone from nested sender object
    sender = webhook_data.get('sender', {})
    sender_provider_id = ''
    if isinstance(sender, dict):
        sender_provider_id = sender.get('attendee_provider_id', '')
    
    # Extract provider_chat_id (the contact we're speaking to)
    provider_chat_id = webhook_data.get('provider_chat_id', '')
    
    logger.debug(f"Direction detection: sender='{sender_provider_id}', provider_chat_id='{provider_chat_id}'")
    
    # Apply provider_chat_id logic
    if sender_provider_id and provider_chat_id:
        if sender_provider_id == provider_chat_id:
            # Sender matches the contact we're speaking to → INBOUND
            logger.debug(f"Inbound: sender matches provider_chat_id")
            return 'inbound'
        else:
            # Sender is different from the contact → OUTBOUND (we're sending to the contact)
            logger.debug(f"Outbound: sender differs from provider_chat_id")
            return 'outbound'
    
    # Fallback to business number logic if provider_chat_id logic fails
    sender_phone = sender_provider_id.replace('@s.whatsapp.net', '') if '@s.whatsapp.net' in sender_provider_id else sender_provider_id
    if sender_phone == business_number:
        logger.debug(f"Outbound: sender ({sender_phone}) is business number")
        return 'outbound'
    
    # Default to inbound if we can't determine
    logger.debug(f"Could not determine direction - defaulting to inbound")
    return 'inbound'


def extract_whatsapp_conversation_id(webhook_data: dict) -> str:
    """
    Extract conversation/thread ID from WhatsApp webhook data
    
    Args:
        webhook_data: Raw webhook data
        
    Returns:
        Conversation ID or fallback ID
    """
    if not isinstance(webhook_data, dict):
        return ''
    
    # Priority order for conversation ID fields
    conversation_fields = [
        'chat_id',           # Most reliable for WhatsApp
        'conversation_id',   # Alternative
        'thread_id',         # Generic thread ID
        'jid'               # WhatsApp JID format
    ]
    
    for field in conversation_fields:
        value = webhook_data.get(field)
        if value:
            return str(value)
    
    # Fallback: create ID from message ID
    message_id = webhook_data.get('id', webhook_data.get('message_id'))
    if message_id:
        return f"msg_{message_id}"
    
    # Last resort: use timestamp
    import time
    return f"msg_{int(time.time())}"


def extract_whatsapp_contact_name(webhook_data: dict) -> str:
    """
    Extract contact name from WhatsApp webhook data
    
    For 1-on-1 chats: Returns the name of the contact we're speaking to.
    For group chats: Returns the group subject/name.
    """
    if not isinstance(webhook_data, dict):
        return ''
    
    # Check if this is a group chat
    is_group = webhook_data.get('is_group', False)
    
    if is_group:
        # GROUP CHAT LOGIC: Use group subject as contact name
        group_subject = webhook_data.get('subject', '')
        if group_subject and group_subject.strip():
            return group_subject.strip()
        
        # Fallback for groups without subject
        attendees = webhook_data.get('attendees', [])
        member_count = len(attendees) if isinstance(attendees, list) else 0
        return f"Group Chat ({member_count} members)" if member_count > 0 else "Group Chat"
    
    # 1-ON-1 CHAT LOGIC: Use provider_chat_id to find contact
    provider_chat_id = webhook_data.get('provider_chat_id', '')
    
    # Method 1: Find name in attendees array by matching provider_id
    attendees = webhook_data.get('attendees', [])
    if attendees and isinstance(attendees, list):
        for attendee in attendees:
            if isinstance(attendee, dict):
                attendee_provider_id = attendee.get('attendee_provider_id', '')
                if attendee_provider_id == provider_chat_id:
                    attendee_name = attendee.get('attendee_name')
                    if attendee_name and attendee_name != attendee_provider_id:
                        # Only return name if it's not just the phone number/JID
                        return str(attendee_name).strip()
    
    # Method 2: Check if sender matches provider_chat_id (inbound case)
    sender = webhook_data.get('sender', {})
    if isinstance(sender, dict):
        sender_provider_id = sender.get('attendee_provider_id', '')
        if sender_provider_id == provider_chat_id:
            attendee_name = sender.get('attendee_name')
            if attendee_name and attendee_name != sender_provider_id:
                # Only return name if it's not just the phone number/JID
                return str(attendee_name).strip()
    
    # Method 3: Fallback - use first attendee if we have one
    if attendees and isinstance(attendees, list) and len(attendees) > 0:
        first_attendee = attendees[0]
        if isinstance(first_attendee, dict):
            attendee_name = first_attendee.get('attendee_name')
            if attendee_name and attendee_name != first_attendee.get('attendee_provider_id'):
                return str(attendee_name).strip()
    
    # Fallback to other possible name fields
    name_fields = [
        'sender_name',
        'contact_name', 
        'attendee_name',
        'name'
    ]
    
    for field in name_fields:
        name = webhook_data.get(field)
        if name and isinstance(name, str) and name.strip():
            # Don't return phone numbers as names
            if not ('@s.whatsapp.net' in name or name.isdigit()):
                return name.strip()
    
    return ''


def get_display_name_or_phone(contact_name: str, phone_number: str) -> str:
    """
    Get display name for contact, fallback to formatted phone number
    
    Args:
        contact_name: Contact name (may be empty)
        phone_number: Phone number (should not be empty)
        
    Returns:
        Contact name if available, otherwise formatted phone number
    """
    if contact_name and contact_name.strip():
        return contact_name.strip()
    
    if phone_number:
        # Format phone number nicely (+27 84 997 7040)
        clean_phone = phone_number.strip()
        if len(clean_phone) >= 10:
            # Assume international format with country code
            if clean_phone.startswith('27') and len(clean_phone) == 11:
                # South African number: 27849977040 → +27 84 997 7040
                return f"+{clean_phone[:2]} {clean_phone[2:4]} {clean_phone[4:7]} {clean_phone[7:]}"
            elif len(clean_phone) >= 10:
                # Generic international: add + and space after country code (assume 2-3 digits)
                if len(clean_phone) >= 11:
                    return f"+{clean_phone[:2]} {clean_phone[2:]}"
                else:
                    return f"+{clean_phone[:1]} {clean_phone[1:]}"
        
        return f"+{clean_phone}"  # Fallback: just add +
    
    return "Unknown Contact"


def extract_whatsapp_message_sender(webhook_data: dict) -> dict:
    """
    Extract message sender information for both 1-on-1 and group chats
    
    Returns:
        Dict with sender info: {
            'name': str,
            'phone': str,  # Only for 1-on-1 chats
            'provider_id': str,
            'is_group_message': bool,
            'group_subject': str  # Only for group messages
        }
    """
    if not isinstance(webhook_data, dict):
        return {
            'name': 'Unknown Sender',
            'phone': '',
            'provider_id': '',
            'is_group_message': False,
            'group_subject': ''
        }
    
    is_group = webhook_data.get('is_group', False)
    sender = webhook_data.get('sender', {})
    
    # Extract sender details
    sender_name = 'Unknown Sender'
    sender_phone = ''
    sender_provider_id = ''
    
    if isinstance(sender, dict):
        sender_name = sender.get('attendee_name', 'Unknown Sender')
        sender_provider_id = sender.get('attendee_provider_id', '')
        
        # Extract phone from provider ID for 1-on-1 chats
        if not is_group and sender_provider_id and '@s.whatsapp.net' in sender_provider_id:
            phone_part = sender_provider_id.split('@s.whatsapp.net')[0]
            cleaned_phone = ''.join(c for c in phone_part if c.isdigit())
            if len(cleaned_phone) >= 7:
                sender_phone = f"+{cleaned_phone}"
    
    result = {
        'name': sender_name,
        'phone': sender_phone,
        'provider_id': sender_provider_id,
        'is_group_message': is_group,
        'group_subject': webhook_data.get('subject', '') if is_group else ''
    }
    
    return result