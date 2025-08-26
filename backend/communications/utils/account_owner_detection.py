"""
Account Owner Detection Utility
Identifies if a sender/attendee is the business account owner across different channels
"""
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class AccountOwnerDetector:
    """
    Detects if a message sender or attendee is the business account owner.
    Provides consistent logic for identifying account ownership across all channels.
    """
    
    def __init__(self, channel_type: str, account_identifier: Optional[str] = None, channel: Optional[Any] = None):
        """
        Initialize the detector with channel context
        
        Args:
            channel_type: Type of channel ('whatsapp', 'gmail', 'linkedin', etc.)
            account_identifier: Business account identifier (phone, email, profile_id)
            channel: Optional Channel model instance to extract account identifier from
        """
        self.channel_type = channel_type.lower()
        self.channel = channel
        self.account_identifier = account_identifier
        
        # If no account_identifier provided but channel is, try to get it from the channel
        if not self.account_identifier and self.channel:
            self.account_identifier = self._get_account_identifier_from_channel()
        
    def is_account_owner(self, sender_data: Dict[str, Any], message_data: Dict[str, Any] = None) -> bool:
        """
        Determine if the sender is the account owner
        
        Args:
            sender_data: Sender/attendee information
            message_data: Optional full message data for additional context
            
        Returns:
            True if sender is the business account owner, False otherwise
        """
        # Method 1: Check explicit is_self/is_sender flag
        if sender_data.get('is_self'):
            return True
        if sender_data.get('is_sender'):
            return True
            
        # Method 2: Channel-specific detection
        if self.channel_type == 'whatsapp':
            return self._is_whatsapp_owner(sender_data, message_data)
        elif self.channel_type in ['gmail', 'outlook', 'email']:
            return self._is_email_owner(sender_data, message_data)
        elif self.channel_type == 'linkedin':
            return self._is_linkedin_owner(sender_data, message_data)
        else:
            return self._is_generic_owner(sender_data, message_data)
    
    def _get_account_identifier_from_channel(self) -> Optional[str]:
        """
        Extract account identifier from channel's associated connections
        
        Returns:
            Account identifier (phone, email, etc.) or None
        """
        if not self.channel:
            return None
            
        try:
            from communications.models import UserChannelConnection
            
            # Handle if channel is a string (unipile_account_id) instead of an object
            if isinstance(self.channel, str):
                unipile_account_id = self.channel
            else:
                unipile_account_id = self.channel.unipile_account_id
            
            # Find a connection for this channel
            connection = UserChannelConnection.objects.filter(
                unipile_account_id=unipile_account_id,
                channel_type=self.channel_type
            ).first()
            
            # Try to get from connection first
            config_to_check = None
            if connection and connection.connection_config:
                config_to_check = connection.connection_config
            # Fallback to channel's own config if available
            elif hasattr(self.channel, 'connection_config') and self.channel.connection_config:
                config_to_check = self.channel.connection_config
                logger.info(f"Using channel config instead of connection config")
            
            if not config_to_check:
                logger.warning(f"No config found for channel {unipile_account_id}")
                return None
            
            # Extract based on channel type
            if self.channel_type == 'whatsapp':
                # WhatsApp stores phone number in connection_config
                # Try different field names that might be used
                phone = (
                    config_to_check.get('account_phone') or
                    config_to_check.get('phone_number') or
                    config_to_check.get('account_identifier')
                )
                if phone:
                    # Normalize phone number (remove @s.whatsapp.net if present)
                    if '@' in phone:
                        phone = phone.split('@')[0]
                    logger.debug(f"Found WhatsApp account identifier: {phone}")
                    return phone
                    
            elif self.channel_type in ['gmail', 'outlook', 'email']:
                # Email channels store email address
                email = config_to_check.get('email')
                if email:
                    logger.debug(f"Found email account identifier: {email}")
                    return email
                    
            elif self.channel_type == 'linkedin':
                # LinkedIn stores profile ID
                profile_id = config_to_check.get('profile_id')
                if profile_id:
                    logger.debug(f"Found LinkedIn account identifier: {profile_id}")
                    return profile_id
            
            logger.warning(f"No account identifier found in connection config for {self.channel_type}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get account identifier from channel: {e}")
            return None
    
    def _is_whatsapp_owner(self, sender_data: Dict[str, Any], message_data: Dict[str, Any] = None) -> bool:
        """
        Check if WhatsApp sender is the business account
        
        Args:
            sender_data: Sender information with phone/id
            message_data: Optional message context
            
        Returns:
            True if sender is the business WhatsApp account
        """
        if not self.account_identifier:
            return False
            
        # Normalize phone numbers for comparison
        account_phone = self._normalize_phone(self.account_identifier)
        
        # Check various sender phone fields
        sender_phone = self._normalize_phone(
            sender_data.get('phone') or 
            sender_data.get('phone_number') or
            sender_data.get('number') or
            sender_data.get('attendee_provider_id', '')
        )
        
        if account_phone and sender_phone:
            if account_phone == sender_phone:
                logger.debug(f"WhatsApp owner detected: {sender_phone} matches account {account_phone}")
                return True
                
        # Check sender ID against account ID
        sender_id = sender_data.get('id') or sender_data.get('external_id')
        if sender_id and sender_id == self.account_identifier:
            logger.debug(f"WhatsApp owner detected by ID: {sender_id}")
            return True
            
        # Check if message has account context
        if message_data:
            account_info = message_data.get('account', {})
            if account_info:
                msg_account_phone = self._normalize_phone(account_info.get('phone'))
                if msg_account_phone and sender_phone and msg_account_phone == sender_phone:
                    return True
                    
        return False
    
    def _is_email_owner(self, sender_data: Dict[str, Any], message_data: Dict[str, Any] = None) -> bool:
        """
        Check if email sender is the account owner
        
        Args:
            sender_data: Sender information with email
            message_data: Optional message context
            
        Returns:
            True if sender is the email account owner
        """
        if not self.account_identifier:
            return False
            
        account_email = self.account_identifier.lower()
        
        # Check sender email
        sender_email = (
            sender_data.get('email', '') or
            sender_data.get('email_address', '') or
            sender_data.get('from', '')
        ).lower()
        
        if sender_email and sender_email == account_email:
            logger.debug(f"Email owner detected: {sender_email}")
            return True
            
        return False
    
    def _is_linkedin_owner(self, sender_data: Dict[str, Any], message_data: Dict[str, Any] = None) -> bool:
        """
        Check if LinkedIn sender is the account owner
        
        Args:
            sender_data: Sender information with profile ID
            message_data: Optional message context
            
        Returns:
            True if sender is the LinkedIn account owner
        """
        if not self.account_identifier:
            return False
            
        # Check profile ID
        sender_profile = (
            sender_data.get('profile_id') or
            sender_data.get('linkedin_id') or
            sender_data.get('id', '')
        )
        
        if sender_profile and sender_profile == self.account_identifier:
            logger.debug(f"LinkedIn owner detected: {sender_profile}")
            return True
            
        return False
    
    def _is_generic_owner(self, sender_data: Dict[str, Any], message_data: Dict[str, Any] = None) -> bool:
        """
        Generic owner detection for unknown channels
        
        Args:
            sender_data: Sender information
            message_data: Optional message context
            
        Returns:
            True if sender appears to be the account owner
        """
        # Check explicit flags
        if sender_data.get('is_account_owner'):
            return True
        if sender_data.get('is_business_account'):
            return True
            
        # Check ID match
        if self.account_identifier:
            sender_id = sender_data.get('id') or sender_data.get('external_id')
            if sender_id and sender_id == self.account_identifier:
                return True
                
        return False
    
    def _normalize_phone(self, phone: Optional[str]) -> Optional[str]:
        """
        Normalize phone number for comparison
        
        Args:
            phone: Phone number in various formats
            
        Returns:
            Normalized phone number or None
        """
        if not phone:
            return None
            
        import re
        # Remove all non-numeric characters except +
        cleaned = re.sub(r'[^\d+]', '', str(phone))
        
        # Remove @s.whatsapp.net or similar suffixes
        if '@' in str(phone):
            cleaned = str(phone).split('@')[0]
            cleaned = re.sub(r'[^\d+]', '', cleaned)
        
        # Ensure it starts with + for international format
        if cleaned and not cleaned.startswith('+'):
            # Assume US number if no country code
            if len(cleaned) == 10:
                cleaned = f"+1{cleaned}"
            elif not cleaned.startswith('1') and len(cleaned) == 11:
                cleaned = f"+{cleaned}"
            else:
                cleaned = f"+{cleaned}"
        
        return cleaned if cleaned else None
    
    def extract_account_identifier(self, connection_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract the account identifier from connection/channel data
        
        Args:
            connection_data: UserChannelConnection or Channel data
            
        Returns:
            Account identifier appropriate for the channel type
        """
        if self.channel_type == 'whatsapp':
            # Try various fields for WhatsApp phone number
            phone = (
                connection_data.get('phone_number') or
                connection_data.get('phone') or
                connection_data.get('account_phone') or
                (connection_data.get('connection_config', {}) or {}).get('phone_number') or
                (connection_data.get('metadata', {}) or {}).get('phone_number')
            )
            return self._normalize_phone(phone) if phone else None
            
        elif self.channel_type in ['gmail', 'outlook', 'email']:
            # Extract email address
            return (
                connection_data.get('email') or
                connection_data.get('email_address') or
                connection_data.get('account_email') or
                (connection_data.get('connection_config', {}) or {}).get('email') or
                (connection_data.get('metadata', {}) or {}).get('email')
            )
            
        elif self.channel_type == 'linkedin':
            # Extract LinkedIn profile ID
            return (
                connection_data.get('profile_id') or
                connection_data.get('linkedin_id') or
                (connection_data.get('connection_config', {}) or {}).get('profile_id') or
                (connection_data.get('metadata', {}) or {}).get('profile_id')
            )
        else:
            # Generic: try to get any identifier
            return (
                connection_data.get('account_id') or
                connection_data.get('external_id') or
                connection_data.get('identifier')
            )
    
    def get_direction(self, sender_data: Dict[str, Any], message_data: Dict[str, Any] = None) -> str:
        """
        Determine message direction based on sender ownership
        
        Args:
            sender_data: Sender/attendee information
            message_data: Optional full message data
            
        Returns:
            'outbound' if from account owner, 'inbound' otherwise
        """
        is_owner = self.is_account_owner(sender_data, message_data)
        return 'outbound' if is_owner else 'inbound'
    
    def filter_attendees(self, attendees: list, exclude_owner: bool = True) -> list:
        """
        Filter attendees list to optionally exclude the account owner
        
        Args:
            attendees: List of attendee dictionaries
            exclude_owner: If True, removes the account owner from the list
            
        Returns:
            Filtered list of attendees
        """
        if not exclude_owner:
            return attendees
            
        filtered = []
        for attendee in attendees:
            if not self.is_account_owner(attendee):
                filtered.append(attendee)
            else:
                logger.debug(f"Filtered out account owner: {attendee.get('name', 'Unknown')}")
                
        return filtered


def get_account_identifier_from_connection(connection, channel_type: str) -> Optional[str]:
    """
    Helper function to extract account identifier from a UserChannelConnection model
    
    Args:
        connection: UserChannelConnection model instance
        channel_type: Type of channel
        
    Returns:
        Account identifier or None
    """
    detector = AccountOwnerDetector(channel_type)
    
    # Convert model to dict-like data
    connection_data = {
        'connection_config': connection.connection_config if hasattr(connection, 'connection_config') else {},
        'metadata': connection.metadata if hasattr(connection, 'metadata') else {},
        'account_name': connection.account_name if hasattr(connection, 'account_name') else None,
    }
    
    # Add any direct fields
    if hasattr(connection, 'phone_number'):
        connection_data['phone_number'] = connection.phone_number
    if hasattr(connection, 'email'):
        connection_data['email'] = connection.email
        
    return detector.extract_account_identifier(connection_data)