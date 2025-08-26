"""
Provider-agnostic sync progress broadcasting system
Handles real-time WebSocket updates for sync operations across all providers
"""
import logging
from typing import Dict, Any, Optional
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone

logger = logging.getLogger(__name__)


class SyncProgressBroadcaster:
    """
    Centralized broadcaster for sync progress updates.
    Supports multiple providers (WhatsApp, Email, LinkedIn, etc.)
    """
    
    def __init__(self, provider_type: str = 'whatsapp'):
        """
        Initialize broadcaster with provider type
        
        Args:
            provider_type: Type of provider (whatsapp, email, linkedin, etc.)
        """
        self.provider_type = provider_type.lower()
        self.channel_layer = get_channel_layer()
        self.last_broadcast_percentage = {}  # Track last broadcast per sync job
        self.last_message_count = {}  # Track last broadcasted message count
        
        # Get message broadcast interval from config
        from communications.channels.whatsapp.sync.config import SYNC_CONFIG
        self.message_broadcast_interval = SYNC_CONFIG.get('messages_broadcast_interval', 100)
        
    def should_broadcast(self, sync_job_id: str, progress_data: Dict[str, Any]) -> bool:
        """
        Determine if progress should be broadcast based on phase and counts
        
        Args:
            sync_job_id: Sync job ID
            progress_data: Progress information including phase and counts
            
        Returns:
            True if should broadcast, False otherwise
        """
        phase = progress_data.get('current_phase', '')
        
        # Track counts for all metrics
        conversations_count = progress_data.get('conversations_processed', 0)
        messages_count = progress_data.get('messages_processed', 0)
        attendees_count = progress_data.get('attendees_processed', 0)
        
        # Get last broadcast counts (default to -1 to ensure first update broadcasts)
        last_key = f"{sync_job_id}_last_counts"
        if not hasattr(self, '_last_broadcast_counts'):
            self._last_broadcast_counts = {}
        
        last_counts = self._last_broadcast_counts.get(last_key, {
            'conversations': -1,
            'messages': -1, 
            'attendees': -1
        })
        
        # Broadcast if any count has changed
        should_send = False
        if conversations_count != last_counts['conversations']:
            should_send = True
        if messages_count != last_counts['messages']:
            should_send = True
        if attendees_count != last_counts['attendees']:
            should_send = True
            
        # Update last broadcast counts if broadcasting
        if should_send:
            self._last_broadcast_counts[last_key] = {
                'conversations': conversations_count,
                'messages': messages_count,
                'attendees': attendees_count
            }
            
        return should_send
    
    def broadcast_progress(
        self,
        sync_job_id: str,
        celery_task_id: str,
        user_id: str,
        progress_data: Dict[str, Any],
        force: bool = False
    ) -> None:
        """
        Broadcast sync progress to WebSocket channels
        
        Args:
            sync_job_id: Database sync job UUID
            celery_task_id: Celery task ID (frontend uses this)
            user_id: User who initiated sync
            progress_data: Progress information
            force: Force broadcast regardless of configuration
        """
        import time
        timestamp = time.time()
        logger.info(f"🔵 [{timestamp}] broadcast_progress called: celery_task_id={celery_task_id}, force={force}")
        logger.info(f"🔵 [{timestamp}] Progress data: {progress_data}")
        
        if not self.channel_layer:
            logger.error("❌ No channel layer available for broadcasting")
            return
            
        try:
            # Check if should broadcast (unless forced)
            if not force and not self.should_broadcast(sync_job_id, progress_data):
                logger.debug(f"🟡 Skipping broadcast (should_broadcast returned False)")
                return
            
            # Update tracking based on phase
            phase = progress_data.get('current_phase', '')
            if 'message' in phase.lower() or 'sync' in phase.lower():
                messages_count = progress_data.get('messages_processed', 0)
                self.last_message_count[sync_job_id] = messages_count
            
            # Prepare broadcast message
            # Note: When sent via channel_layer.group_send, the 'type' routes to handler
            # and the rest of the fields become the event parameter
            message = {
                'type': 'sync_progress_update',  # Routes to sync_progress_update handler
                # These fields will be available directly in the event
                'sync_job_id': sync_job_id,
                'celery_task_id': celery_task_id,  # Frontend needs this
                'provider': self.provider_type,
                'user_id': user_id,
                'progress': progress_data,
                'updated_at': timezone.now().isoformat(),
                'timestamp': timezone.now().timestamp()
            }
            
            # Broadcast to multiple channels for flexibility
            channels_to_broadcast = [
                # Primary channel: Celery task ID (frontend subscribes here)
                f'sync_progress_{celery_task_id}',
                
                # User's all sync jobs
                f'sync_jobs_{user_id}',
                
                # Specific sync job
                f'sync_job_{sync_job_id}',
                
                # Provider-specific channel (future-proofing)
                f'sync_{self.provider_type}_{user_id}'
            ]
            
            # Send to all channels
            for channel_name in channels_to_broadcast:
                try:
                    async_to_sync(self.channel_layer.group_send)(
                        channel_name,
                        message
                    )
                    logger.info(f"✅ Broadcasted to {channel_name}: conversations={progress_data.get('conversations_processed', 0)}, messages={progress_data.get('messages_processed', 0)}, attendees={progress_data.get('attendees_processed', 0)}")
                except Exception as e:
                    logger.warning(f"Failed to broadcast to {channel_name}: {e}")
            
            # Log meaningful progress updates
            phase = progress_data.get('current_phase', '')
            if 'conversation' in phase.lower():
                conversations = progress_data.get('conversations_processed', 0)
                total = progress_data.get('conversations_total', 0)
                logger.info(
                    f"📊 {self.provider_type.upper()} Sync: {conversations}/{total} conversations"
                )
            elif 'message' in phase.lower() or 'sync' in phase.lower():
                messages = progress_data.get('messages_processed', 0)
                logger.info(
                    f"📊 {self.provider_type.upper()} Sync: {messages} messages synced"
                )
                
        except Exception as e:
            logger.error(f"Failed to broadcast sync progress: {e}")
    
    def broadcast_job_update(
        self,
        sync_job_id: str,
        celery_task_id: str,
        user_id: str,
        status: str,
        result_summary: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Broadcast sync job status update (started, completed, failed)
        
        Args:
            sync_job_id: Database sync job UUID
            celery_task_id: Celery task ID
            user_id: User who initiated sync
            status: Job status (running, completed, failed)
            result_summary: Final results if completed
            error_message: Error message if failed
        """
        if not self.channel_layer:
            return
            
        try:
            # Same structure as progress update - fields at root level
            message = {
                'type': 'sync_job_update',
                'sync_job_id': sync_job_id,
                'celery_task_id': celery_task_id,
                'provider': self.provider_type,
                'user_id': user_id,
                'status': status,
                'result_summary': result_summary or {},
                'error_message': error_message,
                'updated_at': timezone.now().isoformat()
            }
            
            # Broadcast to relevant channels
            channels = [
                f'sync_progress_{celery_task_id}',
                f'sync_jobs_{user_id}',
                f'sync_{self.provider_type}_{user_id}'
            ]
            
            for channel_name in channels:
                try:
                    async_to_sync(self.channel_layer.group_send)(
                        channel_name,
                        message
                    )
                except Exception as e:
                    logger.warning(f"Failed to broadcast job update to {channel_name}: {e}")
            
            logger.info(
                f"📢 {self.provider_type.upper()} Sync Job {status.upper()}: "
                f"{sync_job_id[:8]}... (Task: {celery_task_id[:8]}...)"
            )
            
        except Exception as e:
            logger.error(f"Failed to broadcast job update: {e}")
    
    def broadcast_phase_change(
        self,
        sync_job_id: str,
        celery_task_id: str,
        user_id: str,
        phase: str,
        phase_details: Optional[str] = None
    ) -> None:
        """
        Broadcast when sync moves to a new phase
        
        Args:
            sync_job_id: Database sync job UUID
            celery_task_id: Celery task ID
            user_id: User who initiated sync
            phase: New phase name (conversations, messages, etc.)
            phase_details: Optional details about the phase
        """
        if not self.channel_layer:
            return
            
        try:
            message = {
                'type': 'sync_phase_change',
                'sync_job_id': sync_job_id,
                'celery_task_id': celery_task_id,
                'provider': self.provider_type,
                'user_id': user_id,
                'phase': phase,
                'phase_details': phase_details,
                'updated_at': timezone.now().isoformat()
            }
            
            # Send to progress channel
            async_to_sync(self.channel_layer.group_send)(
                f'sync_progress_{celery_task_id}',
                message
            )
            
            logger.info(f"🔄 {self.provider_type.upper()} Sync entering phase: {phase}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast phase change: {e}")


# Singleton instance for easy import
_broadcaster_instances = {}


def get_sync_broadcaster(provider_type: str = 'whatsapp') -> SyncProgressBroadcaster:
    """
    Get or create a broadcaster instance for the given provider
    
    Args:
        provider_type: Type of provider
        
    Returns:
        SyncProgressBroadcaster instance
    """
    if provider_type not in _broadcaster_instances:
        _broadcaster_instances[provider_type] = SyncProgressBroadcaster(provider_type)
    return _broadcaster_instances[provider_type]