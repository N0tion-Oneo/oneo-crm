"""
Link Manager - Manages links between records and conversations

Creates and manages RecordCommunicationLink entries.
"""
import logging
from typing import Dict, List, Optional, Any
from django.db import transaction
from django.utils import timezone

from pipelines.models import Record
from communications.models import Conversation, Participant
from ..models import RecordCommunicationLink, RecordCommunicationProfile

logger = logging.getLogger(__name__)


class LinkManager:
    """Manages links between records and conversations"""
    
    def create_link(
        self,
        record: Record,
        conversation: Conversation,
        participant: Optional[Participant] = None,
        match_type: str = 'auto',
        matched_identifier: str = '',
        confidence: float = 1.0
    ) -> RecordCommunicationLink:
        """
        Create a link between a record and conversation
        
        Args:
            record: Record instance
            conversation: Conversation instance
            participant: Optional Participant that creates the link
            match_type: Type of match (email, phone, provider_id, etc.)
            matched_identifier: The identifier that matched
            confidence: Confidence score (0.0 to 1.0)
            
        Returns:
            RecordCommunicationLink instance
        """
        # Get or create the link
        link, created = RecordCommunicationLink.objects.get_or_create(
            record=record,
            conversation=conversation,
            participant=participant,
            defaults={
                'match_type': match_type,
                'match_identifier': matched_identifier,
                'confidence_score': confidence,
                'created_by_sync': True,
                'is_primary': True  # First link is primary by default
            }
        )
        
        if not created:
            # Update existing link if confidence is higher
            if confidence > link.confidence_score:
                link.confidence_score = confidence
                link.match_identifier = matched_identifier
                link.last_verified = timezone.now()
                link.save()
        
        logger.info(
            f"{'Created' if created else 'Updated'} link between "
            f"record {record.id} and conversation {conversation.id}"
        )
        
        return link
    
    def create_bulk_links(
        self,
        record: Record,
        conversations: List[Conversation],
        match_type: str = 'auto',
        matched_identifier: str = ''
    ) -> List[RecordCommunicationLink]:
        """
        Create multiple links for a record
        
        Args:
            record: Record instance
            conversations: List of Conversation instances
            match_type: Type of match
            matched_identifier: The identifier that matched
            
        Returns:
            List of RecordCommunicationLink instances
        """
        links = []
        
        with transaction.atomic():
            for conversation in conversations:
                try:
                    link = self.create_link(
                        record=record,
                        conversation=conversation,
                        match_type=match_type,
                        matched_identifier=matched_identifier
                    )
                    links.append(link)
                except Exception as e:
                    logger.error(f"Failed to create link: {e}")
                    continue
        
        logger.info(f"Created {len(links)} links for record {record.id}")
        return links
    
    def link_participant_to_record(
        self,
        participant: Participant,
        record: Record,
        confidence: float = 0.9
    ):
        """
        Link a participant to a record
        
        Args:
            participant: Participant instance
            record: Record instance
            confidence: Confidence in the match
        """
        if not participant.contact_record:
            participant.contact_record = record
            participant.resolution_confidence = confidence
            participant.resolution_method = 'record_sync'
            participant.resolved_at = timezone.now()
            participant.save()
            
            logger.info(f"Linked participant {participant.id} to record {record.id}")
    
    def get_record_conversations(
        self,
        record: Record,
        channel_type: Optional[str] = None
    ) -> List[Conversation]:
        """
        Get all conversations linked to a record
        
        Args:
            record: Record instance
            channel_type: Optional filter by channel type
            
        Returns:
            List of Conversation instances
        """
        links = RecordCommunicationLink.objects.filter(record=record)
        
        if channel_type:
            # Filter by conversations from specific channel type
            from communications.models import Conversation
            conv_ids = Conversation.objects.filter(
                channel__channel_type=channel_type
            ).values_list('id', flat=True)
            links = links.filter(conversation_id__in=conv_ids)
        
        conversation_ids = links.values_list('conversation_id', flat=True).distinct()
        
        return list(
            Conversation.objects.filter(id__in=conversation_ids)
            .select_related('channel')
            .order_by('-last_message_at')
        )
    
    def get_conversation_records(
        self,
        conversation: Conversation
    ) -> List[Record]:
        """
        Get all records linked to a conversation
        
        Args:
            conversation: Conversation instance
            
        Returns:
            List of Record instances
        """
        links = RecordCommunicationLink.objects.filter(
            conversation=conversation
        ).select_related('record')
        
        return [link.record for link in links]
    
    def verify_link(
        self,
        link: RecordCommunicationLink
    ) -> bool:
        """
        Verify if a link is still valid
        
        Args:
            link: RecordCommunicationLink instance
            
        Returns:
            True if link is valid
        """
        # Check if both record and conversation still exist
        if not link.record or not link.conversation:
            return False
        
        # Update verification timestamp
        link.last_verified = timezone.now()
        link.save(update_fields=['last_verified'])
        
        return True
    
    def remove_link(
        self,
        record: Record,
        conversation: Conversation
    ):
        """
        Remove a link between record and conversation
        
        Args:
            record: Record instance
            conversation: Conversation instance
        """
        RecordCommunicationLink.objects.filter(
            record=record,
            conversation=conversation
        ).delete()
        
        logger.info(f"Removed link between record {record.id} and conversation {conversation.id}")