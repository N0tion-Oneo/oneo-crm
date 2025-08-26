"""
Sync Utilities and Helper Classes
"""
import logging
from typing import Dict, Any, Optional
from django.utils import timezone
from django.db import transaction
from communications.models import (
    SyncJob, SyncJobProgress, SyncJobStatus, SyncJobType
)
from communications.sync import get_sync_broadcaster

logger = logging.getLogger(__name__)


class SyncJobManager:
    """Manages sync job lifecycle"""
    
    @staticmethod
    def create_sync_job(
        channel_id: str,
        user_id: str,
        sync_type: str,
        options: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> SyncJob:
        """Create a new sync job"""
        sync_job = SyncJob.objects.create(
            channel_id=channel_id,
            user_id=user_id,
            job_type=sync_type,
            status=SyncJobStatus.RUNNING,
            celery_task_id=task_id or 'manual_sync',
            sync_options=options
        )
        sync_job.started_at = timezone.now()
        sync_job.save(update_fields=['started_at'])
        return sync_job
    
    @staticmethod
    def update_sync_job(
        sync_job: SyncJob,
        status: Optional[str] = None,
        stats: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> None:
        """Update sync job status and stats"""
        if status:
            sync_job.status = status
        
        if stats:
            sync_job.result_summary = stats
        
        if error:
            if not sync_job.error_details:
                sync_job.error_details = []
            sync_job.error_details.append({
                'error': error,
                'timestamp': timezone.now().isoformat()
            })
            sync_job.error_count = len(sync_job.error_details)
            sync_job.status = SyncJobStatus.FAILED
        
        if status in [SyncJobStatus.COMPLETED, SyncJobStatus.FAILED]:
            sync_job.completed_at = timezone.now()
        
        sync_job.save()
    
    @staticmethod
    def mark_sync_job_failed(sync_job_id: str, error_message: str) -> None:
        """Mark a sync job as failed"""
        try:
            sync_job = SyncJob.objects.get(id=sync_job_id)
            SyncJobManager.update_sync_job(
                sync_job, 
                status=SyncJobStatus.FAILED,
                error=error_message
            )
        except SyncJob.DoesNotExist:
            logger.error(f"Sync job {sync_job_id} not found")


class SyncProgressTracker:
    """Tracks and reports sync progress"""
    
    def __init__(self, sync_job: Optional[SyncJob] = None, provider_type: str = 'whatsapp'):
        self.sync_job = sync_job
        self.provider_type = provider_type
        self.stats = {
            'conversations_synced': 0,
            'messages_synced': 0,
            'attendees_synced': 0,
            'errors': []
        }
        # Track last update to throttle database writes
        self.last_db_update = None
        self.update_frequency_seconds = 5  # Only update DB every 5 seconds
        self.last_percentage = 0
        self.percentage_threshold = 10  # Update every 10% progress
        
        # Track nested progress for better UX
        self.nested_progress = {
            'parent_phase': None,
            'parent_current': 0,
            'parent_total': 0,
            'child_phase': None,
            'child_current': 0,
            'child_total': 0
        }
        
        # Initialize broadcaster for real-time updates
        self.broadcaster = get_sync_broadcaster(provider_type) if sync_job else None
    
    def update_progress(
        self,
        current_item: int,
        total_items: int,
        item_type: str,
        details: Optional[str] = None
    ) -> None:
        """Update sync progress with throttling"""
        if not self.sync_job:
            return
        
        try:
            percentage = round((current_item / total_items) * 100, 2) if total_items > 0 else 0
            
            # Determine if we should update the database
            should_update_db = False
            now = timezone.now()
            
            # Update if:
            # 1. First update (no last update)
            # 2. Completed (100%)
            # 3. Significant percentage change (>10%)
            # 4. More than 5 seconds since last update
            if not self.last_db_update:
                should_update_db = True
            elif current_item >= total_items:  # Completed
                should_update_db = True
            elif abs(percentage - self.last_percentage) >= self.percentage_threshold:
                should_update_db = True
            elif (now - self.last_db_update).total_seconds() >= self.update_frequency_seconds:
                should_update_db = True
            
            # Always update internal state
            if not self.sync_job.progress:
                self.sync_job.progress = {}
            
            self.sync_job.progress.update({
                'current_phase': item_type,
                'current_item': current_item,
                'total_items': total_items,
                'percentage': percentage,
                'last_update': now.isoformat()
            })
            
            # Also update result_summary for backward compatibility
            if not self.sync_job.result_summary:
                self.sync_job.result_summary = {}
            self.sync_job.result_summary['current_progress'] = {
                'stage': item_type,
                'current': current_item,
                'total': total_items,
                'percentage': percentage
            }
            
            # Broadcast real-time update via WebSocket (immediate, not throttled)
            if self.broadcaster and self.sync_job:
                # Map phase names to what frontend expects
                phase_mapping = {
                    'conversations': 'processing_conversations',
                    'messages': 'syncing_messages',
                    'attendees': 'processing_attendees'
                }
                
                mapped_phase = phase_mapping.get(item_type, item_type)
                
                # Build progress data based on phase
                logger.info(f"🔴 update_progress broadcasting: current_item={current_item}, total_items={total_items}, item_type={item_type}")
                logger.info(f"🔴 Current stats: {self.stats}")
                progress_data = {
                    'current_phase': mapped_phase,
                    'current_item': current_item,
                    'total_items': total_items,
                    'details': details,
                    # Always include cumulative counts
                    'conversations_processed': self.stats.get('conversations_synced', 0),
                    'messages_processed': self.stats.get('messages_synced', 0),
                    'attendees_processed': self.stats.get('attendees_synced', 0),
                }
                logger.info(f"🔴 Sending progress_data: conversations_processed={progress_data['conversations_processed']}")
                
                # Add phase-specific data
                if item_type == 'conversations':
                    # For conversations, we know the total
                    progress_data['conversations_total'] = total_items
                    progress_data['percentage'] = percentage
                    progress_data['batch_progress_percent'] = percentage
                elif item_type == 'messages':
                    # For messages, don't use percentage - just counts
                    progress_data['current_conversation_name'] = details.split(' for ')[-1] if ' for ' in details else None
                    # Don't set percentage fields for messages
                else:
                    # For other phases
                    progress_data['percentage'] = percentage if total_items > 0 else 0
                
                self.broadcaster.broadcast_progress(
                    sync_job_id=str(self.sync_job.id),
                    celery_task_id=self.sync_job.celery_task_id,
                    user_id=str(self.sync_job.user_id),
                    progress_data=progress_data,
                    force=False  # Use config to determine if should broadcast
                )
            
            # Only save to database if needed
            if should_update_db:
                # Check if this progress entry exists
                existing_progress = SyncJobProgress.objects.filter(
                    sync_job=self.sync_job,
                    phase_name=item_type
                ).first()
                
                # Create or update progress entry
                progress, created = SyncJobProgress.objects.update_or_create(
                    sync_job=self.sync_job,
                    phase_name=item_type,
                    defaults={
                        'step_name': details or f"Processing {item_type}",
                        'items_processed': current_item,
                        'items_total': total_items,
                        'step_status': 'in_progress',
                        'started_at': timezone.now() if not existing_progress else existing_progress.started_at,
                        'completed_at': timezone.now() if current_item >= total_items else None
                    }
                )
                
                # Update status to RUNNING if it's still PENDING
                if self.sync_job.status == SyncJobStatus.PENDING:
                    self.sync_job.status = SyncJobStatus.RUNNING
                    self.sync_job.save(update_fields=['status', 'progress', 'result_summary', 'last_progress_update'])
                else:
                    self.sync_job.save(update_fields=['progress', 'result_summary', 'last_progress_update'])
                
                # Update tracking variables
                self.last_db_update = now
                self.last_percentage = percentage
                
                # Log significant updates only
                if percentage == 100 or abs(percentage - self.last_percentage) >= 25:
                    logger.info(f"📊 Progress: {item_type} - {current_item}/{total_items} ({percentage}%)")
                else:
                    logger.debug(f"📊 Progress: {item_type} - {current_item}/{total_items} ({percentage}%)")
            else:
                # Log at TRACE level (if available) or skip logging for minor updates
                pass
            
        except Exception as e:
            logger.error(f"Failed to update progress: {e}")
    
    def increment_stat(self, stat_name: str, count: int = 1) -> None:
        """Increment a statistic counter and broadcast update"""
        if stat_name in self.stats and isinstance(self.stats[stat_name], (int, float)):
            self.stats[stat_name] += count
            logger.info(f"📈 INCREMENT_STAT: {stat_name} by {count}, new total: {self.stats[stat_name]}")
            logger.info(f"📈 All stats now: conversations={self.stats.get('conversations_synced', 0)}, messages={self.stats.get('messages_synced', 0)}, attendees={self.stats.get('attendees_synced', 0)}")
            
            # Broadcast the updated stats immediately when they change
            if self.broadcaster and self.sync_job:
                logger.info(f"📡 Broadcasting update: sync_job_id={self.sync_job.id}, celery_task_id={self.sync_job.celery_task_id}")
                # Determine current phase based on what's being incremented
                if 'conversations' in stat_name:
                    phase = 'processing_conversations'
                elif 'messages' in stat_name:
                    phase = 'syncing_messages'
                elif 'attendees' in stat_name:
                    phase = 'processing_attendees'
                else:
                    phase = 'unknown'
                
                progress_data = {
                    'current_phase': phase,
                    'conversations_processed': self.stats.get('conversations_synced', 0),
                    'messages_processed': self.stats.get('messages_synced', 0),
                    'attendees_processed': self.stats.get('attendees_synced', 0),
                }
                
                self.broadcaster.broadcast_progress(
                    sync_job_id=str(self.sync_job.id),
                    celery_task_id=self.sync_job.celery_task_id,
                    user_id=str(self.sync_job.user_id),
                    progress_data=progress_data,
                    force=True  # Force immediate broadcast when stats change
                )
            else:
                logger.warning(f"⚠️ Cannot broadcast: broadcaster={bool(self.broadcaster)}, sync_job={bool(self.sync_job)}")
    
    def add_error(self, error: str) -> None:
        """Add an error to the error list"""
        self.stats['errors'].append({
            'error': str(error),
            'timestamp': timezone.now().isoformat()
        })
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        return self.stats.copy()
    
    def update_nested_progress(
        self,
        parent_phase: str,
        parent_current: int,
        parent_total: int,
        child_phase: Optional[str] = None,
        child_current: Optional[int] = None,
        child_total: Optional[int] = None,
        details: Optional[str] = None
    ) -> None:
        """
        Update progress for nested operations (e.g., messages within conversations)
        
        Args:
            parent_phase: Main phase name (e.g., 'conversations')
            parent_current: Current parent item
            parent_total: Total parent items
            child_phase: Sub-phase name (e.g., 'message_batch')
            child_current: Current child item
            child_total: Total child items
            details: Optional detail message
        """
        # Check if phase changed and broadcast phase change
        if self.broadcaster and self.sync_job:
            if parent_phase != self.nested_progress['parent_phase']:
                self.broadcaster.broadcast_phase_change(
                    sync_job_id=str(self.sync_job.id),
                    celery_task_id=self.sync_job.celery_task_id,
                    user_id=str(self.sync_job.user_id),
                    phase=parent_phase,
                    phase_details=details
                )
        
        # Update nested tracking
        self.nested_progress['parent_phase'] = parent_phase
        self.nested_progress['parent_current'] = parent_current
        self.nested_progress['parent_total'] = parent_total
        
        if child_phase:
            self.nested_progress['child_phase'] = child_phase
            self.nested_progress['child_current'] = child_current or 0
            self.nested_progress['child_total'] = child_total or 0
        
        # Calculate combined percentage
        parent_percentage = (parent_current / parent_total * 100) if parent_total > 0 else 0
        
        # Build detailed message
        if child_phase and child_total and child_total > 0:
            child_percentage = (child_current / child_total * 100) if child_current else 0
            combined_message = (
                f"{parent_phase}: {parent_current}/{parent_total} ({parent_percentage:.1f}%), "
                f"{child_phase}: {child_current}/{child_total} ({child_percentage:.1f}%)"
            )
        else:
            combined_message = f"{parent_phase}: {parent_current}/{parent_total} ({parent_percentage:.1f}%)"
        
        if details:
            combined_message = f"{combined_message} - {details}"
        
        # Use regular update_progress with the combined message
        self.update_progress(
            parent_current,
            parent_total,
            parent_phase,
            combined_message
        )
    
    def finalize(self, status: str = SyncJobStatus.COMPLETED) -> None:
        """Finalize the sync job with accumulated stats"""
        if self.sync_job:
            # Broadcast final job update
            if self.broadcaster:
                self.broadcaster.broadcast_job_update(
                    sync_job_id=str(self.sync_job.id),
                    celery_task_id=self.sync_job.celery_task_id,
                    user_id=str(self.sync_job.user_id),
                    status=status.lower(),  # Frontend expects lowercase
                    result_summary=self.stats,
                    error_message='; '.join(str(e) for e in self.stats.get('errors', [])) if status == SyncJobStatus.FAILED else None
                )
            
            SyncJobManager.update_sync_job(
                self.sync_job,
                status=status,
                stats=self.stats
            )


class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, max_calls: int = 100, time_window: int = 60):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    def can_proceed(self) -> bool:
        """Check if we can make another API call"""
        now = timezone.now()
        # Remove old calls outside the time window
        self.calls = [
            call_time for call_time in self.calls
            if (now - call_time).total_seconds() < self.time_window
        ]
        
        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True
        return False
    
    def wait_time(self) -> float:
        """Calculate wait time until next call is allowed"""
        if len(self.calls) < self.max_calls:
            return 0
        
        oldest_call = min(self.calls)
        now = timezone.now()
        elapsed = (now - oldest_call).total_seconds()
        wait = self.time_window - elapsed
        return max(0, wait)