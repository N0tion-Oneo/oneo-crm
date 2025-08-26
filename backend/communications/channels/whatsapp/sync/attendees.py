"""
Attendee Synchronization Service
"""
import logging
from typing import Dict, Any, List, Optional
from django.utils import timezone
from communications.models import (
    Channel, ChatAttendee, Conversation, ConversationAttendee,
    AttendeeRole
)
from ..utils.attendee_detection import WhatsAppAttendeeDetector

logger = logging.getLogger(__name__)


class AttendeeSyncService:
    """Handles attendee synchronization for WhatsApp"""
    
    def __init__(self, channel: Channel, account_identifier: Optional[str] = None):
        self.channel = channel
        self.attendee_detector = WhatsAppAttendeeDetector(
            channel=channel,
            account_identifier=account_identifier
        )
    
    def find_attendee_by_provider_id(
        self,
        provider_id: str
    ) -> Optional[ChatAttendee]:
        """
        Find an existing attendee by provider ID without creating
        
        Args:
            provider_id: The provider ID to search for
            
        Returns:
            ChatAttendee instance or None if not found
        """
        try:
            return ChatAttendee.objects.filter(
                channel=self.channel,
                external_attendee_id=provider_id
            ).first()
        except Exception as e:
            logger.error(f"Failed to find attendee: {e}")
            return None
    
    def sync_attendee_from_message(
        self,
        message_data: Dict[str, Any],
        conversation: Conversation
    ) -> Optional[ChatAttendee]:
        """
        Sync an attendee from message data
        
        Args:
            message_data: Message data from API
            conversation: Conversation the message belongs to
            
        Returns:
            ChatAttendee instance or None
        """
        try:
            # Extract attendee info from API message data
            attendee_info = self.attendee_detector.extract_attendee_from_api_message(message_data)
            
            if not attendee_info.get('external_id'):
                return None
            
            # Create or update attendee
            attendee = self.create_or_update_attendee(
                attendee_info,
                conversation=conversation
            )
            
            return attendee
            
        except Exception as e:
            logger.error(f"Failed to sync attendee from message: {e}")
            return None
    
    def sync_attendees_from_chat(
        self,
        chat_data: Dict[str, Any],
        conversation: Optional[Conversation] = None
    ) -> List[ChatAttendee]:
        """
        Sync all attendees from chat data
        
        Args:
            chat_data: Chat data from API
            conversation: Optional conversation to link attendees to
            
        Returns:
            List of ChatAttendee instances
        """
        attendees = []
        
        try:
            # Extract all attendees from chat
            attendee_infos = self.attendee_detector.extract_chat_attendees(chat_data)
            
            for attendee_info in attendee_infos:
                if attendee_info.get('external_id'):
                    attendee = self.create_or_update_attendee(
                        attendee_info,
                        conversation=conversation
                    )
                    if attendee:
                        attendees.append(attendee)
            
            return attendees
            
        except Exception as e:
            logger.error(f"Failed to sync attendees from chat: {e}")
            return attendees
    
    def create_or_update_attendee(
        self,
        attendee_info: Dict[str, Any],
        conversation: Optional[Conversation] = None
    ) -> Optional[ChatAttendee]:
        """
        Create or update a chat attendee
        
        Args:
            attendee_info: Attendee information dictionary
            conversation: Optional conversation to link to
            
        Returns:
            ChatAttendee instance or None
        """
        try:
            external_id = attendee_info.get('external_id')
            if not external_id:
                return None
            
            # Prepare attendee data
            provider_id = attendee_info.get('provider_id', external_id)
            picture_url = (
                attendee_info.get('profile_picture', '') or 
                attendee_info.get('picture_url', '') or 
                ''
            )
            
            # Check if this is the account owner
            is_self = attendee_info.get('is_self', False)
            if not is_self and self.attendee_detector.owner_detector:
                is_self = self.attendee_detector.owner_detector.is_account_owner(attendee_info)
            
            # Create or update attendee
            attendee, created = ChatAttendee.objects.update_or_create(
                external_attendee_id=external_id,
                channel=self.channel,
                defaults={
                    'provider_id': provider_id,
                    'name': attendee_info.get('name', 'Unknown'),
                    'picture_url': picture_url,
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
                logger.debug(f"✅ Created attendee: {attendee.name} ({external_id})")
            else:
                # Update existing attendee if needed
                self._update_attendee_if_changed(attendee, attendee_info)
            
            # Link to conversation if provided
            if conversation:
                self.link_attendee_to_conversation(attendee, conversation)
            
            return attendee
            
        except Exception as e:
            logger.error(f"Failed to create/update attendee: {e}")
            return None
    
    def _update_attendee_if_changed(
        self,
        attendee: ChatAttendee,
        attendee_info: Dict[str, Any]
    ) -> bool:
        """Update attendee if information has changed"""
        updated = False
        
        # Update name if changed and not generic
        if (attendee_info.get('name') and 
            attendee_info['name'] != attendee.name and
            not attendee.name.startswith('WhatsApp User')):
            attendee.name = attendee_info['name']
            updated = True
        
        # Update profile picture if changed
        if (attendee_info.get('profile_picture') and 
            attendee_info['profile_picture'] != attendee.picture_url):
            attendee.picture_url = attendee_info['profile_picture']
            updated = True
        
        # Update metadata
        if attendee.metadata is None:
            attendee.metadata = {}
        
        attendee.metadata['last_seen'] = timezone.now().isoformat()
        
        if attendee_info.get('phone_number'):
            attendee.metadata['phone_number'] = attendee_info['phone_number']
        
        if updated or attendee.metadata:
            attendee.save()
            if updated:
                logger.debug(f"Updated attendee: {attendee.name}")
        
        return updated
    
    def link_attendee_to_conversation(
        self,
        attendee: ChatAttendee,
        conversation: Conversation,
        role: str = AttendeeRole.MEMBER
    ) -> ConversationAttendee:
        """
        Link an attendee to a conversation
        
        Args:
            attendee: ChatAttendee instance
            conversation: Conversation instance
            role: Attendee role in conversation
            
        Returns:
            ConversationAttendee instance
        """
        conv_attendee, created = ConversationAttendee.objects.get_or_create(
            conversation=conversation,
            attendee=attendee,
            defaults={
                'role': role,
                'joined_at': timezone.now()
            }
        )
        
        if created:
            logger.debug(
                f"🔗 Linked attendee {attendee.name} to "
                f"conversation {conversation.id}"
            )
        
        return conv_attendee
    
    def sync_bulk_attendees(
        self,
        attendees_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Sync multiple attendees in bulk
        
        Args:
            attendees_data: List of attendee data dictionaries
            
        Returns:
            Statistics dictionary
        """
        stats = {
            'created': 0,
            'updated': 0,
            'failed': 0,
            'total': len(attendees_data)
        }
        
        for attendee_data in attendees_data:
            try:
                attendee = self.create_or_update_attendee(attendee_data)
                if attendee:
                    stats['created' if attendee.id else 'updated'] += 1
                else:
                    stats['failed'] += 1
            except Exception as e:
                logger.error(f"Failed to sync attendee: {e}")
                stats['failed'] += 1
        
        logger.info(
            f"Bulk attendee sync complete: "
            f"{stats['created']} created, "
            f"{stats['updated']} updated, "
            f"{stats['failed']} failed"
        )
        
        return stats