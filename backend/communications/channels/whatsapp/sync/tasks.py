"""
Celery Tasks for WhatsApp Synchronization
"""
import logging
from typing import Dict, Any, Optional
from celery import shared_task
from django.db import connection as db_connection
from django.utils import timezone

from communications.models import (
    Channel, UserChannelConnection, SyncJob, SyncJobStatus, SyncJobType,
    Conversation
)
from .comprehensive import ComprehensiveSyncService
from .messages import MessageSyncService
from .utils import SyncJobManager

logger = logging.getLogger(__name__)


def _run_sync_in_context(
    task_self,
    channel_id: str,
    user_id: str,
    sync_options: Optional[Dict[str, Any]],
    task_id: str
) -> Dict[str, Any]:
    """Helper method to run sync within tenant context"""
    sync_job = None
    
    try:
        # Get channel and connection
        channel, connection = _get_channel_and_connection(channel_id, user_id)
        
        if not channel:
            error_msg = f"Channel not found for ID: {channel_id}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        # IMPORTANT: Apply config defaults here to ensure they're used
        from .config import get_sync_options
        corrected_sync_options = get_sync_options(sync_options)
        logger.info(f"📊 Using sync options: {corrected_sync_options}")
        
        # Create sync job with corrected options
        sync_job = SyncJobManager.create_sync_job(
            channel_id=channel.id,
            user_id=user_id,
            sync_type=SyncJobType.COMPREHENSIVE,
            options=corrected_sync_options,
            task_id=task_id
        )
        
        logger.debug(f"  Created sync job: {sync_job.id}")
        
        # Run comprehensive sync
        sync_service = ComprehensiveSyncService(
            channel=channel,
            connection=connection,
            sync_job=sync_job
        )
        
        # Validate before starting
        validation = sync_service.validate_sync_requirements()
        if not validation['valid']:
            error_msg = f"Validation failed: {', '.join(validation['errors'])}"
            if sync_job:
                SyncJobManager.mark_sync_job_failed(str(sync_job.id), error_msg)
            return {'success': False, 'error': error_msg, 'validation': validation}
        
        # Run the sync with corrected options
        stats = sync_service.run_comprehensive_sync(corrected_sync_options)
        
        logger.info(f"✅ Background sync completed: {stats}")
        
        return {
            'success': True,
            'sync_job_id': str(sync_job.id) if sync_job else None,
            'stats': stats
        }
        
    except Exception as e:
        error_msg = f"Background sync failed: {str(e)}"
        logger.error(f"❌ {error_msg}", exc_info=True)
        
        if sync_job:
            SyncJobManager.mark_sync_job_failed(str(sync_job.id), error_msg)
        
        # Retry if possible
        if hasattr(task_self, 'retry'):
            raise task_self.retry(exc=e, countdown=60)
        
        return {
            'success': False,
            'error': error_msg
        }


