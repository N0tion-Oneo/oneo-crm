"""
Signal handlers to ensure all model fields are properly populated
"""
import logging
from django.db.models.signals import post_save, pre_save, m2m_changed
from django.dispatch import receiver
from django.utils import timezone

from communications.models import (
    Message, Conversation, Participant, ConversationParticipant,
    UserChannelConnection, TenantUniPileConfig
)
from communications.services.field_manager import field_manager

logger = logging.getLogger(__name__)


# ============== Message Signals ==============

@receiver(post_save, sender=Message)
def populate_message_fields(sender, instance, created, **kwargs):
    """Ensure all message fields are properly populated"""
    if created:
        # Set timestamps
        if instance.direction == 'inbound' and not instance.received_at:
            instance.received_at = instance.created_at
            instance.save(update_fields=['received_at'])
        
        # Update conversation stats
        if instance.conversation:
            conversation = instance.conversation
            conversation.message_count = conversation.messages.count()
            conversation.last_message_at = timezone.now()
            conversation.save(update_fields=['message_count', 'last_message_at'])
            
            # Update participant activity
            if instance.sender_participant:
                try:
                    conv_participant = ConversationParticipant.objects.get(
                        conversation=conversation,
                        participant=instance.sender_participant
                    )
                    field_manager.update_participant_activity(conv_participant)
                except ConversationParticipant.DoesNotExist:
                    # Create the relationship if it doesn't exist
                    ConversationParticipant.objects.create(
                        conversation=conversation,
                        participant=instance.sender_participant,
                        role='member',
                        message_count=1,
                        last_message_at=timezone.now()
                    )
            
            # Increment unread for other participants
            if instance.direction == 'inbound':
                other_participants = ConversationParticipant.objects.filter(
                    conversation=conversation,
                    is_active=True
                ).exclude(participant=instance.sender_participant)
                
                for conv_participant in other_participants:
                    field_manager.increment_unread(conv_participant)
        
        # Update participant stats
        if instance.sender_participant:
            field_manager.update_participant_stats(instance.sender_participant)
        
        # Track message sent for rate limiting
        if instance.direction == 'outbound' and instance.channel:
            # Find the UserChannelConnection
            try:
                connection = UserChannelConnection.objects.get(
                    unipile_account_id=instance.channel.unipile_account_id
                )
                field_manager.record_message_sent(connection)
            except UserChannelConnection.DoesNotExist:
                pass
        
        # Update channel stats
        if instance.channel:
            field_manager.update_channel_stats(instance.channel)


# ============== Conversation Signals ==============

@receiver(post_save, sender=Conversation)
def populate_conversation_fields(sender, instance, created, **kwargs):
    """Ensure conversation fields are properly populated"""
    if created:
        # Detect conversation type based on initial setup
        field_manager.detect_conversation_type(instance)
        
        # Set initial sync status
        instance.sync_status = 'pending'
        instance.save(update_fields=['sync_status'])


@receiver(post_save, sender=ConversationParticipant)
def update_conversation_participant_count(sender, instance, created, **kwargs):
    """Update conversation participant count when participants change"""
    if created or not instance.is_active:
        conversation = instance.conversation
        active_count = ConversationParticipant.objects.filter(
            conversation=conversation,
            is_active=True
        ).count()
        
        conversation.participant_count = active_count
        conversation.save(update_fields=['participant_count'])
        
        # Re-detect conversation type
        field_manager.detect_conversation_type(conversation, active_count)


# ============== Participant Signals ==============

@receiver(pre_save, sender=Participant)
def populate_participant_fields(sender, instance, **kwargs):
    """Ensure participant fields are populated before save"""
    # Set first_seen if this is a new participant
    if not instance.pk and not instance.first_seen:
        instance.first_seen = timezone.now()
    
    # Always update last_seen
    instance.last_seen = timezone.now()
    
    # Extract social handles from metadata if available
    if instance.metadata:
        metadata = instance.metadata
        
        if not instance.instagram_username and metadata.get('instagram_username'):
            instance.instagram_username = metadata['instagram_username']
        
        if not instance.facebook_id and metadata.get('facebook_id'):
            instance.facebook_id = metadata['facebook_id']
        
        if not instance.telegram_id and metadata.get('telegram_id'):
            instance.telegram_id = metadata['telegram_id']
        
        if not instance.twitter_handle and metadata.get('twitter_handle'):
            instance.twitter_handle = metadata['twitter_handle']


@receiver(post_save, sender=Participant)
def update_participant_stats_on_save(sender, instance, created, **kwargs):
    """Update participant statistics after save"""
    # Removed to prevent infinite recursion
    # The stats should be updated when messages are created, not on every save
    pass


# ============== UserChannelConnection Signals ==============

@receiver(pre_save, sender=UserChannelConnection)
def populate_connection_fields(sender, instance, **kwargs):
    """Ensure connection fields are properly populated"""
    # Initialize rate limiting fields
    if not instance.last_rate_limit_reset:
        instance.last_rate_limit_reset = timezone.now()
    
    # Set default rate limit if not set
    if not instance.rate_limit_per_hour:
        instance.rate_limit_per_hour = 100


@receiver(post_save, sender=UserChannelConnection)
def sync_connection_success(sender, instance, **kwargs):
    """Update fields when connection syncs successfully"""
    if instance.account_status == 'active' and not instance.last_sync_at:
        instance.last_sync_at = timezone.now()
        instance.sync_error_count = 0
        instance.last_error = ''
        instance.save(update_fields=['last_sync_at', 'sync_error_count', 'last_error'])


# ============== TenantUniPileConfig Signals ==============

@receiver(post_save, sender=TenantUniPileConfig)
def initialize_tenant_config(sender, instance, created, **kwargs):
    """Initialize tenant config with default preferences"""
    if created and not instance.provider_preferences:
        # Set default provider preferences
        default_prefs = instance.get_default_provider_preferences()
        instance.provider_preferences = default_prefs
        instance.save(update_fields=['provider_preferences'])


# ============== Analytics Generation ==============

def generate_daily_analytics():
    """Generate daily analytics for all channels (called by Celery task)"""
    from communications.models import Channel
    from datetime import date
    
    today = date.today()
    
    # Generate tenant-wide analytics
    field_manager.create_daily_analytics(today, channel=None)
    
    # Generate per-channel analytics
    for channel in Channel.objects.filter(is_active=True):
        field_manager.create_daily_analytics(today, channel=channel)
    
    logger.info(f"Generated daily analytics for {today}")