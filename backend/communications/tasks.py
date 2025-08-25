"""
Celery tasks for Communication System
Note: This is a minimal version after legacy code cleanup.
Many tasks have been disabled pending reimplementation.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone as django_timezone
from django_tenants.utils import schema_context

from .models import (
    Channel, Message, Conversation, CommunicationAnalytics, UserChannelConnection
)
from .unipile_sdk import unipile_service
from .message_sync import MessageSyncService

# Initialize service instances
message_sync_service = MessageSyncService()

logger = logging.getLogger(__name__)
User = get_user_model()


# =========================================================================
# PLACEHOLDER TASKS - These need reimplementation
# =========================================================================

@shared_task
def resolve_unconnected_conversations_task(tenant_schema: str):
    """Placeholder: Resolve conversations without contact connections"""
    logger.warning("resolve_unconnected_conversations_task not implemented")
    return {'status': 'not_implemented'}


@shared_task
def resolve_conversation_contact_task(conversation_id: str, contact_id: str):
    """Placeholder: Resolve a specific conversation to a contact"""
    logger.warning("resolve_conversation_contact_task not implemented")
    return {'status': 'not_implemented'}


@shared_task
def mark_chat_read_realtime(chat_id: str, account_id: str):
    """Placeholder: Mark a chat as read in real-time"""
    logger.warning("mark_chat_read_realtime not implemented")
    return {'status': 'not_implemented'}


@shared_task
def fetch_contact_profile_picture(contact_id: str):
    """Placeholder: Fetch contact profile picture"""
    logger.warning("fetch_contact_profile_picture not implemented")
    return {'status': 'not_implemented'}


@shared_task
def process_message_attachment(message_id: str):
    """Placeholder: Process message attachment"""
    logger.warning("process_message_attachment not implemented")
    return {'status': 'not_implemented'}


@shared_task
def sync_conversations_background(connection_id: str, tenant_schema: Optional[str] = None):
    """Placeholder: Background conversation sync"""
    logger.warning("sync_conversations_background not implemented")
    return {'status': 'not_implemented'}


# =========================================================================
# ACTIVE TASKS - These are still functional
# =========================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def sync_whatsapp_messages(
    self,
    account_id: str,
    chat_id: Optional[str] = None,
    limit: int = 50,
    tenant_schema: Optional[str] = None
):
    """
    Sync WhatsApp messages for a specific account and optionally a specific chat
    """
    try:
        logger.info(f"Starting WhatsApp message sync for account {account_id}, chat {chat_id}")
        
        # Use tenant context if provided
        if tenant_schema:
            with schema_context(tenant_schema):
                result = message_sync_service.sync_messages(
                    channel_type='whatsapp',
                    account_id=account_id,
                    conversation_id=chat_id,
                    limit=limit
                )
        else:
            result = message_sync_service.sync_messages(
                channel_type='whatsapp',
                account_id=account_id,
                conversation_id=chat_id,
                limit=limit
            )
        
        logger.info(f"WhatsApp message sync completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"WhatsApp message sync failed: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=300 * (2 ** self.request.retries))
        return {'error': str(e)}


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