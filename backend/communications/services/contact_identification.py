"""
Enhanced contact identification service using stored account data
"""
import logging
from typing import Dict, Any, Optional, Tuple
from communications.models import UserChannelConnection

logger = logging.getLogger(__name__)


class ContactIdentificationService:
    """
    Service for identifying contacts and extracting phone numbers using comprehensive account data
    """
    
    def identify_whatsapp_contact(self, connection: UserChannelConnection, 
                                message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Identify WhatsApp contact using stored account data and message context
        
        Args:
            connection: UserChannelConnection with stored account data
            message_data: Raw message data from UniPile webhook
            
        Returns:
            Dict with contact identification details
        """
        identification = {
            'contact_phone': None,
            'contact_name': None,
            'business_phone': None,
            'is_group_chat': False,
            'group_subject': None,
            'identification_method': None,
            'confidence': 'high'
        }
        
        try:
            # Get business phone from stored account data
            business_phone = connection.connection_config.get('phone_number')
            if business_phone:
                identification['business_phone'] = f"+{business_phone}"
                logger.debug(f"Business phone from account data: +{business_phone}")
            
            # Check if this is a group chat
            is_group = message_data.get('is_group', False)
            identification['is_group_chat'] = is_group
            
            if is_group:
                return self._identify_group_chat_contact(message_data, identification)
            else:
                return self._identify_individual_contact(message_data, identification, business_phone)
                
        except Exception as e:
            logger.error(f"Error identifying WhatsApp contact: {e}")
            identification['identification_method'] = 'error_fallback'
            identification['confidence'] = 'low'
            return identification
    
    def _identify_group_chat_contact(self, message_data: Dict[str, Any], 
                                   identification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Identify contact details for group chat messages
        """
        identification['identification_method'] = 'group_chat'
        
        # Get group subject/name
        group_subject = message_data.get('subject', '')
        if group_subject and group_subject.strip():
            identification['group_subject'] = group_subject.strip()
            identification['contact_name'] = group_subject.strip()
        else:
            # Fallback group naming
            attendees = message_data.get('attendees', [])
            member_count = len(attendees) if isinstance(attendees, list) else 0
            group_name = f"Group Chat ({member_count} members)" if member_count > 0 else "Group Chat"
            identification['group_subject'] = group_name
            identification['contact_name'] = group_name
        
        # For group messages, we don't extract individual phone numbers
        # Groups use group IDs like "27720720045-1419774108@g.us"
        identification['contact_phone'] = None
        
        logger.debug(f"Identified group chat: {identification['contact_name']}")
        return identification
    
    def _identify_individual_contact(self, message_data: Dict[str, Any], 
                                   identification: Dict[str, Any], 
                                   business_phone: str = None) -> Dict[str, Any]:
        """
        Identify contact details for 1-on-1 chat messages
        """
        # Method 1: Use provider_chat_id (most reliable for 1-on-1 chats)
        provider_chat_id = message_data.get('provider_chat_id', '')
        if provider_chat_id:
            contact_phone = self._extract_phone_from_jid(provider_chat_id)
            if contact_phone and contact_phone != business_phone:
                identification['contact_phone'] = contact_phone
                identification['identification_method'] = 'provider_chat_id'
                
                # Find contact name by matching provider_chat_id in attendees
                contact_name = self._find_contact_name_by_phone(message_data, provider_chat_id)
                if contact_name:
                    identification['contact_name'] = contact_name
                
                logger.debug(f"Identified contact via provider_chat_id: {contact_phone}")
                return identification
        
        # Method 2: Extract from sender information
        sender_info = message_data.get('sender', {})
        if isinstance(sender_info, dict):
            sender_provider_id = sender_info.get('attendee_provider_id', '')
            sender_name = sender_info.get('attendee_name', '')
            
            if sender_provider_id:
                sender_phone = self._extract_phone_from_jid(sender_provider_id)
                
                # If sender is not the business phone, it's the contact
                if sender_phone and sender_phone != business_phone:
                    identification['contact_phone'] = sender_phone
                    identification['identification_method'] = 'sender_info'
                    
                    if sender_name and sender_name != sender_provider_id:
                        identification['contact_name'] = sender_name
                    
                    logger.debug(f"Identified contact via sender: {sender_phone}")
                    return identification
        
        # Method 3: Fallback to attendees array
        attendees = message_data.get('attendees', [])
        if attendees and isinstance(attendees, list):
            for attendee in attendees:
                if isinstance(attendee, dict):
                    attendee_provider_id = attendee.get('attendee_provider_id', '')
                    attendee_name = attendee.get('attendee_name', '')
                    
                    if attendee_provider_id:
                        attendee_phone = self._extract_phone_from_jid(attendee_provider_id)
                        
                        # Skip if this is the business phone
                        if attendee_phone and attendee_phone != business_phone:
                            identification['contact_phone'] = attendee_phone
                            identification['identification_method'] = 'attendees_array'
                            
                            if attendee_name and attendee_name != attendee_provider_id:
                                identification['contact_name'] = attendee_name
                            
                            logger.debug(f"Identified contact via attendees: {attendee_phone}")
                            return identification
        
        # Method 4: Legacy fallback methods
        identification = self._legacy_phone_extraction(message_data, identification, business_phone)
        
        return identification
    
    def _extract_phone_from_jid(self, jid: str) -> Optional[str]:
        """
        Extract phone number from WhatsApp JID format
        
        Args:
            jid: WhatsApp JID like "27720720047@s.whatsapp.net" or plain phone number
            
        Returns:
            Formatted phone number with + prefix or None
        """
        if not jid:
            return None
        
        # Handle WhatsApp JID format: phone@s.whatsapp.net
        if '@s.whatsapp.net' in jid:
            phone = jid.split('@s.whatsapp.net')[0]
        elif '@g.us' in jid:
            # This is a group ID, not an individual phone number
            return None
        else:
            phone = jid
        
        # Clean the phone number - remove non-digits
        cleaned_phone = ''.join(c for c in phone if c.isdigit())
        
        # Validate phone number length (typical mobile numbers are 7-15 digits)
        if len(cleaned_phone) < 7 or len(cleaned_phone) > 15:
            return None
        
        # Format with + prefix (these should include country codes)
        return f"+{cleaned_phone}"
    
    def _find_contact_name_by_phone(self, message_data: Dict[str, Any], target_provider_id: str) -> Optional[str]:
        """
        Find contact name by matching provider ID in attendees
        """
        attendees = message_data.get('attendees', [])
        if not attendees or not isinstance(attendees, list):
            return None
        
        for attendee in attendees:
            if isinstance(attendee, dict):
                attendee_provider_id = attendee.get('attendee_provider_id', '')
                if attendee_provider_id == target_provider_id:
                    attendee_name = attendee.get('attendee_name', '')
                    if attendee_name and attendee_name != attendee_provider_id:
                        # Only return name if it's not just the phone number/JID
                        return attendee_name.strip()
        
        return None
    
    def _legacy_phone_extraction(self, message_data: Dict[str, Any], 
                                identification: Dict[str, Any], 
                                business_phone: str = None) -> Dict[str, Any]:
        """
        Legacy fallback phone extraction methods
        """
        identification['identification_method'] = 'legacy_fallback'
        identification['confidence'] = 'medium'
        
        # Try other common phone fields
        phone_fields = [
            'from',               # Generic sender JID
            'phone',              # Direct phone field
            'contact_phone',      # Contact info
            'to',                 # For outbound messages
            'recipient'           # Alternative recipient
        ]
        
        for field in phone_fields:
            value = message_data.get(field, '')
            if value:
                phone = self._extract_phone_from_jid(str(value))
                if phone and phone != business_phone:
                    identification['contact_phone'] = phone
                    logger.debug(f"Legacy: found phone in field '{field}': {phone}")
                    break
        
        # Try to extract name from various fields
        if not identification.get('contact_name'):
            name_fields = ['sender_name', 'contact_name', 'attendee_name', 'name']
            for field in name_fields:
                name = message_data.get(field)
                if name and isinstance(name, str) and name.strip():
                    # Don't return phone numbers as names
                    if not ('@s.whatsapp.net' in name or name.isdigit()):
                        identification['contact_name'] = name.strip()
                        break
        
        return identification
    
    def get_formatted_contact_display(self, identification: Dict[str, Any]) -> str:
        """
        Get formatted display name for contact identification
        
        Args:
            identification: Result from identify_whatsapp_contact()
            
        Returns:
            Formatted display name
        """
        contact_name = identification.get('contact_name', '')
        contact_phone = identification.get('contact_phone', '')
        is_group = identification.get('is_group_chat', False)
        
        if is_group:
            group_subject = identification.get('group_subject', '')
            return group_subject or 'Group Chat'
        
        if contact_name and contact_name.strip():
            return contact_name.strip()
        
        if contact_phone:
            # Format phone number nicely
            return self._format_phone_display(contact_phone)
        
        return "Unknown Contact"
    
    def _format_phone_display(self, phone_number: str) -> str:
        """
        Format phone number for display
        
        Args:
            phone_number: Phone number like "+27720720047"
            
        Returns:
            Formatted phone like "+27 72 072 0047"
        """
        if not phone_number:
            return "Unknown Contact"
        
        # Remove + for processing
        clean_phone = phone_number.replace('+', '').strip()
        
        if len(clean_phone) >= 10:
            # Assume international format with country code
            if clean_phone.startswith('27') and len(clean_phone) == 11:
                # South African number: 27720720047 → +27 72 072 0047
                return f"+{clean_phone[:2]} {clean_phone[2:4]} {clean_phone[4:7]} {clean_phone[7:]}"
            elif clean_phone.startswith('1') and len(clean_phone) == 11:
                # US/Canada number: 15551234567 → +1 555 123 4567
                return f"+{clean_phone[:1]} {clean_phone[1:4]} {clean_phone[4:7]} {clean_phone[7:]}"
            elif len(clean_phone) >= 11:
                # Generic international: assume 2-3 digit country code
                return f"+{clean_phone[:2]} {clean_phone[2:]}"
            else:
                # Shorter numbers: assume 1 digit country code
                return f"+{clean_phone[:1]} {clean_phone[1:]}"
        
        return f"+{clean_phone}"  # Fallback: just add +
    
    def get_identification_summary(self, connection: UserChannelConnection) -> Dict[str, Any]:
        """
        Get summary of contact identification capabilities for this connection
        """
        summary = {
            'connection_id': str(connection.id),
            'channel_type': connection.channel_type,
            'business_phone': None,
            'identification_methods': []
        }
        
        if connection.channel_type == 'whatsapp':
            business_phone = connection.connection_config.get('phone_number')
            if business_phone:
                summary['business_phone'] = f"+{business_phone}"
                summary['identification_methods'].extend([
                    'provider_chat_id_matching',
                    'sender_provider_id_comparison',
                    'attendees_array_filtering',
                    'business_phone_exclusion'
                ])
        
        summary['identification_methods'].extend([
            'group_chat_detection',
            'contact_name_extraction',
            'legacy_fallback_methods'
        ])
        
        return summary


# Global service instance
contact_identification_service = ContactIdentificationService()