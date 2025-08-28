"""
Comprehensive Email Synchronization Service
Orchestrates full email data synchronization
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction

from communications.models import (
    Channel, UserChannelConnection, SyncJob, SyncJobStatus, SyncJobType
)
from .config import get_sync_options, EMAIL_SYNC_CONFIG
from .folders import EmailFolderSyncService
from .threads import EmailThreadSyncService
from .messages import EmailMessageSyncService

logger = logging.getLogger(__name__)


class EmailComprehensiveSyncService:
    """Orchestrates comprehensive email synchronization"""
    
    def __init__(
        self,
        channel: Channel,
        connection: Optional[UserChannelConnection] = None,
        sync_job: Optional[SyncJob] = None
    ):
        self.channel = channel
        self.connection = connection
        self.sync_job = sync_job
        
        # Initialize progress tracker
        self.progress_tracker = EmailSyncProgressTracker(sync_job) if sync_job else None
        
        # Initialize sync services
        self.folder_service = EmailFolderSyncService(
            channel=channel,
            connection=connection,
            progress_tracker=self.progress_tracker
        )
        self.thread_service = EmailThreadSyncService(
            channel=channel,
            connection=connection,
            progress_tracker=self.progress_tracker
        )
        self.message_service = EmailMessageSyncService(
            channel=channel,
            connection=connection,
            progress_tracker=self.progress_tracker
        )
    
    def run_comprehensive_sync(
        self,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run a comprehensive sync of all email data
        
        Args:
            options: Sync options dictionary
                - max_threads: Number of email threads to sync (default: 100)
                - max_messages_per_thread: Messages per thread (default: 50)
                - days_back: Days to look back for messages (default: 30)
                - folders_to_sync: List of folders to sync (default: ['inbox', 'sent', 'drafts'])
            
        Returns:
            Statistics dictionary
        """
        # Get sync options
        sync_options = get_sync_options(options)
        
        # Broadcast sync start
        if self.progress_tracker and self.sync_job:
            self._broadcast_sync_start()
        
        stats = {
            'folders_synced': 0,
            'threads_synced': 0,
            'messages_synced': 0,
            'threads_created': 0,
            'messages_created': 0,
            'errors': [],
            'started_at': timezone.now().isoformat(),
            'completed_at': None
        }
        
        try:
            # Phase 1: Sync folder structure
            logger.info("📁 Phase 1: Syncing email folders...")
            folder_stats = self._sync_folders_phase()
            stats['folders_synced'] = folder_stats['folders_synced']
            stats['errors'].extend(folder_stats.get('errors', []))
            
            # Phase 2: Sync email threads
            logger.info("📧 Phase 2: Syncing email threads...")
            thread_stats = self._sync_threads_phase(sync_options)
            stats['threads_synced'] = thread_stats['threads_synced']
            stats['threads_created'] = thread_stats['threads_created']
            stats['errors'].extend(thread_stats.get('errors', []))
            
            # Phase 3: Sync messages for each thread
            logger.info("💬 Phase 3: Syncing email messages...")
            msg_stats = self._sync_messages_phase(sync_options)
            stats['messages_synced'] = msg_stats['messages_synced']
            stats['messages_created'] = msg_stats['messages_created']
            stats['errors'].extend(msg_stats.get('errors', []))
            
            # Phase 4: Final cleanup and optimization
            self._cleanup_phase()
            
            stats['completed_at'] = timezone.now().isoformat()
            
            # Finalize progress tracking
            if self.progress_tracker:
                self.progress_tracker.finalize(
                    status=SyncJobStatus.COMPLETED if not stats['errors'] else SyncJobStatus.COMPLETED_WITH_ERRORS
                )
            
            logger.info(
                f"✅ Email sync complete: {stats['folders_synced']} folders, "
                f"{stats['threads_synced']} threads, {stats['messages_synced']} messages"
            )
            
        except Exception as e:
            error_msg = f"Comprehensive email sync failed: {e}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
            stats['completed_at'] = timezone.now().isoformat()
            
            # Mark job as failed
            if self.progress_tracker:
                self.progress_tracker.add_error(error_msg)
                self.progress_tracker.finalize(status=SyncJobStatus.FAILED)
        
        return stats
    
    def _sync_folders_phase(self) -> Dict[str, Any]:
        """Phase 1: Sync email folders"""
        logger.info(f"📁 Starting folder sync phase for channel {self.channel.id}")
        
        # Sync folders
        folder_stats = self.folder_service.sync_folders()
        
        # Update progress
        if self.progress_tracker:
            self.progress_tracker.update_progress(
                current=folder_stats['folders_synced'],
                total=folder_stats['folders_synced'],
                phase='folders',
                details={'folders': folder_stats.get('folders', [])}
            )
        
        return folder_stats
    
    def _sync_threads_phase(self, sync_options: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 2: Sync email threads"""
        max_threads = sync_options['max_threads']
        days_back = sync_options.get('days_back', 30)
        folders_to_sync = sync_options.get('folders_to_sync', ['inbox', 'sent', 'drafts'])
        
        since_date = None
        if days_back and days_back > 0:
            since_date = timezone.now() - timedelta(days=days_back)
        
        logger.info(
            f"📧 Starting thread sync phase (max={max_threads}, "
            f"folders={folders_to_sync}) for channel {self.channel.id}"
        )
        
        total_stats = {
            'threads_synced': 0,
            'threads_created': 0,
            'threads_updated': 0,
            'errors': []
        }
        
        # Sync threads from each folder
        threads_per_folder = max_threads // len(folders_to_sync) if folders_to_sync else max_threads
        
        for folder in folders_to_sync:
            try:
                logger.info(f"Syncing threads from folder: {folder}")
                thread_stats = self.thread_service.sync_email_threads(
                    folder=folder,
                    limit=threads_per_folder,
                    since_date=since_date
                )
                
                total_stats['threads_synced'] += thread_stats['threads_synced']
                total_stats['threads_created'] += thread_stats['threads_created']
                total_stats['threads_updated'] += thread_stats.get('threads_updated', 0)
                total_stats['errors'].extend(thread_stats.get('errors', []))
                
            except Exception as e:
                error_msg = f"Failed to sync threads from folder {folder}: {e}"
                logger.error(error_msg)
                total_stats['errors'].append(error_msg)
        
        return total_stats
    
    def _sync_messages_phase(self, sync_options: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 3: Sync messages for threads"""
        max_messages_per_thread = sync_options['max_messages_per_thread']
        days_back = sync_options.get('days_back', 30)
        
        since_date = None
        if days_back and days_back > 0:
            since_date = timezone.now() - timedelta(days=days_back)
        
        # Get threads to sync messages for
        threads = self.thread_service.get_threads_for_sync(limit=sync_options['max_threads'])
        
        logger.info(f"📨 Starting messages sync phase ({len(threads)} threads)")
        
        total_stats = {
            'messages_synced': 0,
            'messages_created': 0,
            'messages_updated': 0,
            'errors': []
        }
        
        for idx, conversation in enumerate(threads):
            try:
                # Get thread ID from conversation metadata
                thread_id = conversation.metadata.get('thread_id') or conversation.external_thread_id
                
                if not thread_id:
                    logger.warning(f"No thread ID for conversation {conversation.id}")
                    continue
                
                # Sync messages for this thread
                msg_stats = self.message_service.sync_messages_for_thread(
                    conversation=conversation,
                    thread_id=thread_id,
                    max_messages=max_messages_per_thread,
                    since_date=since_date
                )
                
                # Update totals
                total_stats['messages_synced'] += msg_stats['messages_synced']
                total_stats['messages_created'] += msg_stats['messages_created']
                total_stats['messages_updated'] += msg_stats.get('messages_updated', 0)
                total_stats['errors'].extend(msg_stats.get('errors', []))
                
                # Update conversation sync timestamp
                conversation.last_synced_at = timezone.now()
                conversation.save(update_fields=['last_synced_at'])
                
                logger.debug(
                    f"Processed thread {idx + 1}/{len(threads)}: "
                    f"{msg_stats['messages_synced']} messages"
                )
                
            except Exception as e:
                error_msg = f"Failed to sync messages for thread {conversation.id}: {e}"
                logger.error(error_msg)
                total_stats['errors'].append(error_msg)
        
        return total_stats
    
    def _cleanup_phase(self) -> None:
        """Phase 4: Cleanup and optimization"""
        try:
            # Update channel sync metadata
            if self.channel:
                if not self.channel.sync_settings:
                    self.channel.sync_settings = {}
                
                self.channel.sync_settings['last_comprehensive_sync'] = {
                    'timestamp': timezone.now().isoformat(),
                    'stats': self.progress_tracker.get_stats() if self.progress_tracker else {}
                }
                self.channel.save(update_fields=['sync_settings'])
            
            # Update connection sync timestamp
            if self.connection:
                UserChannelConnection.objects.filter(pk=self.connection.pk).update(
                    last_sync_at=timezone.now()
                )
            
            logger.debug("Cleanup phase completed")
            
        except Exception as e:
            logger.error(f"Cleanup phase failed: {e}")
    
    def _broadcast_sync_start(self) -> None:
        """Broadcast sync start event"""
        from communications.sync import get_sync_broadcaster
        
        broadcaster = get_sync_broadcaster('email')
        broadcaster.broadcast_job_update(
            sync_job_id=str(self.sync_job.id),
            celery_task_id=self.sync_job.celery_task_id,
            user_id=str(self.sync_job.user_id),
            status='running'
        )
        
        # Broadcast initial progress
        initial_progress = {
            'current_phase': 'initializing',
            'folders_synced': 0,
            'threads_processed': 0,
            'messages_processed': 0,
        }
        broadcaster.broadcast_progress(
            sync_job_id=str(self.sync_job.id),
            celery_task_id=self.sync_job.celery_task_id,
            user_id=str(self.sync_job.user_id),
            progress_data=initial_progress,
            force=True
        )
    
    def validate_sync_requirements(self) -> Dict[str, Any]:
        """
        Validate that sync can proceed
        
        Returns:
            Validation result dictionary
        """
        validation = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check channel
        if not self.channel:
            validation['valid'] = False
            validation['errors'].append("No channel configured")
        
        # Check connection
        if self.connection:
            if not self.connection.is_active:
                validation['warnings'].append("Connection is not active")
            
            if not self.connection.unipile_account_id:
                validation['valid'] = False
                validation['errors'].append("No UniPile account ID configured")
        else:
            validation['warnings'].append("No connection configured")
        
        # Check for existing sync job
        if self.sync_job:
            if self.sync_job.status == SyncJobStatus.RUNNING:
                validation['warnings'].append("Sync job already in progress")
        
        return validation


class EmailSyncProgressTracker:
    """Tracks email sync progress"""
    
    def __init__(self, sync_job: Optional[SyncJob] = None):
        self.sync_job = sync_job
        self.stats = {
            'folders_synced': 0,
            'threads_synced': 0,
            'messages_synced': 0,
            'errors': []
        }
        self.broadcaster = None
        
        if sync_job:
            from communications.sync import get_sync_broadcaster
            self.broadcaster = get_sync_broadcaster('email')
    
    def increment_stat(self, stat_name: str, count: int = 1) -> None:
        """Increment a statistic counter"""
        if stat_name in self.stats and isinstance(self.stats[stat_name], (int, float)):
            self.stats[stat_name] += count
            
            # Broadcast the updated stats
            if self.broadcaster and self.sync_job:
                progress_data = {
                    'current_phase': self._get_current_phase(),
                    'folders_synced': self.stats.get('folders_synced', 0),
                    'threads_processed': self.stats.get('threads_synced', 0),
                    'messages_processed': self.stats.get('messages_synced', 0),
                }
                
                self.broadcaster.broadcast_progress(
                    sync_job_id=str(self.sync_job.id),
                    celery_task_id=self.sync_job.celery_task_id,
                    user_id=str(self.sync_job.user_id),
                    progress_data=progress_data,
                    force=True
                )
    
    def update_progress(
        self,
        current: int,
        total: int,
        phase: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update progress for a specific phase"""
        if self.broadcaster and self.sync_job:
            progress_data = {
                'current_phase': phase,
                'current': current,
                'total': total,
                'details': details or {},
                **self.stats
            }
            
            self.broadcaster.broadcast_progress(
                sync_job_id=str(self.sync_job.id),
                celery_task_id=self.sync_job.celery_task_id,
                user_id=str(self.sync_job.user_id),
                progress_data=progress_data
            )
    
    def add_error(self, error: str) -> None:
        """Add an error to the tracker"""
        self.stats['errors'].append(error)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        return self.stats.copy()
    
    def finalize(self, status: SyncJobStatus) -> None:
        """Finalize the sync job"""
        if self.sync_job:
            self.sync_job.status = status
            self.sync_job.completed_at = timezone.now()
            self.sync_job.result = self.stats
            self.sync_job.save()
            
            # Broadcast final status
            if self.broadcaster:
                self.broadcaster.broadcast_job_update(
                    sync_job_id=str(self.sync_job.id),
                    celery_task_id=self.sync_job.celery_task_id,
                    user_id=str(self.sync_job.user_id),
                    status=status.value
                )
    
    def _get_current_phase(self) -> str:
        """Determine current phase based on stats"""
        if self.stats['messages_synced'] > 0:
            return 'messages'
        elif self.stats['threads_synced'] > 0:
            return 'threads'
        elif self.stats['folders_synced'] > 0:
            return 'folders'
        return 'initializing'