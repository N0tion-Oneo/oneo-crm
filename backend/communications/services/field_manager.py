"""
Field Manager Service - Ensures all model fields are properly populated
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from django.db import models, transaction
from django.utils import timezone
from django.db.models import F, Q, Count
from cryptography.fernet import Fernet
from django.conf import settings

logger = logging.getLogger(__name__)


class FieldManager:
    """Manages proper field population for all communication models"""
    
    def __init__(self):
        # Initialize encryption for tokens
        # Generate a proper Fernet key from SECRET_KEY
        import hashlib
        import base64
        
        # Create a proper 32-byte key from SECRET_KEY
        key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        fernet_key = base64.urlsafe_b64encode(key)
        self.cipher_suite = Fernet(fernet_key)
    
    # ============== TenantUniPileConfig Field Management ==============
    
    def update_webhook_status(self, config, success: bool = True, secret: str = None):
        """Update webhook tracking fields"""
        from communications.models import TenantUniPileConfig
        
        if success:
            config.last_webhook_received = timezone.now()
            config.webhook_failures = 0
        else:
            config.webhook_failures = F('webhook_failures') + 1
        
        if secret:
            config.webhook_secret = secret
            
        config.save(update_fields=[
            'last_webhook_received', 'webhook_failures', 'webhook_secret'
        ] if secret else ['last_webhook_received', 'webhook_failures'])
        
        logger.info(f"Updated webhook status for tenant config: success={success}")
    
    def set_provider_preferences(self, config, provider_type: str, preferences: Dict):
        """Set provider preferences with validation"""
        from communications.models import TenantUniPileConfig
        
        if not config.provider_preferences:
            config.provider_preferences = {}
        
        # Ensure preferences include all required fields
        default_prefs = {
            'enabled_features': [],
            'auto_sync_enabled': True,
            'sync_frequency': 'real_time',
            'auto_create_contacts': True,
            'rate_limits': {},
            'notifications_enabled': True
        }
        
        # Merge with defaults
        final_prefs = {**default_prefs, **preferences}
        config.provider_preferences[provider_type] = final_prefs
        
        config.save(update_fields=['provider_preferences'])
        logger.info(f"Set provider preferences for {provider_type}")
    
    # ============== UserChannelConnection Field Management ==============
    
    def store_tokens(self, connection, access_token: str, refresh_token: str = None, 
                    expires_in: int = None):
        """Encrypt and store authentication tokens"""
        from communications.models import UserChannelConnection
        
        # Encrypt tokens
        if access_token:
            connection.access_token = self.cipher_suite.encrypt(access_token.encode()).decode()
        
        if refresh_token:
            connection.refresh_token = self.cipher_suite.encrypt(refresh_token.encode()).decode()
        
        # Set expiration
        if expires_in:
            connection.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
        
        connection.save(update_fields=['access_token', 'refresh_token', 'token_expires_at'])
        logger.info(f"Stored encrypted tokens for connection {connection.id}")
    
    def get_decrypted_token(self, connection) -> Optional[str]:
        """Get decrypted access token"""
        if not connection.access_token:
            return None
        
        try:
            return self.cipher_suite.decrypt(connection.access_token.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt token: {e}")
            return None
    
    def record_message_sent(self, connection):
        """Track messages sent for rate limiting"""
        from communications.models import UserChannelConnection
        
        now = timezone.now()
        
        # Reset daily counter if needed
        if not connection.last_rate_limit_reset or \
           connection.last_rate_limit_reset.date() != now.date():
            connection.messages_sent_today = 1
            connection.last_rate_limit_reset = now
        else:
            connection.messages_sent_today = F('messages_sent_today') + 1
        
        connection.messages_sent_count = F('messages_sent_count') + 1
        
        connection.save(update_fields=[
            'messages_sent_today', 'messages_sent_count', 'last_rate_limit_reset'
        ])
        
        logger.debug(f"Recorded message sent for connection {connection.id}")
    
    def set_custom_rate_limit(self, connection, rate_limit: int):
        """Set custom rate limit for connection"""
        connection.rate_limit_per_hour = rate_limit
        connection.save(update_fields=['rate_limit_per_hour'])
        logger.info(f"Set rate limit to {rate_limit} for connection {connection.id}")
    
    # ============== Channel Field Management ==============
    
    def update_channel_stats(self, channel):
        """Update channel statistics"""
        from communications.models import Message
        
        stats = Message.objects.filter(channel=channel).aggregate(
            total=Count('id'),
            last_message=models.Max('created_at')
        )
        
        channel.message_count = stats['total'] or 0
        channel.last_message_at = stats['last_message']
        channel.last_sync_at = timezone.now()
        
        channel.save(update_fields=['message_count', 'last_message_at', 'last_sync_at'])
        logger.info(f"Updated stats for channel {channel.id}: {stats['total']} messages")
    
    def set_channel_sync_settings(self, channel, settings: Dict):
        """Set channel sync settings"""
        channel.sync_settings = settings
        channel.save(update_fields=['sync_settings'])
        logger.info(f"Updated sync settings for channel {channel.id}")
    
    # ============== Conversation Field Management ==============
    
    def detect_conversation_type(self, conversation, participant_count: int = None):
        """Detect and set conversation type based on participants"""
        from communications.models import ConversationType, ConversationParticipant
        
        if participant_count is None:
            participant_count = ConversationParticipant.objects.filter(
                conversation=conversation,
                is_active=True
            ).count()
        
        # Determine type based on metadata and participant count
        metadata = conversation.metadata or {}
        
        if metadata.get('is_broadcast'):
            conversation.conversation_type = ConversationType.BROADCAST
        elif metadata.get('is_channel') or metadata.get('is_community'):
            conversation.conversation_type = ConversationType.CHANNEL
        elif participant_count > 2:
            conversation.conversation_type = ConversationType.GROUP
        else:
            conversation.conversation_type = ConversationType.DIRECT
        
        conversation.participant_count = participant_count
        conversation.save(update_fields=['conversation_type', 'participant_count'])
        
        logger.info(f"Set conversation {conversation.id} type to {conversation.conversation_type}")
    
    def set_conversation_priority(self, conversation, priority: str):
        """Set conversation priority"""
        from communications.models import Priority
        
        if priority in [p.value for p in Priority]:
            conversation.priority = priority
            conversation.save(update_fields=['priority'])
            logger.info(f"Set conversation {conversation.id} priority to {priority}")
    
    def mark_conversation_hot(self, conversation, is_hot: bool = True):
        """Mark conversation as frequently accessed"""
        conversation.is_hot = is_hot
        conversation.last_accessed_at = timezone.now()
        conversation.save(update_fields=['is_hot', 'last_accessed_at'])
    
    def update_conversation_sync_status(self, conversation, status: str, error: str = None):
        """Update conversation sync status"""
        conversation.sync_status = status
        conversation.last_synced_at = timezone.now()
        
        if error:
            conversation.sync_error_count = F('sync_error_count') + 1
            conversation.sync_error_message = error[:500]  # Truncate long errors
        else:
            conversation.sync_error_count = 0
            conversation.sync_error_message = ''
        
        conversation.save(update_fields=[
            'sync_status', 'last_synced_at', 'sync_error_count', 'sync_error_message'
        ])
    
    def update_conversation_stats(self, conversation):
        """Update conversation statistics (message count, last message time)"""
        from communications.models import Message
        
        # Get aggregated stats from messages
        stats = Message.objects.filter(conversation=conversation).aggregate(
            total=Count('id'),
            last_message=models.Max('created_at')
        )
        
        conversation.message_count = stats['total'] or 0
        conversation.last_message_at = stats['last_message']
        
        # Update participant count from active participants
        from communications.models import ConversationParticipant
        active_participant_count = ConversationParticipant.objects.filter(
            conversation=conversation,
            is_active=True
        ).count()
        
        conversation.participant_count = active_participant_count
        
        # Save the updated stats
        conversation.save(update_fields=[
            'message_count', 'last_message_at', 'participant_count'
        ])
        
        logger.debug(f"Updated stats for conversation {conversation.id}: "
                    f"{conversation.message_count} messages, "
                    f"{conversation.participant_count} participants")
    
    # ============== Message Field Management ==============
    
    def set_message_timestamps(self, message, sent_at: datetime = None, 
                              received_at: datetime = None):
        """Set message timestamps properly"""
        if sent_at:
            message.sent_at = sent_at
        
        if received_at:
            message.received_at = received_at
        elif message.direction == 'inbound' and not message.received_at:
            message.received_at = message.created_at
        
        message.save(update_fields=['sent_at', 'received_at'])
    
    def set_message_subject(self, message, subject: str):
        """Set message subject (for emails)"""
        if subject:
            message.subject = subject[:500]  # Truncate to field max length
            message.save(update_fields=['subject'])
    
    def mark_message_local_only(self, message, is_local: bool = True):
        """Mark message as local-only (not synced to provider)"""
        message.is_local_only = is_local
        
        if is_local:
            message.sync_status = 'pending'
        
        message.save(update_fields=['is_local_only', 'sync_status'])
    
    # ============== Participant Field Management ==============
    
    def set_participant_social_handles(self, participant, 
                                      instagram: str = None,
                                      facebook: str = None,
                                      telegram: str = None,
                                      twitter: str = None):
        """Set social media handles for participant"""
        update_fields = []
        
        if instagram:
            participant.instagram_username = instagram
            update_fields.append('instagram_username')
        
        if facebook:
            participant.facebook_id = facebook
            update_fields.append('facebook_id')
        
        if telegram:
            participant.telegram_id = telegram
            update_fields.append('telegram_id')
        
        if twitter:
            participant.twitter_handle = twitter
            update_fields.append('twitter_handle')
        
        if update_fields:
            participant.save(update_fields=update_fields)
            logger.info(f"Updated social handles for participant {participant.id}")
    
    def record_participant_resolution(self, participant, record, 
                                     confidence: float, method: str):
        """Record contact resolution details"""
        participant.contact_record = record
        participant.resolution_confidence = confidence
        participant.resolution_method = method
        participant.resolved_at = timezone.now()
        
        participant.save(update_fields=[
            'contact_record', 'resolution_confidence', 
            'resolution_method', 'resolved_at'
        ])
        
        logger.info(f"Resolved participant {participant.id} to record {record.id} "
                   f"(confidence: {confidence}, method: {method})")
    
    def record_secondary_resolution(self, participant, record, 
                                   confidence: float, method: str, pipeline_name: str):
        """Record secondary record resolution (e.g., company)"""
        participant.secondary_record = record
        participant.secondary_confidence = confidence
        participant.secondary_resolution_method = method
        participant.secondary_pipeline = pipeline_name
        
        participant.save(update_fields=[
            'secondary_record', 'secondary_confidence',
            'secondary_resolution_method', 'secondary_pipeline'
        ])
        
        logger.info(f"Resolved participant {participant.id} secondary to {record.id}")
    
    def update_participant_stats(self, participant):
        """Update participant statistics"""
        from communications.models import ConversationParticipant, Message
        
        # Count conversations
        conversation_count = ConversationParticipant.objects.filter(
            participant=participant,
            is_active=True
        ).count()
        
        # Count messages
        message_count = Message.objects.filter(
            sender_participant=participant
        ).count()
        
        participant.total_conversations = conversation_count
        participant.total_messages = message_count
        participant.last_seen = timezone.now()
        
        participant.save(update_fields=[
            'total_conversations', 'total_messages', 'last_seen'
        ])
        
        logger.debug(f"Updated stats for participant {participant.id}: "
                    f"{conversation_count} conversations, {message_count} messages")
    
    # ============== ConversationParticipant Field Management ==============
    
    def set_provider_participant_id(self, conv_participant, provider_id: str):
        """Set provider-specific participant ID"""
        conv_participant.provider_participant_id = provider_id
        conv_participant.save(update_fields=['provider_participant_id'])
    
    def mark_participant_left(self, conv_participant):
        """Mark participant as left the conversation"""
        conv_participant.is_active = False
        conv_participant.left_at = timezone.now()
        conv_participant.save(update_fields=['is_active', 'left_at'])
        
        logger.info(f"Marked participant {conv_participant.participant_id} as left")
    
    def update_participant_activity(self, conv_participant, increment_messages: bool = True):
        """Update participant activity in conversation"""
        if increment_messages:
            conv_participant.message_count = F('message_count') + 1
        
        conv_participant.last_message_at = timezone.now()
        
        conv_participant.save(update_fields=['message_count', 'last_message_at'])
    
    def mark_messages_read(self, conv_participant):
        """Mark messages as read for participant"""
        conv_participant.last_read_at = timezone.now()
        conv_participant.unread_count = 0
        
        conv_participant.save(update_fields=['last_read_at', 'unread_count'])
    
    def increment_unread(self, conv_participant, count: int = 1):
        """Increment unread message count"""
        conv_participant.unread_count = F('unread_count') + count
        conv_participant.save(update_fields=['unread_count'])
    
    # ============== CommunicationAnalytics Field Management ==============
    
    def create_daily_analytics(self, date: datetime.date = None, channel=None):
        """Create or update daily analytics"""
        from communications.models import (
            CommunicationAnalytics, Message, MessageDirection, Channel
        )
        
        if date is None:
            date = timezone.now().date()
        
        # Build query
        query = Q(created_at__date=date)
        if channel:
            query &= Q(channel=channel)
        
        # Calculate metrics
        messages = Message.objects.filter(query)
        
        sent_count = messages.filter(direction=MessageDirection.OUTBOUND).count()
        received_count = messages.filter(direction=MessageDirection.INBOUND).count()
        
        # Calculate response rate (simplified)
        total_outbound = sent_count or 1  # Avoid division by zero
        response_rate = min((received_count / total_outbound) * 100, 100)
        
        # Calculate engagement score (0-100)
        total_messages = sent_count + received_count
        engagement_score = min((total_messages / 10) * 10, 100)  # Scale based on activity
        
        # Active channels count (if tenant-wide)
        active_channels = 1
        if not channel:
            active_channels = Channel.objects.filter(
                messages__created_at__date=date
            ).distinct().count()
        
        # Create or update analytics
        analytics, created = CommunicationAnalytics.objects.update_or_create(
            date=date,
            channel=channel,
            defaults={
                'messages_sent': sent_count,
                'messages_received': received_count,
                'active_channels': active_channels,
                'response_rate': response_rate,
                'engagement_score': engagement_score,
                'metadata': {
                    'total_messages': total_messages,
                    'calculation_time': timezone.now().isoformat()
                }
            }
        )
        
        logger.info(f"{'Created' if created else 'Updated'} analytics for {date} "
                   f"(channel: {channel.id if channel else 'tenant-wide'})")
        
        return analytics
    
    # ============== RecordCommunicationProfile Field Management ==============
    
    def schedule_auto_sync(self, profile):
        """Schedule automatic sync based on frequency settings"""
        from communications.record_communications.tasks import sync_record_communications
        
        if not profile.auto_sync_enabled or profile.sync_frequency_hours == 0:
            return
        
        # Schedule next sync
        next_sync = timezone.now() + timedelta(hours=profile.sync_frequency_hours)
        
        # Use Celery to schedule the task
        sync_record_communications.apply_async(
            args=[str(profile.record_id)],
            eta=next_sync
        )
        
        logger.info(f"Scheduled auto-sync for record {profile.record_id} at {next_sync}")
    
    # ============== RecordCommunicationLink Field Management ==============
    
    def verify_communication_link(self, link):
        """Verify and update communication link"""
        link.last_verified = timezone.now()
        
        # Could add actual verification logic here
        # For now, just update the timestamp
        
        link.save(update_fields=['last_verified'])
        logger.debug(f"Verified communication link {link.id}")
    
    def set_link_creator(self, link, user):
        """Set the user who created the link"""
        link.linked_by = user
        link.save(update_fields=['linked_by'])
    
    # ============== RecordSyncJob Field Management ==============
    
    def set_sync_job_trigger(self, job, user=None, reason: str = None):
        """Set trigger information for sync job"""
        if user:
            job.triggered_by = user
        
        if reason:
            job.trigger_reason = reason[:255]  # Truncate to field length
        
        job.save(update_fields=['triggered_by', 'trigger_reason'])
    
    def update_sync_job_progress(self, job, accounts_synced: int, total_accounts: int):
        """Update sync job progress with account tracking"""
        job.accounts_synced = accounts_synced
        job.total_accounts_to_sync = total_accounts
        
        if total_accounts > 0:
            job.progress_percentage = int((accounts_synced / total_accounts) * 100)
        
        job.save(update_fields=[
            'accounts_synced', 'total_accounts_to_sync', 'progress_percentage'
        ])
        
        logger.debug(f"Updated sync job {job.id}: {accounts_synced}/{total_accounts} accounts")


# Create singleton instance
field_manager = FieldManager()