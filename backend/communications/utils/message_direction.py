"""
Unified message direction logic for WhatsApp and other messaging channels
"""
import logging
from typing import Dict, Any
from .account_owner_detection import AccountOwnerDetector

logger = logging.getLogger(__name__)


def determine_whatsapp_direction(message_data: Dict[str, Any], business_account_id: str = None, channel: Any = None) -> str:
    """
    Single source of truth for determining WhatsApp message direction
    
    Args:
        message_data: Raw message data from UniPile
        business_account_id: Optional business account ID for comparison
        channel: Optional Channel instance for automatic account detection
        
    Returns:
        'in' for inbound (from customer), 'out' for outbound (from business)
    """
    # Method 1: Use is_sender field if available (most reliable)
    if 'is_sender' in message_data:
        is_sender = message_data.get('is_sender', 0)
        return 'out' if is_sender else 'in'
    
    # Method 2: Use AccountOwnerDetector for sender analysis
    if business_account_id or channel:
        detector = AccountOwnerDetector('whatsapp', account_identifier=business_account_id, channel=channel)
        sender_info = message_data.get('sender', {})
        
        if isinstance(sender_info, dict) and sender_info:  # Check sender_info is not empty
            logger.debug(f"WhatsApp direction detection - Sender: {sender_info}, Account ID: {business_account_id}")
            is_owner = detector.is_account_owner(sender_info, message_data)
            logger.debug(f"WhatsApp direction detection - Is owner: {is_owner}")
            if is_owner:
                return 'out'
            elif sender_info.get('attendee_provider_id') or sender_info.get('id'):
                # Has sender info but not owner
                return 'in'
    
    # Method 3: Check message direction field directly
    direction = message_data.get('direction', '').lower()
    if direction in ['in', 'inbound', 'received']:
        return 'in'
    elif direction in ['out', 'outbound', 'sent']:
        return 'out'
    
    # Method 4: Check message type/source indicators
    message_type = message_data.get('type', '').lower()
    if message_type in ['received', 'incoming']:
        return 'in'
    elif message_type in ['sent', 'outgoing']:
        return 'out'
    
    # Default fallback: assume inbound if uncertain (safer for notifications)
    logger.warning(f"Unable to determine message direction for data: {list(message_data.keys())}")
    return 'in'


def determine_email_direction(message_data: Dict[str, Any], user_email: str = None) -> str:
    """
    Determine email message direction
    
    Args:
        message_data: Raw email data from UniPile
        user_email: User's email address for comparison
        
    Returns:
        'in' for received emails, 'out' for sent emails
    """
    # Check sender vs user email
    if user_email:
        sender_email = message_data.get('from', {}).get('email', '') if isinstance(message_data.get('from'), dict) else message_data.get('from', '')
        if sender_email.lower() == user_email.lower():
            return 'out'
        elif sender_email:  # Has sender but not user
            return 'in'
    
    # Check email direction field
    direction = message_data.get('direction', '').lower()
    if direction in ['in', 'inbound', 'received']:
        return 'in'
    elif direction in ['out', 'outbound', 'sent']:
        return 'out'
    
    # Check folder indicators
    folder = message_data.get('folder', '').lower()
    if folder in ['sent', 'outbox']:
        return 'out'
    elif folder in ['inbox', 'received']:
        return 'in'
    
    # Default to inbound
    return 'in'


def determine_linkedin_direction(message_data: Dict[str, Any], user_profile_id: str = None) -> str:
    """
    Determine LinkedIn message direction
    
    Args:
        message_data: Raw LinkedIn message data from UniPile
        user_profile_id: User's LinkedIn profile ID for comparison
        
    Returns:
        'in' for received messages, 'out' for sent messages
    """
    # Check sender vs user profile
    if user_profile_id:
        sender_id = message_data.get('sender', {}).get('profile_id', '') if isinstance(message_data.get('sender'), dict) else ''
        if sender_id == user_profile_id:
            return 'out'
        elif sender_id:
            return 'in'
    
    # Use is_sender field
    if 'is_sender' in message_data:
        return 'out' if message_data['is_sender'] else 'in'
    
    # Check direction field
    direction = message_data.get('direction', '').lower()
    if direction in ['in', 'inbound', 'received']:
        return 'in'
    elif direction in ['out', 'outbound', 'sent']:
        return 'out'
    
    # Default to inbound
    return 'in'


def determine_message_direction(message_data: Dict[str, Any], channel_type: str, user_identifier: str = None, channel: Any = None) -> str:
    """
    Universal message direction determiner for all channel types
    
    Args:
        message_data: Raw message data from UniPile
        channel_type: Type of channel ('whatsapp', 'gmail', 'linkedin', etc.)
        user_identifier: User's identifier for the channel (email, phone, profile_id, etc.)
        channel: Optional Channel instance for automatic account detection
        
    Returns:
        'in' for inbound messages, 'out' for outbound messages
    """
    channel_type = channel_type.lower()
    
    if channel_type == 'whatsapp':
        return determine_whatsapp_direction(message_data, user_identifier, channel)
    elif channel_type in ['gmail', 'outlook', 'email', 'mail']:
        return determine_email_direction(message_data, user_identifier)
    elif channel_type == 'linkedin':
        return determine_linkedin_direction(message_data, user_identifier)
    else:
        # Generic direction logic for unknown channels
        if 'is_sender' in message_data:
            return 'out' if message_data['is_sender'] else 'in'
        
        direction = message_data.get('direction', '').lower()
        if direction in ['in', 'inbound', 'received']:
            return 'in'
        elif direction in ['out', 'outbound', 'sent']:
            return 'out'
        
        # Default to inbound
        return 'in'