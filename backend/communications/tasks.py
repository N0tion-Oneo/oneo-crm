"""
Celery tasks for Communication System
Record-first sync implementation
"""
import logging
from typing import Optional
from datetime import timedelta

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone as django_timezone
from django_tenants.utils import schema_context

from .models import Message, CommunicationAnalytics

# Import record communication tasks to ensure they're discovered
# Note: tasks.py re-exports from sync_tasks.py for proper autodiscovery
from .record_communications.tasks import (
    sync_record_communications,
    process_webhook_message_task,
    sync_all_records_for_pipeline,
    cleanup_old_sync_jobs,
    check_stale_profiles
)

logger = logging.getLogger(__name__)
User = get_user_model()


# =========================================================================
# EMAIL SYNC TASKS  
# =========================================================================

@shared_task(bind=True, max_retries=2)
def sync_email_read_status_to_provider(
    self,
    message_id: int,
    tenant_schema: str,
    mark_as_read: bool = True
):
    """
    Sync email read status to the email provider (Gmail/Outlook) via UniPile
    
    Args:
        message_id: The message ID in our database
        tenant_schema: The tenant schema to use
        mark_as_read: True to mark as read, False to mark as unread
    """
    try:
        with schema_context(tenant_schema):
            from .models import Message
            from .channels.email.service import EmailService
            import asyncio
            
            message = Message.objects.get(id=message_id)
            
            # Get the UniPile email ID from metadata
            unipile_email_id = message.metadata.get('unipile_id') if message.metadata else None
            
            # Only sync if it's an email with a UniPile ID
            if not (message.channel and message.channel.channel_type in ['email', 'gmail', 'outlook', 'office365'] and unipile_email_id):
                logger.info(f"Message {message_id} is not an email (type: {message.channel.channel_type if message.channel else 'None'}) or has no UniPile ID in metadata, skipping sync")
                return
            
            # Get the account_id from the channel
            account_id = None
            if message.channel and hasattr(message.channel, 'unipile_account_id'):
                account_id = message.channel.unipile_account_id
                logger.info(f"Using UniPile account_id: {account_id} for message {message_id}")
            else:
                logger.warning(f"No UniPile account_id found for channel {message.channel.id if message.channel else 'None'}, message {message_id}")
            
            # Run the async method
            email_service = EmailService()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    email_service.mark_email_as_read(
                        email_id=unipile_email_id,
                        account_id=account_id,
                        mark_as_read=mark_as_read
                    )
                )
                
                if result.get('success'):
                    logger.info(f"Successfully synced read status for message {message_id} to UniPile")
                else:
                    logger.warning(f"Failed to sync read status for message {message_id}: {result}")
                    
                return result
            finally:
                loop.close()
                
    except Message.DoesNotExist:
        logger.error(f"Message {message_id} not found")
    except Exception as e:
        logger.error(f"Error syncing read status for message {message_id}: {e}")
        raise self.retry(exc=e)


# =========================================================================
# UTILITY TASKS
# =========================================================================


@shared_task(bind=True, max_retries=2)
def cleanup_old_messages(
    self,
    days_to_keep: int = 90,
    tenant_schema: Optional[str] = None
):
    """
    Clean up old messages beyond retention period
    """
    try:
        cutoff_date = django_timezone.now() - timedelta(days=days_to_keep)
        
        if tenant_schema:
            with schema_context(tenant_schema):
                deleted_count = Message.objects.filter(
                    created_at__lt=cutoff_date
                ).delete()[0]
        else:
            deleted_count = Message.objects.filter(
                created_at__lt=cutoff_date
            ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old messages")
        return {'deleted_count': deleted_count}
        
    except Exception as e:
        logger.error(f"Message cleanup failed: {e}")
        return {'error': str(e)}


@shared_task
def update_communication_analytics(tenant_schema: Optional[str] = None):
    """
    Update communication analytics for the tenant
    """
    try:
        if tenant_schema:
            with schema_context(tenant_schema):
                # Get message counts by channel
                from django.db.models import Count
                stats = Message.objects.values('channel__channel_type').annotate(
                    count=Count('id')
                )
                
                analytics, created = CommunicationAnalytics.objects.get_or_create(
                    defaults={'metrics': {}}
                )
                
                analytics.metrics['message_counts'] = {
                    stat['channel__channel_type']: stat['count']
                    for stat in stats
                }
                analytics.metrics['last_updated'] = django_timezone.now().isoformat()
                analytics.save()
                
                return {'status': 'success', 'metrics': analytics.metrics}
        else:
            logger.warning("No tenant schema provided for analytics update")
            return {'status': 'skipped', 'reason': 'no_tenant_schema'}
            
    except Exception as e:
        logger.error(f"Analytics update failed: {e}")
        return {'error': str(e)}