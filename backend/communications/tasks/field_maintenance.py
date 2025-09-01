"""
Celery tasks for field maintenance and analytics generation
"""
import logging
from datetime import datetime, timedelta
from celery import shared_task
from django.utils import timezone
from django.db.models import Count, F, Q

logger = logging.getLogger(__name__)


@shared_task
def generate_daily_analytics():
    """Generate daily analytics for all communication channels"""
    from communications.services.field_manager import field_manager
    from communications.models import Channel
    
    try:
        today = timezone.now().date()
        
        # Generate tenant-wide analytics
        field_manager.create_daily_analytics(today, channel=None)
        
        # Generate per-channel analytics
        for channel in Channel.objects.filter(is_active=True):
            field_manager.create_daily_analytics(today, channel=channel)
        
        logger.info(f"Successfully generated daily analytics for {today}")
        return {'status': 'success', 'date': str(today)}
        
    except Exception as e:
        logger.error(f"Failed to generate daily analytics: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def update_participant_statistics():
    """Update statistics for all active participants"""
    from communications.models import Participant
    from communications.services.field_manager import field_manager
    
    try:
        # Get participants active in the last 7 days
        cutoff_date = timezone.now() - timedelta(days=7)
        active_participants = Participant.objects.filter(
            last_seen__gte=cutoff_date
        )
        
        updated_count = 0
        for participant in active_participants:
            field_manager.update_participant_stats(participant)
            updated_count += 1
        
        logger.info(f"Updated statistics for {updated_count} participants")
        return {'status': 'success', 'updated': updated_count}
        
    except Exception as e:
        logger.error(f"Failed to update participant statistics: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def update_channel_statistics():
    """Update message counts and last message times for all channels"""
    from communications.models import Channel
    from communications.services.field_manager import field_manager
    
    try:
        channels = Channel.objects.filter(is_active=True)
        
        updated_count = 0
        for channel in channels:
            field_manager.update_channel_stats(channel)
            updated_count += 1
        
        logger.info(f"Updated statistics for {updated_count} channels")
        return {'status': 'success', 'updated': updated_count}
        
    except Exception as e:
        logger.error(f"Failed to update channel statistics: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def detect_hot_conversations():
    """Identify and mark frequently accessed conversations as hot"""
    from communications.models import Conversation
    from communications.services.field_manager import field_manager
    
    try:
        # Find conversations with high activity in the last 24 hours
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        # Conversations with 10+ messages in last 24 hours
        hot_conversations = Conversation.objects.annotate(
            recent_messages=Count(
                'messages',
                filter=Q(messages__created_at__gte=cutoff_time)
            )
        ).filter(recent_messages__gte=10)
        
        marked_count = 0
        for conversation in hot_conversations:
            field_manager.mark_conversation_hot(conversation, True)
            marked_count += 1
        
        # Unmark old hot conversations
        old_hot = Conversation.objects.filter(
            is_hot=True,
            last_accessed_at__lt=cutoff_time
        )
        
        unmarked_count = 0
        for conversation in old_hot:
            field_manager.mark_conversation_hot(conversation, False)
            unmarked_count += 1
        
        logger.info(f"Marked {marked_count} hot conversations, unmarked {unmarked_count}")
        return {
            'status': 'success',
            'marked': marked_count,
            'unmarked': unmarked_count
        }
        
    except Exception as e:
        logger.error(f"Failed to detect hot conversations: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def cleanup_expired_tokens():
    """Clean up expired authentication tokens"""
    from communications.models import UserChannelConnection
    
    try:
        now = timezone.now()
        expired_connections = UserChannelConnection.objects.filter(
            token_expires_at__lt=now,
            account_status='active'
        )
        
        updated_count = 0
        for connection in expired_connections:
            connection.account_status = 'expired'
            connection.save(update_fields=['account_status'])
            updated_count += 1
        
        logger.info(f"Marked {updated_count} connections as expired")
        return {'status': 'success', 'expired': updated_count}
        
    except Exception as e:
        logger.error(f"Failed to cleanup expired tokens: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def process_scheduled_syncs():
    """Process scheduled auto-syncs for records across all tenants"""
    from communications.record_communications.models import RecordCommunicationProfile
    from communications.record_communications.tasks import sync_record_communications
    from tenants.models import Tenant
    from django_tenants.utils import schema_context
    
    try:
        now = timezone.now()
        total_scheduled = 0
        
        # Process each tenant separately
        for tenant in Tenant.objects.exclude(schema_name='public'):
            with schema_context(tenant.schema_name):
                # Find profiles due for sync in this tenant
                profiles = RecordCommunicationProfile.objects.filter(
                    auto_sync_enabled=True,
                    sync_frequency_hours__gt=0,
                    sync_in_progress=False
                ).exclude(
                    last_full_sync__gte=now - timedelta(hours=F('sync_frequency_hours'))
                )
                
                scheduled_count = 0
                for profile in profiles[:10]:  # Limit to 10 per tenant per run
                    # Schedule the sync task with tenant schema
                    sync_record_communications.delay(
                        record_id=profile.record_id,
                        tenant_schema=tenant.schema_name,
                        trigger_reason='Scheduled periodic sync'
                    )
                    
                    # Mark as in progress
                    profile.mark_sync_started()
                    scheduled_count += 1
                
                if scheduled_count > 0:
                    logger.info(f"Scheduled {scheduled_count} record syncs in tenant {tenant.schema_name}")
                total_scheduled += scheduled_count
        
        logger.info(f"Total scheduled syncs across all tenants: {total_scheduled}")
        return {'status': 'success', 'scheduled': total_scheduled}
        
    except Exception as e:
        logger.error(f"Failed to process scheduled syncs: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def verify_communication_links():
    """Verify and update communication link timestamps"""
    from communications.record_communications.models import RecordCommunicationLink
    from communications.services.field_manager import field_manager
    
    try:
        # Get links that haven't been verified in 7 days
        cutoff_date = timezone.now() - timedelta(days=7)
        
        unverified_links = RecordCommunicationLink.objects.filter(
            Q(last_verified__lt=cutoff_date) | Q(last_verified__isnull=True)
        )[:100]  # Process 100 at a time
        
        verified_count = 0
        for link in unverified_links:
            field_manager.verify_communication_link(link)
            verified_count += 1
        
        logger.info(f"Verified {verified_count} communication links")
        return {'status': 'success', 'verified': verified_count}
        
    except Exception as e:
        logger.error(f"Failed to verify communication links: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def update_conversation_types():
    """Update conversation types based on participant count"""
    from communications.models import Conversation
    from communications.services.field_manager import field_manager
    
    try:
        # Get conversations with potentially incorrect types
        conversations = Conversation.objects.filter(
            conversation_type='direct'
        ).annotate(
            active_participants=Count(
                'conversation_participants',
                filter=Q(conversation_participants__is_active=True)
            )
        ).filter(active_participants__gt=2)
        
        updated_count = 0
        for conversation in conversations:
            field_manager.detect_conversation_type(
                conversation,
                conversation.active_participants
            )
            updated_count += 1
        
        logger.info(f"Updated {updated_count} conversation types")
        return {'status': 'success', 'updated': updated_count}
        
    except Exception as e:
        logger.error(f"Failed to update conversation types: {e}")
        return {'status': 'error', 'error': str(e)}