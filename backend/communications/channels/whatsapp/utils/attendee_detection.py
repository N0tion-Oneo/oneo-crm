"""
WhatsApp Attendee Detection (Fixed for correct model fields)
Automatically detects and manages chat participants from webhook data
"""
import logging
from typing import Dict, Any, Optional, List
from django.utils import timezone
from communications.utils.account_owner_detection import AccountOwnerDetector

logger = logging.getLogger(__name__)


class WhatsAppAttendeeDetector:
    """Detects and manages WhatsApp chat attendees from webhook and API data"""
    
    def __init__(self, channel: Optional[Any] = None, account_identifier: Optional[str] = None):
        """
        Initialize with channel or account identifier for owner detection
        
        Args:
            channel: Channel instance to extract account identifier from
            account_identifier: Business WhatsApp phone number or account ID (overrides channel)
        """
        self.channel = channel
        self.account_identifier = account_identifier
        
        # Use the AccountOwnerDetector which will handle getting the account identifier
        self.owner_detector = AccountOwnerDetector('whatsapp', account_identifier=account_identifier, channel=channel)
        
        # Get the account_identifier from the owner_detector (it handles the extraction logic)
        self.account_identifier = self.owner_detector.account_identifier
    
    def set_account_identifier(self, account_identifier: str):
        """Update the account identifier for owner detection"""
        self.account_identifier = account_identifier
        self.owner_detector = AccountOwnerDetector('whatsapp', account_identifier)
    
    def extract_attendee_from_api_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract attendee information from API message data
        
        Args:
            message_data: Message data from UniPile API
            
        Returns:
            Dictionary containing attendee information
        """
        # The extract_attendee_from_webhook method handles both webhook and API data
        # It checks for fields used by both sources
        return self.extract_attendee_from_webhook(message_data)
    
    def extract_attendee_from_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract attendee information from webhook data
        
        Args:
            webhook_data: Raw webhook payload
            
        Returns:
            Dictionary containing attendee information
        """
        attendee_info = {
            'external_id': None,
            'phone_number': None,
            'name': None,
            'is_self': False,
            'profile_picture': None,
            'status': None
        }
        
        # Extract from message data
        message_data = webhook_data.get('message', webhook_data)
        
        # Try to get sender information from various possible locations
        sender = message_data.get('sender', {})
        if sender:
            attendee_info['external_id'] = sender.get('id') or sender.get('phone')
            attendee_info['phone_number'] = self._normalize_phone(sender.get('phone') or sender.get('number'))
            attendee_info['name'] = sender.get('name') or sender.get('display_name')
            attendee_info['is_self'] = sender.get('is_self', False)
            attendee_info['profile_picture'] = sender.get('profile_picture_url')
            attendee_info['status'] = sender.get('status')
        
        # Try alternative field structures used by UniPile
        if not attendee_info['external_id']:
            # Check for 'from' field (common in WhatsApp webhooks)
            from_field = message_data.get('from')
            if from_field:
                if isinstance(from_field, dict):
                    attendee_info['external_id'] = from_field.get('id')
                    attendee_info['phone_number'] = self._normalize_phone(from_field.get('phone'))
                    attendee_info['name'] = from_field.get('name')
                else:
                    # Sometimes 'from' is just the phone number
                    attendee_info['external_id'] = from_field
                    attendee_info['phone_number'] = self._normalize_phone(from_field)
        
        # Check for sender_id and related fields
        if not attendee_info['external_id']:
            # First try sender_attendee_id (UniPile API field)
            attendee_info['external_id'] = (
                message_data.get('sender_attendee_id') or
                message_data.get('sender_id') or
                message_data.get('from_id') or
                message_data.get('attendee_id')
            )
        
        if not attendee_info['phone_number']:
            # Try to extract phone from various fields
            phone = (
                message_data.get('from_number') or
                message_data.get('sender_phone') or
                message_data.get('phone')
            )
            
            # If no phone but we have sender_id, extract from it (e.g., "27836851686@s.whatsapp.net")
            if not phone and message_data.get('sender_id'):
                sender_id = message_data.get('sender_id')
                if '@' in sender_id:
                    phone = sender_id.split('@')[0]
                else:
                    phone = sender_id
            
            attendee_info['phone_number'] = self._normalize_phone(phone)
        
        if not attendee_info['name']:
            # First try direct name fields
            attendee_info['name'] = (
                message_data.get('sender_name') or
                message_data.get('from_name') or
                message_data.get('attendee_name')
            )
            
            # If still no name, try to extract pushName from original data
            if not attendee_info['name'] and message_data.get('original'):
                try:
                    import json
                    original_data = json.loads(message_data['original'])
                    attendee_info['name'] = original_data.get('pushName')
                except (json.JSONDecodeError, TypeError):
                    pass
        
        # Check if it's from the account owner
        # First check the is_sender field from API (most reliable)
        if message_data.get('is_sender'):
            attendee_info['is_self'] = True
        # Then use the centralized detector
        elif self.owner_detector:
            attendee_info['is_self'] = self.owner_detector.is_account_owner(
                attendee_info, 
                webhook_data
            )
        else:
            # Fallback to old logic if no detector configured
            account_info = webhook_data.get('account', {})
            if account_info:
                account_phone = self._normalize_phone(account_info.get('phone'))
                if account_phone and attendee_info['phone_number'] == account_phone:
                    attendee_info['is_self'] = True
        
        # Generate name if not available
        if not attendee_info['name'] and attendee_info['phone_number']:
            attendee_info['name'] = f"WhatsApp User {attendee_info['phone_number']}"
        
        return attendee_info
    
    def extract_chat_attendees(self, chat_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract all attendees from chat data (API or webhook)
        
        Args:
            chat_data: Chat data from API or webhook
            
        Returns:
            List of attendee dictionaries
        """
        attendees = []
        seen_ids = set()
        
        # Extract from participants list (group chats)
        participants = chat_data.get('participants', [])
        for participant in participants:
            attendee = {
                'external_id': participant.get('id') or participant.get('phone'),
                'phone_number': self._normalize_phone(participant.get('phone') or participant.get('number')),
                'name': participant.get('name') or participant.get('display_name'),
                'is_self': participant.get('is_self', False),  # May be provided by API
                'profile_picture': participant.get('profile_picture_url'),
                'role': participant.get('role', 'member'),  # admin, member
                'status': participant.get('status'),
                'joined_at': participant.get('joined_at')
            }
            
            # Use owner detector to verify/correct is_self flag
            if self.owner_detector and not attendee['is_self']:
                attendee['is_self'] = self.owner_detector.is_account_owner(attendee)
            
            if attendee['external_id'] and attendee['external_id'] not in seen_ids:
                seen_ids.add(attendee['external_id'])
                attendees.append(attendee)
        
        # Extract from attendees list (alternative format)
        attendee_list = chat_data.get('attendees', [])
        for att in attendee_list:
            attendee = {
                'external_id': att.get('id') or att.get('attendee_id'),
                'phone_number': self._normalize_phone(att.get('phone')),
                'name': att.get('name'),
                'is_self': att.get('is_self', False),
                'profile_picture': att.get('profile_picture_url'),
                'role': att.get('role', 'member'),
                'status': att.get('status'),
                'joined_at': att.get('joined_at')
            }
            
            # Use owner detector to verify/correct is_self flag
            if self.owner_detector and not attendee['is_self']:
                attendee['is_self'] = self.owner_detector.is_account_owner(attendee)
            
            if attendee['external_id'] and attendee['external_id'] not in seen_ids:
                seen_ids.add(attendee['external_id'])
                attendees.append(attendee)
        
        # If no participants found, extract from chat metadata
        if not attendees:
            # For 1-1 chats, extract from chat name/recipient
            recipient = chat_data.get('recipient', {})
            if recipient:
                attendee = {
                    'external_id': recipient.get('id') or recipient.get('phone'),
                    'phone_number': self._normalize_phone(recipient.get('phone')),
                    'name': recipient.get('name') or chat_data.get('name'),
                    'is_self': False,  # Recipients are typically not the account owner
                    'profile_picture': recipient.get('profile_picture_url'),
                    'role': 'member',
                    'status': recipient.get('status')
                }
                
                # Use owner detector to verify is_self flag
                if self.owner_detector:
                    attendee['is_self'] = self.owner_detector.is_account_owner(attendee)
                
                if attendee['external_id']:
                    attendees.append(attendee)
            
            # Also check for attendee_provider_id (UniPile format for 1-1 chats)
            elif chat_data.get('attendee_provider_id'):
                provider_id = chat_data['attendee_provider_id']
                # Extract phone number from provider_id (format: 27825292776@s.whatsapp.net)
                phone = provider_id.split('@')[0] if '@' in provider_id else provider_id
                
                attendee = {
                    'external_id': provider_id,
                    'phone_number': self._normalize_phone(phone),
                    'name': chat_data.get('attendee_name') or chat_data.get('name') or f'WhatsApp User {phone[-4:]}',
                    'is_self': False,  # attendee_provider_id is the other party
                    'profile_picture': None,
                    'role': 'member',
                    'status': 'active'
                }
                
                # Use owner detector to verify is_self flag
                if self.owner_detector:
                    attendee['is_self'] = self.owner_detector.is_account_owner(attendee)
                
                attendees.append(attendee)
        
        return attendees
    
    def create_or_update_attendee(
        self, 
        attendee_info: Dict[str, Any], 
        conversation: Optional[Any] = None,
        channel: Optional[Any] = None
    ) -> Optional[Any]:
        """
        Create or update a ChatAttendee record and link to conversation if provided
        
        Args:
            attendee_info: Dictionary with attendee information
            conversation: Optional Conversation instance to link
            channel: Channel instance (required)
            
        Returns:
            ChatAttendee instance or None
        """
        from communications.models import ChatAttendee, ConversationAttendee
        
        # Handle UniPile API format where 'id' is the external ID
        external_id = attendee_info.get('external_id') or attendee_info.get('id')
        
        if not external_id:
            logger.warning(f"Cannot create attendee without external_id: {attendee_info}")
            return None
        
        if not channel:
            logger.error("Channel is required to create/update attendee")
            return None
        
        try:
            # Build provider_id from phone or external_id
            provider_id = attendee_info.get('provider_id') or attendee_info.get('phone_number') or external_id
            if attendee_info.get('phone_number') and '@' not in provider_id:
                # For WhatsApp, provider_id is often in format phone@s.whatsapp.net
                provider_id = f"{attendee_info['phone_number']}@s.whatsapp.net"
            
            # Ensure picture_url is never None (it's required field)
            picture_url = attendee_info.get('profile_picture', '') or attendee_info.get('picture_url', '') or ''
            
            # Check if this attendee is the account owner
            is_self = attendee_info.get('is_self', False)
            if not is_self and self.owner_detector:
                # Double-check with the owner detector
                is_self = self.owner_detector.is_account_owner(attendee_info)
            
            attendee, created = ChatAttendee.objects.update_or_create(
                external_attendee_id=external_id,
                channel=channel,
                defaults={
                    'provider_id': provider_id,
                    'name': attendee_info.get('name', 'Unknown'),
                    'picture_url': picture_url,  # Ensure it's never None
                    'is_self': is_self,
                    'metadata': {
                        'phone_number': attendee_info.get('phone_number'),
                        'role': attendee_info.get('role', 'member'),
                        'status': attendee_info.get('status'),
                        'joined_at': attendee_info.get('joined_at'),
                        'last_seen': timezone.now().isoformat()
                    }
                }
            )
            
            if created:
                logger.info(f"✅ Created WhatsApp attendee: {attendee.name} ({external_id}) - is_self={is_self}")
            else:
                # Update last seen and any changed info
                updated = False
                
                if attendee_info.get('name') and attendee_info['name'] != attendee.name:
                    attendee.name = attendee_info['name']
                    updated = True
                
                if attendee_info.get('profile_picture') and attendee_info['profile_picture'] != attendee.picture_url:
                    attendee.picture_url = attendee_info['profile_picture']
                    updated = True
                
                # IMPORTANT: Update is_self flag if it's different
                # This is crucial for properly identifying the account owner
                if is_self != attendee.is_self:
                    attendee.is_self = is_self
                    updated = True
                    logger.info(f"📝 Updated is_self flag for {attendee.name}: {attendee.is_self}")
                
                # Update metadata
                if not attendee.metadata:
                    attendee.metadata = {}
                
                attendee.metadata['last_seen'] = timezone.now().isoformat()
                
                if attendee_info.get('phone_number'):
                    attendee.metadata['phone_number'] = attendee_info['phone_number']
                
                if attendee_info.get('status'):
                    attendee.metadata['status'] = attendee_info['status']
                
                if updated or attendee.metadata:
                    attendee.save()
                    logger.debug(f"📝 Updated WhatsApp attendee: {attendee.name}")
            
            # Link attendee to conversation if provided
            if conversation and attendee:
                try:
                    conv_attendee, created = ConversationAttendee.objects.get_or_create(
                        conversation=conversation,
                        attendee=attendee,
                        defaults={
                            'role': attendee_info.get('role', 'member'),
                            'is_active': True,
                            'metadata': {
                                'joined_via': 'whatsapp',
                                'original_role': attendee_info.get('role', 'member')
                            }
                        }
                    )
                    if created:
                        logger.info(f"🔗 Linked attendee {attendee.name} to conversation {conversation.id}")
                        # Update participant count
                        conversation.participant_count = conversation.conversation_attendees.filter(is_active=True).count()
                        conversation.save(update_fields=['participant_count'])
                except Exception as e:
                    logger.error(f"Failed to link attendee to conversation: {e}")
            
            return attendee
            
        except Exception as e:
            logger.error(f"Failed to create/update WhatsApp attendee: {e}")
            return None
    
    def process_chat_attendees(
        self, 
        chat_data: Dict[str, Any], 
        conversation: Optional[Any] = None,
        channel: Any = None
    ) -> List[Any]:
        """
        Process all attendees from chat data
        
        Args:
            chat_data: Chat data from API or webhook
            conversation: Optional Conversation instance
            channel: Channel instance (required)
            
        Returns:
            List of ChatAttendee instances
        """
        if not channel:
            logger.error("Channel is required to process attendees")
            return []
        
        attendees = self.extract_chat_attendees(chat_data)
        processed_attendees = []
        
        for attendee_info in attendees:
            attendee = self.create_or_update_attendee(
                attendee_info, 
                conversation=conversation,
                channel=channel
            )
            if attendee:
                processed_attendees.append(attendee)
        
        logger.info(f"Processed {len(processed_attendees)} WhatsApp attendees")
        return processed_attendees
    
    def link_message_to_attendee(
        self, 
        message, 
        webhook_data: Dict[str, Any], 
        conversation: Optional[Any] = None,
        channel: Any = None
    ):
        """
        Link a message to its sender attendee
        
        Args:
            message: Message instance
            webhook_data: Raw webhook data
            conversation: Optional Conversation instance
            channel: Channel instance (required)
        """
        if not channel:
            logger.error("Channel is required to link message to attendee")
            return
        
        sender_info = self.extract_attendee_from_webhook(webhook_data)
        if sender_info.get('external_id'):
            attendee = self.create_or_update_attendee(
                sender_info, 
                conversation=conversation,
                channel=channel
            )
            if attendee and message:
                # Set the sender field on the message
                message.sender = attendee
                
                # Also store attendee reference in message metadata for backwards compatibility
                if not message.metadata:
                    message.metadata = {}
                message.metadata['attendee_id'] = str(attendee.id)
                message.metadata['attendee_name'] = attendee.name
                message.metadata['attendee_phone'] = attendee.metadata.get('phone_number') if attendee.metadata else None
                
                # Save with both sender and metadata
                message.save(update_fields=['sender', 'metadata'])
                logger.debug(f"🔗 Linked message {message.id} to attendee {attendee.name} as sender")
    
    def _normalize_phone(self, phone: Optional[str]) -> Optional[str]:
        """
        Normalize phone number format
        
        Args:
            phone: Phone number in various formats
            
        Returns:
            Normalized phone number or None
        """
        if not phone:
            return None
        
        # Remove all non-numeric characters except +
        import re
        cleaned = re.sub(r'[^\d+]', '', str(phone))
        
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