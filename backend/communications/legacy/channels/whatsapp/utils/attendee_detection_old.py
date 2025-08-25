"""
WhatsApp Attendee Detection
Automatically detects and manages chat participants from webhook data
"""
import logging
from typing import Dict, Any, Optional, List
from django.utils import timezone

logger = logging.getLogger(__name__)


class WhatsAppAttendeeDetector:
    """Detects and manages WhatsApp chat attendees from webhook and API data"""
    
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
            attendee_info['external_id'] = (
                message_data.get('sender_id') or
                message_data.get('from_id') or
                message_data.get('attendee_id')
            )
        
        if not attendee_info['phone_number']:
            attendee_info['phone_number'] = self._normalize_phone(
                message_data.get('from_number') or
                message_data.get('sender_phone') or
                message_data.get('phone')
            )
        
        if not attendee_info['name']:
            attendee_info['name'] = (
                message_data.get('sender_name') or
                message_data.get('from_name') or
                message_data.get('attendee_name')
            )
        
        # Check if it's from the account owner
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
                'is_self': participant.get('is_self', False),
                'profile_picture': participant.get('profile_picture_url'),
                'role': participant.get('role', 'member'),  # admin, member
                'status': participant.get('status'),
                'joined_at': participant.get('joined_at')
            }
            
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
                    'is_self': False,
                    'profile_picture': recipient.get('profile_picture_url'),
                    'role': 'member',
                    'status': recipient.get('status')
                }
                if attendee['external_id']:
                    attendees.append(attendee)
        
        return attendees
    
    def create_or_update_attendee(self, attendee_info: Dict[str, Any], chat_id: str, channel) -> Optional[Any]:
        """
        Create or update a ChatAttendee record
        
        Args:
            attendee_info: Dictionary with attendee information
            chat_id: WhatsApp chat ID
            channel: Channel instance
            
        Returns:
            ChatAttendee instance or None
        """
        from communications.models import ChatAttendee
        
        if not attendee_info.get('external_id'):
            logger.warning(f"Cannot create attendee without external_id: {attendee_info}")
            return None
        
        try:
            attendee, created = ChatAttendee.objects.update_or_create(
                external_attendee_id=attendee_info['external_id'],
                chat_id=chat_id,
                channel=channel,
                defaults={
                    'name': attendee_info.get('name', 'Unknown'),
                    'phone_number': attendee_info.get('phone_number'),
                    'is_self': attendee_info.get('is_self', False),
                    'is_active': True,
                    'metadata': {
                        'profile_picture': attendee_info.get('profile_picture'),
                        'role': attendee_info.get('role', 'member'),
                        'status': attendee_info.get('status'),
                        'joined_at': attendee_info.get('joined_at'),
                        'last_seen': timezone.now().isoformat()
                    }
                }
            )
            
            if created:
                logger.info(f"✅ Created WhatsApp attendee: {attendee.name} ({attendee.external_attendee_id})")
            else:
                # Update last seen and any changed info
                updated = False
                
                if attendee_info.get('name') and attendee_info['name'] != attendee.name:
                    attendee.name = attendee_info['name']
                    updated = True
                
                if attendee_info.get('phone_number') and attendee_info['phone_number'] != attendee.phone_number:
                    attendee.phone_number = attendee_info['phone_number']
                    updated = True
                
                # Update metadata
                if not attendee.metadata:
                    attendee.metadata = {}
                
                attendee.metadata['last_seen'] = timezone.now().isoformat()
                
                if attendee_info.get('profile_picture'):
                    attendee.metadata['profile_picture'] = attendee_info['profile_picture']
                
                if attendee_info.get('status'):
                    attendee.metadata['status'] = attendee_info['status']
                
                if updated or attendee.metadata:
                    attendee.save()
                    logger.debug(f"📝 Updated WhatsApp attendee: {attendee.name}")
            
            return attendee
            
        except Exception as e:
            logger.error(f"Failed to create/update WhatsApp attendee: {e}")
            return None
    
    def process_chat_attendees(self, chat_data: Dict[str, Any], chat_id: str, channel) -> List[Any]:
        """
        Process all attendees from chat data
        
        Args:
            chat_data: Chat data from API or webhook
            chat_id: WhatsApp chat ID
            channel: Channel instance
            
        Returns:
            List of ChatAttendee instances
        """
        attendees = self.extract_chat_attendees(chat_data)
        processed_attendees = []
        
        for attendee_info in attendees:
            attendee = self.create_or_update_attendee(attendee_info, chat_id, channel)
            if attendee:
                processed_attendees.append(attendee)
        
        logger.info(f"Processed {len(processed_attendees)} WhatsApp attendees for chat {chat_id}")
        return processed_attendees
    
    def link_message_to_attendee(self, message, webhook_data: Dict[str, Any], chat_id: str, channel):
        """
        Link a message to its sender attendee
        
        Args:
            message: Message instance
            webhook_data: Raw webhook data
            chat_id: WhatsApp chat ID
            channel: Channel instance
        """
        sender_info = self.extract_attendee_from_webhook(webhook_data)
        if sender_info.get('external_id'):
            attendee = self.create_or_update_attendee(sender_info, chat_id, channel)
            if attendee and message:
                # Store attendee reference in message metadata
                if not message.metadata:
                    message.metadata = {}
                message.metadata['attendee_id'] = str(attendee.id)
                message.metadata['attendee_name'] = attendee.name
                message.metadata['attendee_phone'] = attendee.phone_number
                message.save(update_fields=['metadata'])
                logger.debug(f"🔗 Linked message {message.id} to attendee {attendee.name}")
    
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
        
        # Remove all non-numeric characters
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