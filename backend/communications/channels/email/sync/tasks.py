"""
Celery tasks for email synchronization
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from celery import shared_task
from django.db import transaction

from communications.models import (
    Channel, UserChannelConnection, SyncJob, SyncJobStatus, SyncJobType
)
from .comprehensive import EmailComprehensiveSyncService
from .threads import EmailThreadSyncService
from .messages import EmailMessageSyncService
from .folders import EmailFolderSyncService

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='communications.channels.email.sync.run_comprehensive')
def run_email_comprehensive_sync(
    self,
    channel_id: str,
    connection_id: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Run comprehensive email synchronization as a Celery task
    
    Args:
        channel_id: Channel ID to sync
        connection_id: Optional specific connection ID
        options: Sync options dictionary
        
    Returns:
        Sync statistics dictionary
    """
    sync_job = None
    
    try:
        # Get channel and connection
        channel = Channel.objects.get(id=channel_id)
        connection = None
        if connection_id:
            connection = UserChannelConnection.objects.get(id=connection_id)
        
        # Create sync job
        sync_job = SyncJob.objects.create(
            channel=channel,
            connection=connection,
            user_id=connection.user_id if connection else None,
            tenant_id=connection.tenant_id if connection else channel.tenant_id,
            job_type=SyncJobType.COMPREHENSIVE,
            celery_task_id=self.request.id,
            status=SyncJobStatus.RUNNING,
            started_at=timezone.now(),
            parameters=options or {}
        )
        
        logger.info(
            f"Starting comprehensive email sync for channel {channel_id} "
            f"(job_id={sync_job.id}, task_id={self.request.id})"
        )
        
        # Initialize sync service
        sync_service = EmailComprehensiveSyncService(
            channel=channel,
            connection=connection,
            sync_job=sync_job
        )
        
        # Validate sync requirements
        validation = sync_service.validate_sync_requirements()
        if not validation['valid']:
            error_msg = f"Sync validation failed: {', '.join(validation['errors'])}"
            logger.error(error_msg)
            
            sync_job.status = SyncJobStatus.FAILED
            sync_job.completed_at = timezone.now()
            sync_job.error = error_msg
            sync_job.save()
            
            return {
                'success': False,
                'error': error_msg,
                'validation': validation
            }
        
        # Run comprehensive sync
        stats = sync_service.run_comprehensive_sync(options)
        
        # Update sync job with results
        sync_job.completed_at = timezone.now()
        sync_job.status = (
            SyncJobStatus.COMPLETED if not stats.get('errors') 
            else SyncJobStatus.COMPLETED_WITH_ERRORS
        )
        sync_job.result = stats
        sync_job.save()
        
        # Update connection last sync time
        if connection:
            connection.last_sync_at = timezone.now()
            connection.save(update_fields=['last_sync_at'])
        
        logger.info(
            f"Comprehensive email sync completed for channel {channel_id}: "
            f"{stats.get('threads_synced', 0)} threads, "
            f"{stats.get('messages_synced', 0)} messages"
        )
        
        return {
            'success': True,
            'sync_job_id': str(sync_job.id),
            'stats': stats
        }
        
    except Exception as e:
        error_msg = f"Email comprehensive sync failed: {e}"
        logger.error(error_msg, exc_info=True)
        
        if sync_job:
            sync_job.status = SyncJobStatus.FAILED
            sync_job.completed_at = timezone.now()
            sync_job.error = str(e)
            sync_job.save()
        
        return {
            'success': False,
            'error': error_msg
        }


