"""
Participant Link Manager - Manages linking participants to records

This is the simplified replacement for LinkManager that only handles
participant-to-record linking, not RecordCommunicationLink creation.
"""
import logging
from typing import List, Optional
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from pipelines.models import Record
from communications.models import Conversation, Participant, ConversationParticipant

logger = logging.getLogger(__name__)


class ParticipantLinkManager:
    """Manages linking participants to records"""
    
    def link_participant_to_record(
        self,
        participant: Participant,
        record: Record,
        confidence: float = 0.9,
        method: str = 'manual'
    ) -> bool:
        """
        Link a participant to a record
        
        Args:
            participant: Participant instance
            record: Record instance
            confidence: Confidence score (0.0 to 1.0)
            method: Method used for linking (manual, email_match, phone_match, etc.)
        
        Returns:
            True if newly linked, False if already linked
        """
        if participant.contact_record_id == record.id:
            return False
            
        participant.contact_record = record
        participant.resolution_confidence = confidence
        participant.resolution_method = method
        participant.resolved_at = timezone.now()
        participant.save()
        
        logger.info(f"Linked participant {participant.id} to record {record.id} via {method}")
        return True
    
    def unlink_participant(self, participant: Participant) -> bool:
        """
        Unlink a participant from their record
        
        Args:
            participant: Participant instance
            
        Returns:
            True if unlinked, False if was not linked
        """
        if not participant.contact_record:
            return False
            
        record_id = participant.contact_record_id
        participant.contact_record = None
        participant.resolution_confidence = 0
        participant.resolution_method = ''
        participant.resolved_at = None
        participant.save()
        
        logger.info(f"Unlinked participant {participant.id} from record {record_id}")
        return True
    
    def get_record_participants(self, record: Record) -> QuerySet:
        """
        Get all participants linked to a record
        
        Args:
            record: Record instance
            
        Returns:
            QuerySet of Participant instances
        """
        return Participant.objects.filter(contact_record=record)
    
    def get_record_conversations(
        self,
        record: Record,
        channel_type: Optional[str] = None
    ) -> List[Conversation]:
        """
        Get all conversations linked to a record through participants
        
        Args:
            record: Record instance
            channel_type: Optional filter by channel type
            
        Returns:
            List of Conversation instances
        """
        # Get all participants linked to this record
        participants = self.get_record_participants(record)
        
        # Get conversations through participants
        query = Conversation.objects.filter(
            conversation_participants__participant__in=participants
        ).distinct()
        
        if channel_type:
            query = query.filter(channel__channel_type=channel_type)
        
        return list(query.order_by('-last_message_at'))
    
    def get_conversation_records(self, conversation: Conversation) -> List[Record]:
        """
        Get all records linked to a conversation through participants
        
        Args:
            conversation: Conversation instance
            
        Returns:
            List of Record instances
        """
        # Get all participants in this conversation
        participants = Participant.objects.filter(
            conversation_participants__conversation=conversation
        ).exclude(contact_record__isnull=True)
        
        # Get unique records from participants
        record_ids = participants.values_list('contact_record_id', flat=True).distinct()
        return list(Record.objects.filter(id__in=record_ids))
    
    def link_participants_by_identifier(
        self,
        record: Record,
        identifier_type: str,
        identifier_value: str,
        confidence: float = 0.9
    ) -> int:
        """
        Link all participants with a specific identifier to a record
        
        Args:
            record: Record instance
            identifier_type: Type of identifier (email, phone, linkedin)
            identifier_value: Value to match
            confidence: Confidence score
            
        Returns:
            Number of participants linked
        """
        linked_count = 0
        
        with transaction.atomic():
            if identifier_type == 'email':
                participants = Participant.objects.filter(
                    email__iexact=identifier_value,
                    contact_record__isnull=True
                )
                method = 'email_match'
            elif identifier_type == 'phone':
                participants = Participant.objects.filter(
                    phone=identifier_value,
                    contact_record__isnull=True
                )
                method = 'phone_match'
            elif identifier_type == 'linkedin':
                participants = Participant.objects.filter(
                    linkedin_member_urn=identifier_value,
                    contact_record__isnull=True
                )
                method = 'linkedin_match'
            else:
                logger.warning(f"Unknown identifier type: {identifier_type}")
                return 0
            
            for participant in participants:
                if self.link_participant_to_record(participant, record, confidence, method):
                    linked_count += 1
        
        if linked_count > 0:
            logger.info(f"Linked {linked_count} participants to record {record.id} via {identifier_type}")
        
        return linked_count
    
    def update_participant_confidence(
        self,
        participant: Participant,
        new_confidence: float,
        reason: str = ''
    ):
        """
        Update the confidence score for a participant-record link
        
        Args:
            participant: Participant instance
            new_confidence: New confidence score
            reason: Optional reason for the update
        """
        if not participant.contact_record:
            return
            
        participant.resolution_confidence = new_confidence
        participant.resolved_at = timezone.now()
        if reason:
            participant.resolution_method = f"{participant.resolution_method}_{reason}"
        participant.save()
        
        logger.info(
            f"Updated confidence for participant {participant.id}: "
            f"{new_confidence} (reason: {reason})"
        )