@shared_task(bind=True, max_retries=3)
def sync_account_comprehensive_background(
    self,
    channel_id: str,
    user_id: str,
    sync_options: Optional[Dict[str, Any]] = None,
    tenant_schema: Optional[str] = None
) -> Dict[str, Any]:
    """
    Background task for comprehensive WhatsApp account sync
    
    Args:
        channel_id: Channel ID or UniPile account ID
        user_id: User ID who initiated the sync
        sync_options: Optional sync configuration
        tenant_schema: Tenant schema name for multi-tenancy
        
    Returns:
        Sync statistics dictionary
    """
    sync_job = None
    
    try:
        # Capture task ID
        task_id = self.request.id
        logger.debug(f"🎯 Starting background sync task {task_id}")
        
        # Switch to tenant schema if provided
        if tenant_schema:
            from django_tenants.utils import schema_context
            logger.debug(f"  Processing sync in tenant: {tenant_schema}")
            # Use schema_context for the entire operation
            with schema_context(tenant_schema):
                return _run_sync_in_context(
                    self, channel_id, user_id, sync_options, task_id
                )
        
        # If no tenant schema, run without context (shouldn't happen in production)
        return _run_sync_in_context(
            self, channel_id, user_id, sync_options, task_id
        )
        
    except Exception as e:
        error_msg = f"Background sync failed: {e}"
        logger.error(error_msg, exc_info=True)
        
        # Mark job as failed
        if sync_job:
            SyncJobManager.mark_sync_job_failed(str(sync_job.id), error_msg)
        
        # Retry if retries available
        if self.request.retries < self.max_retries:
            logger.debug(f"Retrying task (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        
        return {
            'success': False,
            'error': error_msg,
            'sync_job_id': str(sync_job.id) if sync_job else None
        }


@shared_task(bind=True, max_retries=3)
def sync_chat_specific_background(
    self,
    channel_id: str,
    chat_id: str,
    user_id: str,
    sync_options: Optional[Dict[str, Any]] = None,
    tenant_schema: Optional[str] = None
) -> Dict[str, Any]:
    """
    Background task for syncing a specific WhatsApp chat
    
    Args:
        channel_id: Channel ID
        chat_id: Chat/Conversation external ID
        user_id: User ID who initiated the sync
        sync_options: Optional sync configuration
        tenant_schema: Tenant schema name
        
    Returns:
        Sync statistics dictionary
    """
    sync_job = None
    
    try:
        # Capture task ID
        task_id = self.request.id
        logger.info(f"🎯 Starting chat-specific sync task {task_id} for chat {chat_id}")
        
        # Ensure sync_options has config values (no fallbacks)
        from .config import get_sync_options
        sync_options = get_sync_options(sync_options)
        
        # Define the actual sync logic
        def run_chat_sync():
            nonlocal sync_job
            
            # Get channel and connection
            channel, connection = _get_channel_and_connection(channel_id, user_id)
            
            if not channel:
                error_msg = f"Channel not found for ID: {channel_id}"
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            # Get or create conversation
            conversation = Conversation.objects.filter(
                external_thread_id=chat_id,
                channel=channel
            ).first()
            
            if not conversation:
                error_msg = f"Conversation not found for chat ID: {chat_id}"
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            # Create sync job
            sync_job = SyncJobManager.create_sync_job(
                channel_id=channel.id,
                user_id=user_id,
                sync_type=SyncJobType.CHAT_SPECIFIC,
                options={
                    'chat_id': chat_id,
                    **(sync_options or {})
                },
                task_id=task_id
            )
            
            # Initialize message sync service with progress tracker
            from .utils import SyncProgressTracker
            progress_tracker = SyncProgressTracker(sync_job)
            
            message_service = MessageSyncService(
                channel=channel,
                connection=connection,
                progress_tracker=progress_tracker
            )
            
            # Sync messages for the specific conversation
            # Get max_messages from sync_options (which must be provided by config)
            max_messages = sync_options['max_messages_per_chat']  # No fallback, use config
            stats = message_service.sync_messages_for_conversation(
                conversation,
                max_messages=max_messages
            )
            
            # Update sync job
            if sync_job:
                SyncJobManager.update_sync_job(
                    sync_job,
                    status=SyncJobStatus.COMPLETED,
                    stats=stats
                )
            
            # Update conversation sync timestamp
            conversation.last_synced_at = timezone.now()
            conversation.save(update_fields=['last_synced_at'])
            
            logger.info(f"✅ Chat-specific sync completed: {stats}")
            
            return {
                'success': True,
                'sync_job_id': str(sync_job.id) if sync_job else None,
                'stats': stats
            }
        
        # Switch to tenant schema if provided
        if tenant_schema:
            from django_tenants.utils import schema_context
            logger.info(f"  Processing chat sync in tenant: {tenant_schema}")
            with schema_context(tenant_schema):
                return run_chat_sync()
        else:
            return run_chat_sync()
        
    except Exception as e:
        error_msg = f"Chat-specific sync failed: {e}"
        logger.error(error_msg, exc_info=True)
        
        # Mark job as failed
        if sync_job:
            SyncJobManager.mark_sync_job_failed(str(sync_job.id), error_msg)
        
        # Retry if retries available
        if self.request.retries < self.max_retries:
            logger.debug(f"Retrying task (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=30 * (self.request.retries + 1))
        
        return {
            'success': False,
            'error': error_msg,
            'sync_job_id': str(sync_job.id) if sync_job else None
        }


@shared_task
def cleanup_old_sync_jobs(days_to_keep: int = 30) -> Dict[str, Any]:
    """
    Cleanup old sync jobs
    
    Args:
        days_to_keep: Number of days to keep sync jobs
        
    Returns:
        Cleanup statistics
    """
    try:
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        
        # Delete old sync jobs
        deleted_count, _ = SyncJob.objects.filter(
            created_at__lt=cutoff_date
        ).delete()
        
        logger.info(f"Cleaned up {deleted_count} old sync jobs")
        
        return {
            'success': True,
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }


# Helper functions

def _get_channel_and_connection(
    channel_id: str,
    user_id: str
) -> tuple[Optional[Channel], Optional[UserChannelConnection]]:
    """
    Get channel and connection objects
    
    Args:
        channel_id: Channel ID or UniPile account ID
        user_id: User ID
        
    Returns:
        Tuple of (Channel, UserChannelConnection) or (None, None)
    """
    try:
        # Try to get by channel ID first
        channel = Channel.objects.filter(id=channel_id).first()
        
        # If not found, try by UniPile account ID
        if not channel:
            channel = Channel.objects.filter(
                unipile_account_id=channel_id,
                channel_type='whatsapp'
            ).first()
        
        # Get connection
        connection = None
        if channel:
            connection = UserChannelConnection.objects.filter(
                user_id=user_id,
                channel_type='whatsapp',
                is_active=True
            ).first()
            
            # If no connection by user, try by UniPile account ID
            if not connection:
                connection = UserChannelConnection.objects.filter(
                    unipile_account_id=channel_id,
                    channel_type='whatsapp',
                    is_active=True
                ).first()
        
        return channel, connection
        
    except Exception as e:
        logger.error(f"Failed to get channel and connection: {e}")
        return None, None