@shared_task(bind=True, name='communications.channels.email.sync.run_incremental')
def run_email_incremental_sync(
    self,
    channel_id: str,
    connection_id: Optional[str] = None,
    since_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run incremental email synchronization as a Celery task
    
    Args:
        channel_id: Channel ID to sync
        connection_id: Optional specific connection ID
        since_date: ISO format date string for incremental sync
        
    Returns:
        Sync statistics dictionary
    """
    sync_job = None
    
    try:
        # Get channel and connection
        channel = Channel.objects.get(id=channel_id)
        connection = None
        if connection_id:
            connection = UserChannelConnection.objects.get(id=connection_id)
        
        # Parse since date
        if since_date:
            since_dt = datetime.fromisoformat(since_date)
        else:
            # Default to last 24 hours for incremental
            since_dt = timezone.now() - timedelta(hours=24)
        
        # Create sync job
        sync_job = SyncJob.objects.create(
            channel=channel,
            connection=connection,
            user_id=connection.user_id if connection else None,
            tenant_id=connection.tenant_id if connection else channel.tenant_id,
            job_type=SyncJobType.INCREMENTAL,
            celery_task_id=self.request.id,
            status=SyncJobStatus.RUNNING,
            started_at=timezone.now(),
            parameters={'since_date': since_dt.isoformat()}
        )
        
        logger.info(
            f"Starting incremental email sync for channel {channel_id} "
            f"since {since_dt} (job_id={sync_job.id})"
        )
        
        # Initialize services
        thread_service = EmailThreadSyncService(
            channel=channel,
            connection=connection
        )
        message_service = EmailMessageSyncService(
            channel=channel,
            connection=connection
        )
        
        stats = {
            'threads_synced': 0,
            'messages_synced': 0,
            'messages_created': 0,
            'messages_updated': 0,
            'errors': [],
            'started_at': timezone.now().isoformat()
        }
        
        # Sync recent threads
        folders_to_sync = ['inbox', 'sent']
        for folder in folders_to_sync:
            try:
                thread_stats = thread_service.sync_email_threads(
                    folder=folder,
                    limit=20,  # Smaller limit for incremental
                    since_date=since_dt
                )
                
                stats['threads_synced'] += thread_stats['threads_synced']
                stats['errors'].extend(thread_stats.get('errors', []))
                
            except Exception as e:
                error_msg = f"Failed to sync threads from {folder}: {e}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
        
        # Sync messages for recent threads
        recent_threads = thread_service.get_threads_for_sync(
            limit=20,
            since_date=since_dt
        )
        
        for conversation in recent_threads:
            try:
                thread_id = conversation.metadata.get('thread_id') or conversation.external_thread_id
                if not thread_id:
                    continue
                
                msg_stats = message_service.sync_messages_for_thread(
                    conversation=conversation,
                    thread_id=thread_id,
                    max_messages=20,  # Smaller limit for incremental
                    since_date=since_dt
                )
                
                stats['messages_synced'] += msg_stats['messages_synced']
                stats['messages_created'] += msg_stats['messages_created']
                stats['messages_updated'] += msg_stats.get('messages_updated', 0)
                stats['errors'].extend(msg_stats.get('errors', []))
                
            except Exception as e:
                error_msg = f"Failed to sync messages for thread {conversation.id}: {e}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
        
        stats['completed_at'] = timezone.now().isoformat()
        
        # Update sync job
        sync_job.completed_at = timezone.now()
        sync_job.status = (
            SyncJobStatus.COMPLETED if not stats['errors'] 
            else SyncJobStatus.COMPLETED_WITH_ERRORS
        )
        sync_job.result = stats
        sync_job.save()
        
        # Update connection last sync time
        if connection:
            connection.last_sync_at = timezone.now()
            connection.save(update_fields=['last_sync_at'])
        
        logger.info(
            f"Incremental email sync completed for channel {channel_id}: "
            f"{stats['threads_synced']} threads, {stats['messages_synced']} messages"
        )
        
        return {
            'success': True,
            'sync_job_id': str(sync_job.id),
            'stats': stats
        }
        
    except Exception as e:
        error_msg = f"Email incremental sync failed: {e}"
        logger.error(error_msg, exc_info=True)
        
        if sync_job:
            sync_job.status = SyncJobStatus.FAILED
            sync_job.completed_at = timezone.now()
            sync_job.error = str(e)
            sync_job.save()
        
        return {
            'success': False,
            'error': error_msg
        }


@shared_task(name='communications.channels.email.sync.sync_single_thread')
def sync_email_thread(
    channel_id: str,
    thread_id: str,
    max_messages: int = 50
) -> Dict[str, Any]:
    """
    Sync a single email thread
    
    Args:
        channel_id: Channel ID
        thread_id: Thread ID to sync
        max_messages: Maximum messages to sync
        
    Returns:
        Sync statistics dictionary
    """
    try:
        channel = Channel.objects.get(id=channel_id)
        
        # Get or create conversation for this thread
        from communications.models import Conversation
        conversation, created = Conversation.objects.get_or_create(
            channel=channel,
            external_thread_id=thread_id,
            defaults={
                'metadata': {'thread_id': thread_id},
                'last_activity_at': timezone.now()
            }
        )
        
        # Initialize message service
        message_service = EmailMessageSyncService(channel=channel)
        
        # Sync messages for this thread
        stats = message_service.sync_messages_for_thread(
            conversation=conversation,
            thread_id=thread_id,
            max_messages=max_messages
        )
        
        logger.info(
            f"Thread sync completed for {thread_id}: "
            f"{stats['messages_synced']} messages"
        )
        
        return {
            'success': True,
            'stats': stats
        }
        
    except Exception as e:
        error_msg = f"Failed to sync thread {thread_id}: {e}"
        logger.error(error_msg, exc_info=True)
        
        return {
            'success': False,
            'error': error_msg
        }


@shared_task(name='communications.channels.email.sync.sync_folders')
def sync_email_folders(channel_id: str) -> Dict[str, Any]:
    """
    Sync email folder structure
    
    Args:
        channel_id: Channel ID
        
    Returns:
        Sync statistics dictionary
    """
    try:
        channel = Channel.objects.get(id=channel_id)
        
        # Initialize folder service
        folder_service = EmailFolderSyncService(channel=channel)
        
        # Sync folders
        stats = folder_service.sync_folders()
        
        logger.info(
            f"Folder sync completed for channel {channel_id}: "
            f"{stats['folders_synced']} folders"
        )
        
        return {
            'success': True,
            'stats': stats
        }
        
    except Exception as e:
        error_msg = f"Failed to sync folders: {e}"
        logger.error(error_msg, exc_info=True)
        
        return {
            'success': False,
            'error': error_msg
        }


@shared_task(name='communications.channels.email.sync.cleanup_old_emails')
def cleanup_old_emails(days_to_keep: int = 90) -> Dict[str, Any]:
    """
    Clean up old email messages
    
    Args:
        days_to_keep: Number of days to keep messages
        
    Returns:
        Cleanup statistics
    """
    try:
        from communications.models import Message
        
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        
        # Find old email messages
        old_messages = Message.objects.filter(
            channel__channel_type__in=['gmail', 'outlook', 'email'],
            created_at__lt=cutoff_date,
            is_deleted=False
        )
        
        count = old_messages.count()
        
        # Soft delete old messages
        old_messages.update(
            is_deleted=True,
            deleted_at=timezone.now()
        )
        
        logger.info(f"Cleaned up {count} old email messages")
        
        return {
            'success': True,
            'messages_deleted': count,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        error_msg = f"Email cleanup failed: {e}"
        logger.error(error_msg, exc_info=True)
        
        return {
            'success': False,
            'error': error_msg
        }