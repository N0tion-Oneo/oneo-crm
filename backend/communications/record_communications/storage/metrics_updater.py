"""
Metrics Updater - Updates communication metrics for records

Calculates and updates RecordCommunicationProfile metrics.
"""
import logging
from typing import Dict, Optional, Any
from django.db import models
from django.utils import timezone

from pipelines.models import Record
from communications.models import Conversation, Message
from ..models import RecordCommunicationProfile

logger = logging.getLogger(__name__)


class MetricsUpdater:
    """Updates communication metrics for records"""
    
    def update_profile_metrics(
        self,
        record: Record,
        force_recalculate: bool = False
    ) -> RecordCommunicationProfile:
        """
        Update all metrics for a record's communication profile
        
        Args:
            record: Record instance
            force_recalculate: Force recalculation of all metrics
            
        Returns:
            Updated RecordCommunicationProfile
        """
        # Get or create profile
        profile, created = RecordCommunicationProfile.objects.get_or_create(
            record=record,
            defaults={
                'pipeline': record.pipeline
            }
        )
        
        # Calculate metrics
        metrics = self.calculate_metrics(record)
        
        # Use model's update_metrics method
        profile.update_metrics(
            conversations=metrics['total_conversations'],
            messages=metrics['total_messages'],
            unread=metrics['total_unread']
        )
        
        # Update last message timestamp separately if changed
        if metrics['last_message_at'] and (not profile.last_message_at or metrics['last_message_at'] > profile.last_message_at):
            profile.last_message_at = metrics['last_message_at']
            profile.save(update_fields=['last_message_at', 'updated_at'])
        
        logger.info(
            f"Updated metrics for record {record.id}: "
            f"{metrics['total_conversations']} conversations, "
            f"{metrics['total_messages']} messages"
        )
        
        return profile
    
    def calculate_metrics(self, record: Record) -> Dict[str, Any]:
        """
        Calculate communication metrics for a record
        
        Args:
            record: Record instance
            
        Returns:
            Dict with calculated metrics
        """
        # Get all conversations linked through participants (both primary and secondary)
        from communications.models import Participant, ConversationParticipant
        from django.db.models import Q
        participants = Participant.objects.filter(
            Q(contact_record=record) | Q(secondary_record=record)
        )
        conversation_ids = ConversationParticipant.objects.filter(
            participant__in=participants
        ).values_list('conversation_id', flat=True).distinct()
        
        # Calculate conversation count
        total_conversations = len(conversation_ids)
        
        # Calculate message count
        total_messages = Message.objects.filter(
            conversation_id__in=conversation_ids
        ).count()
        
        # Calculate unread count from conversations
        # Note: Neither Message nor Conversation models have is_read field
        # Using unread_count field instead
        total_unread = Conversation.objects.filter(
            id__in=conversation_ids
        ).aggregate(
            total=models.Sum('unread_count')
        )['total'] or 0
        
        # Get last message timestamp
        last_message = Message.objects.filter(
            conversation_id__in=conversation_ids
        ).order_by('-created_at').first()
        
        last_message_at = last_message.created_at if last_message else None
        
        return {
            'total_conversations': total_conversations,
            'total_messages': total_messages,
            'total_unread': total_unread,
            'last_message_at': last_message_at
        }
    
    def increment_metrics(
        self,
        record: Record,
        conversations_added: int = 0,
        messages_added: int = 0,
        unread_added: int = 0
    ) -> RecordCommunicationProfile:
        """
        Increment metrics without full recalculation
        
        Args:
            record: Record instance
            conversations_added: Number of conversations added
            messages_added: Number of messages added
            unread_added: Number of unread messages added
            
        Returns:
            Updated RecordCommunicationProfile
        """
        profile = RecordCommunicationProfile.objects.filter(
            record=record
        ).first()
        
        if not profile:
            # Create and calculate from scratch
            return self.update_profile_metrics(record)
        
        # Increment counters
        if conversations_added:
            profile.total_conversations = models.F('total_conversations') + conversations_added
        
        if messages_added:
            profile.total_messages = models.F('total_messages') + messages_added
        
        if unread_added:
            profile.total_unread = models.F('total_unread') + unread_added
        
        profile.save()
        
        # Refresh from database to get actual values
        profile.refresh_from_db()
        
        return profile
    
    def update_last_message_time(
        self,
        record: Record,
        timestamp: Any
    ):
        """
        Update the last message timestamp for a record
        
        Args:
            record: Record instance
            timestamp: New last message timestamp
        """
        profile = RecordCommunicationProfile.objects.filter(
            record=record
        ).first()
        
        if profile:
            # Only update if newer
            if not profile.last_message_at or timestamp > profile.last_message_at:
                profile.last_message_at = timestamp
                profile.save(update_fields=['last_message_at'])
    
    def mark_messages_read(
        self,
        record: Record,
        conversation: Optional[Conversation] = None
    ) -> int:
        """
        Mark messages as read for a record
        
        Args:
            record: Record instance
            conversation: Optional specific conversation
            
        Returns:
            Number of messages marked as read
        """
        # Get linked conversations through participants (both primary and secondary)
        from communications.models import Participant, ConversationParticipant
        from django.db.models import Q
        participants = Participant.objects.filter(
            Q(contact_record=record) | Q(secondary_record=record)
        )
        
        if conversation:
            conversation_ids = [conversation.id]
        else:
            conversation_ids = ConversationParticipant.objects.filter(
                participant__in=participants
            ).values_list('conversation_id', flat=True)
        
        # Mark conversations as read by setting unread_count to 0
        # Note: Neither Message nor Conversation models have is_read field
        updated = Conversation.objects.filter(
            id__in=conversation_ids,
            unread_count__gt=0
        ).update(unread_count=0)
        
        # Update profile unread count
        if updated > 0:
            profile = RecordCommunicationProfile.objects.filter(
                record=record
            ).first()
            
            if profile:
                # Recalculate unread count from conversations (both primary and secondary)
                from communications.models import Participant, ConversationParticipant
                from django.db.models import Q
                participants = Participant.objects.filter(
                    Q(contact_record=record) | Q(secondary_record=record)
                )
                conv_ids = ConversationParticipant.objects.filter(
                    participant__in=participants
                ).values_list('conversation_id', flat=True)
                
                new_unread = Conversation.objects.filter(
                    id__in=conv_ids
                ).aggregate(
                    total=models.Sum('unread_count')
                )['total'] or 0
                
                profile.total_unread = new_unread
                profile.save(update_fields=['total_unread'])
        
        return updated
    
    def get_channel_breakdown(
        self,
        record: Record
    ) -> Dict[str, Dict[str, int]]:
        """
        Get communication breakdown by channel
        
        Args:
            record: Record instance
            
        Returns:
            Dict with channel statistics
        """
        # Get all conversations through participants grouped by channel type (both primary and secondary)
        from communications.models import Participant, ConversationParticipant
        from django.db.models import Q
        participants = Participant.objects.filter(
            Q(contact_record=record) | Q(secondary_record=record)
        )
        
        # Get conversations with channel info
        conversations = Conversation.objects.filter(
            conversation_participants__participant__in=participants
        ).select_related('channel').distinct()
        
        breakdown = {}
        
        # Group by channel type
        for conversation in conversations:
            channel_type = conversation.channel.channel_type if conversation.channel else 'unknown'
            
            if channel_type not in breakdown:
                breakdown[channel_type] = {
                    'conversations': 0,
                    'messages': 0,
                    'unread': 0
                }
            
            breakdown[channel_type]['conversations'] += 1
            breakdown[channel_type]['messages'] += conversation.messages.count()
            breakdown[channel_type]['unread'] += conversation.unread_count or 0
        
        return breakdown