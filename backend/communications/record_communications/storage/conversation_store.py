"""
Conversation Store - Handles persistence of conversation data

Stores conversations from UniPile and manages updates.
"""
import logging
from typing import Dict, List, Optional, Any
from django.db import transaction
from django.utils import timezone

from communications.models import (
    Conversation, Channel, Participant, ConversationParticipant
)
from communications.services.field_manager import field_manager

logger = logging.getLogger(__name__)


class ConversationStore:
    """Stores and manages conversation data"""
    
    def store_conversation(
        self,
        conversation_data: Dict[str, Any],
        channel: Channel
    ) -> Conversation:
        """
        Store or update a conversation
        
        Args:
            conversation_data: Transformed conversation data
            channel: Channel instance
            
        Returns:
            Conversation instance
        """
        external_id = conversation_data.get('external_conversation_id')
        
        if not external_id:
            raise ValueError("Conversation must have external_conversation_id")
        
        # Get or create conversation
        conversation, created = Conversation.objects.get_or_create(
            external_thread_id=external_id,
            channel=channel,
            defaults={
                'subject': conversation_data.get('subject', ''),
                'last_message_at': conversation_data.get('last_message_at'),
                'metadata': conversation_data.get('metadata', {}),
                'unread_count': conversation_data.get('unread_count', 0)
            }
        )
        
        if not created:
            # Update existing conversation
            conversation.subject = conversation_data.get('subject', conversation.subject)
            conversation.last_message_at = conversation_data.get('last_message_at', conversation.last_message_at)
            conversation.metadata.update(conversation_data.get('metadata', {}))
            conversation.unread_count = conversation_data.get('unread_count', conversation.unread_count)
            # Note: is_read field doesn't exist on Conversation model
            # This would need to be tracked differently if needed
            conversation.save()
        else:
            # New conversation created - use field manager to set additional fields
            # Detect conversation type based on metadata
            field_manager.detect_conversation_type(conversation)
            
            # Set initial sync status
            field_manager.update_conversation_sync_status(
                conversation, 
                'synced',
                error=None
            )
            
            # Mark as hot if it has many messages
            if conversation_data.get('message_count', 0) > 50:
                field_manager.mark_conversation_hot(conversation, True)
        
        logger.info(
            f"{'Created' if created else 'Updated'} conversation {conversation.id} "
            f"(external: {external_id})"
        )
        
        return conversation
    
    def store_bulk_conversations(
        self,
        conversations_data: List[Dict[str, Any]],
        channel: Channel
    ) -> List[Conversation]:
        """
        Store multiple conversations efficiently
        
        Args:
            conversations_data: List of transformed conversation data
            channel: Channel instance
            
        Returns:
            List of Conversation instances
        """
        conversations = []
        
        with transaction.atomic():
            for conv_data in conversations_data:
                try:
                    conversation = self.store_conversation(conv_data, channel)
                    conversations.append(conversation)
                except Exception as e:
                    logger.error(f"Failed to store conversation: {e}")
                    continue
        
        logger.info(f"Stored {len(conversations)} conversations")
        return conversations
    
    def link_participants_to_conversation(
        self,
        conversation: Conversation,
        participants_data: List[Dict[str, Any]]
    ) -> List[ConversationParticipant]:
        """
        Link participants to a conversation
        
        Args:
            conversation: Conversation instance
            participants_data: List of participant data
            
        Returns:
            List of ConversationParticipant instances
        """
        conversation_participants = []
        
        for participant_data in participants_data:
            participant = self._get_or_create_participant(participant_data)
            
            # Create link between participant and conversation
            conv_participant, created = ConversationParticipant.objects.get_or_create(
                conversation=conversation,
                participant=participant,
                defaults={
                    'is_primary': participant_data.get('is_primary', False),
                    'joined_at': participant_data.get('joined_at', timezone.now())
                }
            )
            
            conversation_participants.append(conv_participant)
        
        return conversation_participants
    
    def _get_or_create_participant(self, participant_data: Dict[str, Any]) -> Participant:
        """
        Get or create a participant
        
        Args:
            participant_data: Transformed participant data
            
        Returns:
            Participant instance
        """
        # Try to find existing participant by various identifiers
        email = participant_data.get('email', '')
        phone = participant_data.get('phone', '')
        
        # Build query for existing participant
        from django.db.models import Q
        query = Q()
        
        if email:
            query |= Q(email__iexact=email)
        if phone:
            query |= Q(phone=phone)
        
        # Check for provider_id in metadata
        provider_id = participant_data.get('metadata', {}).get('provider_id')
        if provider_id:
            query |= Q(metadata__provider_id=provider_id)
        
        if query:
            participant = Participant.objects.filter(query).first()
            
            if participant:
                # Update participant info if needed
                if not participant.name and participant_data.get('name'):
                    participant.name = participant_data['name']
                if not participant.avatar_url and participant_data.get('avatar_url'):
                    participant.avatar_url = participant_data['avatar_url']
                
                # Update identifiers
                for field in ['email', 'phone', 'linkedin_member_urn', 
                            'instagram_username', 'telegram_id']:
                    if participant_data.get(field) and not getattr(participant, field):
                        setattr(participant, field, participant_data[field])
                
                participant.save()
                return participant
        
        # Create new participant
        participant = Participant.objects.create(**participant_data)
        logger.info(f"Created new participant {participant.id}: {participant.name or participant.email or participant.phone}")
        
        return participant
    
    def update_conversation_metrics(
        self,
        conversation: Conversation,
        message_count: Optional[int] = None,
        unread_count: Optional[int] = None,
        last_message_at: Optional[Any] = None
    ):
        """
        Update conversation metrics
        
        Args:
            conversation: Conversation instance
            message_count: Total message count
            unread_count: Unread message count
            last_message_at: Timestamp of last message
        """
        update_fields = []
        
        if message_count is not None:
            conversation.message_count = message_count
            update_fields.append('message_count')
        
        if unread_count is not None:
            conversation.unread_count = unread_count
            update_fields.append('unread_count')
        
        if last_message_at is not None:
            conversation.last_message_at = last_message_at
            update_fields.append('last_message_at')
        
        if update_fields:
            conversation.save(update_fields=update_fields)