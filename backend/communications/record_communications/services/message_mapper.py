"""
Service to map incoming messages from webhooks to records
"""
import logging
from typing import Dict, List, Optional, Any

from django.db import transaction
from django.utils import timezone

from pipelines.models import Record
from communications.models import (
    Conversation, Message, Participant, MessageDirection
)
from ..models import RecordCommunicationProfile
from .identifier_extractor import RecordIdentifierExtractor
# from communications.consumers import broadcast_to_channel  # TODO: Implement WebSocket broadcasting

logger = logging.getLogger(__name__)


class MessageMapper:
    """Map incoming webhook messages to records"""
    
    def __init__(self):
        self.identifier_extractor = RecordIdentifierExtractor()
    
    def process_webhook_message(
        self, 
        webhook_data: Dict[str, Any],
        channel_type: str,
        channel_id: int
    ) -> List[Record]:
        """
        Process incoming message from webhook and map to records.
        
        Args:
            webhook_data: Raw webhook data
            channel_type: Type of channel (email, whatsapp, etc.)
            channel_id: ID of the CommunicationConnection
            
        Returns:
            List of records that were linked to this message
        """
        try:
            # Extract sender identifiers from webhook data
            sender_identifiers = self._extract_sender_identifiers(
                webhook_data, channel_type
            )
            
            if not sender_identifiers:
                logger.warning(f"No identifiers found in webhook data for {channel_type}")
                return []
            
            # Find matching records using identifiers
            matching_records = self.identifier_extractor.find_records_by_identifiers(
                sender_identifiers
            )
            
            if not matching_records:
                logger.info(f"No matching records found for identifiers: {sender_identifiers}")
                return []
            
            # Get or create participant
            participant = self._get_or_create_participant(
                webhook_data, channel_type, sender_identifiers
            )
            
            # Get or create conversation
            conversation = self._get_or_create_conversation(
                webhook_data, channel_type, channel_id
            )
            
            # Store the message
            message = self._store_webhook_message(
                webhook_data, conversation, participant, channel_id
            )
            
            # Link to all matching records
            linked_records = []
            for record in matching_records:
                # Update participant with record link if not already linked
                if not participant.contact_record:
                    participant.contact_record = record
                    participant.resolution_confidence = 0.95
                    participant.resolution_method = f'{channel_type}_webhook_match'
                    participant.resolved_at = timezone.now()
                    participant.save()
                
                # No need to create RecordCommunicationLink anymore
                # The link is through the participant's contact_record
                # Always update record communication profile metrics for new messages
                self._update_record_profile(record, conversation, message)
                
                # Broadcast to record's WebSocket channel
                self._broadcast_to_record(record.id, message, conversation)
                
                linked_records.append(record)
            
            logger.info(
                f"Webhook message linked to {len(linked_records)} records: "
                f"{[r.id for r in linked_records]}"
            )
            
            return linked_records
            
        except Exception as e:
            logger.error(f"Error processing webhook message: {e}")
            return []
    
    def _extract_sender_identifiers(
        self, 
        webhook_data: Dict[str, Any],
        channel_type: str
    ) -> Dict[str, List[str]]:
        """Extract sender identifiers from webhook data"""
        identifiers = {
            'email': [],
            'phone': [],
            'linkedin': [],
            'domain': []
        }
        
        if channel_type == 'email':
            # Extract email from webhook
            from_email = (
                webhook_data.get('from', {}).get('email') or
                webhook_data.get('from_email') or
                webhook_data.get('sender', {}).get('email')
            )
            
            if from_email:
                identifiers['email'].append(from_email.lower())
                # Also extract domain
                if '@' in from_email:
                    domain = from_email.split('@')[1].lower()
                    if domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
                        identifiers['domain'].append(domain)
        
        elif channel_type == 'whatsapp':
            # Extract phone from webhook
            from_phone = (
                webhook_data.get('from_phone') or
                webhook_data.get('from', {}).get('phone') or
                webhook_data.get('sender', {}).get('attendee_provider_id', '').replace('@s.whatsapp.net', '')
            )
            
            if from_phone:
                # Normalize phone
                normalized = self.identifier_extractor._normalize_phone(from_phone)
                if normalized:
                    identifiers['phone'].append(normalized)
        
        elif channel_type == 'linkedin':
            # Extract LinkedIn ID
            linkedin_id = (
                webhook_data.get('from_linkedin') or
                webhook_data.get('sender', {}).get('linkedin_urn')
            )
            
            if linkedin_id:
                identifiers['linkedin'].append(f'linkedin:{linkedin_id}')
        
        return identifiers
    
    def _get_or_create_participant(
        self,
        webhook_data: Dict[str, Any],
        channel_type: str,
        identifiers: Dict[str, List[str]]
    ) -> Participant:
        """Get or create participant from webhook data"""
        # Build participant lookup query
        if identifiers.get('email'):
            participant = Participant.objects.filter(
                email=identifiers['email'][0]
            ).first()
        elif identifiers.get('phone'):
            participant = Participant.objects.filter(
                phone=identifiers['phone'][0]
            ).first()
        elif identifiers.get('linkedin'):
            participant = Participant.objects.filter(
                linkedin_member_urn=identifiers['linkedin'][0]
            ).first()
        else:
            participant = None
        
        if not participant:
            # Create new participant
            participant = Participant.objects.create(
                email=identifiers.get('email', [''])[0] or '',
                phone=identifiers.get('phone', [''])[0] or '',
                linkedin_member_urn=identifiers.get('linkedin', [''])[0] or '',
                name=self._extract_sender_name(webhook_data),
                metadata={'source': f'{channel_type}_webhook'}
            )
        
        return participant
    
    def _get_or_create_conversation(
        self,
        webhook_data: Dict[str, Any],
        channel_type: str,
        channel_id: int
    ) -> Conversation:
        """Get or create conversation from webhook data"""
        # Extract thread/conversation ID
        thread_id = (
            webhook_data.get('thread_id') or
            webhook_data.get('conversation_id') or
            webhook_data.get('chat_id')
        )
        
        if thread_id:
            conversation, created = Conversation.objects.get_or_create(
                external_thread_id=thread_id,
                channel_id=channel_id,
                defaults={
                    'subject': webhook_data.get('subject', f'{channel_type} conversation'),
                    'last_message_at': timezone.now()
                }
            )
        else:
            # Create new conversation for this message
            conversation = Conversation.objects.create(
                channel_id=channel_id,
                subject=webhook_data.get('subject', f'{channel_type} conversation'),
                last_message_at=timezone.now()
            )
        
        return conversation
    
    def _store_webhook_message(
        self,
        webhook_data: Dict[str, Any],
        conversation: Conversation,
        participant: Participant,
        channel_id: int
    ) -> Message:
        """Store message from webhook data"""
        # Determine message direction
        direction = webhook_data.get('direction', MessageDirection.INBOUND)
        if isinstance(direction, str):
            direction = MessageDirection.INBOUND if direction == 'inbound' else MessageDirection.OUTBOUND
        
        # Create message
        message = Message.objects.create(
            external_message_id=webhook_data.get('id', ''),
            conversation=conversation,
            channel_id=channel_id,
            sender_participant=participant,
            content=webhook_data.get('text', '') or webhook_data.get('body', {}).get('text', ''),
            subject=webhook_data.get('subject', ''),
            direction=direction,
            sent_at=webhook_data.get('timestamp') or webhook_data.get('date') or timezone.now(),
            contact_email=participant.email,
            contact_phone=participant.phone,
            sync_status='synced',
            metadata=webhook_data
        )
        
        # Update conversation last message time
        conversation.last_message_at = message.sent_at or message.created_at
        conversation.message_count += 1
        conversation.save(update_fields=['last_message_at', 'message_count'])
        
        return message
    
    def _update_record_profile(
        self,
        record: Record,
        conversation: Conversation,
        message: Message
    ):
        """Update record communication profile with new message"""
        try:
            profile = RecordCommunicationProfile.objects.get(record=record)
            
            # Update metrics
            profile.total_messages += 1
            profile.last_message_at = message.sent_at or message.created_at
            
            # Check if this is a new conversation for this record
            # Look for participants in this conversation linked to this record
            from communications.models import ConversationParticipant
            existing_participant_count = ConversationParticipant.objects.filter(
                conversation=conversation,
                participant__contact_record=record
            ).count()
            
            if existing_participant_count == 1:  # First participant linked to this record
                profile.total_conversations += 1
            
            # Update unread count if inbound message
            if message.direction == MessageDirection.INBOUND:
                profile.total_unread += 1
            
            profile.save(update_fields=[
                'total_messages', 'last_message_at', 
                'total_conversations', 'total_unread'
            ])
            
        except RecordCommunicationProfile.DoesNotExist:
            # Profile doesn't exist yet, will be created on next sync
            pass
    
    def _broadcast_to_record(
        self,
        record_id: int,
        message: Message,
        conversation: Conversation
    ):
        """Broadcast new message to record's WebSocket channel"""
        try:
            # Format message for frontend
            message_data = {
                'type': 'new_message',
                'message': {
                    'id': str(message.id),
                    'content': message.content,
                    'direction': message.direction,
                    'sent_at': message.sent_at.isoformat() if message.sent_at else None,
                    'sender': {
                        'name': message.sender_participant.name if message.sender_participant else 'Unknown',
                        'email': message.contact_email,
                        'phone': message.contact_phone
                    }
                },
                'conversation': {
                    'id': str(conversation.id),
                    'subject': conversation.subject,
                    'message_count': conversation.message_count
                }
            }
            
            # TODO: Broadcast to record channel when WebSocket is implemented
            # channel_name = f'record_communications:{record_id}'
            # broadcast_to_channel(channel_name, message_data)
            
            logger.info(f"Would broadcast new message to channel: record_communications:{record_id}")
            
        except Exception as e:
            logger.error(f"Error broadcasting to record {record_id}: {e}")
    
    def _get_primary_identifier(self, identifiers: Dict[str, List[str]]) -> str:
        """Get the primary identifier from a dict of identifiers"""
        if identifiers.get('email'):
            return identifiers['email'][0]
        elif identifiers.get('phone'):
            return identifiers['phone'][0]
        elif identifiers.get('linkedin'):
            return identifiers['linkedin'][0]
        else:
            return 'unknown'
    
    def _extract_sender_name(self, webhook_data: Dict[str, Any]) -> str:
        """Extract sender name from webhook data"""
        return (
            webhook_data.get('from', {}).get('name') or
            webhook_data.get('from_name') or
            webhook_data.get('sender', {}).get('name') or
            webhook_data.get('attendee', {}).get('name') or
            'Unknown'
        )