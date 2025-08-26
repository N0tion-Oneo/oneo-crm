"""
Comprehensive Synchronization Service
Orchestrates full WhatsApp data synchronization
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction

from communications.models import (
    Channel, UserChannelConnection, SyncJob, SyncJobStatus, SyncJobType
)
from .config import SYNC_CONFIG
from .conversations import ConversationSyncService
from .messages import MessageSyncService
from .attendees import AttendeeSyncService
from .utils import SyncJobManager, SyncProgressTracker

logger = logging.getLogger(__name__)


class ComprehensiveSyncService:
    """Orchestrates comprehensive WhatsApp synchronization"""
    
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
        self.progress_tracker = SyncProgressTracker(sync_job)
        
        # Initialize sync services
        self.conversation_service = ConversationSyncService(
            channel=channel,
            connection=connection,
            progress_tracker=self.progress_tracker
        )
        self.message_service = MessageSyncService(
            channel=channel,
            connection=connection,
            progress_tracker=self.progress_tracker
        )
        self.attendee_service = AttendeeSyncService(
            channel=channel
        )
    
    def run_comprehensive_sync(
        self,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run a comprehensive sync of all WhatsApp data
        
        Args:
            options: Sync options dictionary
                - max_conversations: Number of conversations to sync (default: 300)
                - max_messages_per_chat: Messages per conversation (default: 300) 
                - days_back: Days to look back for messages (default: 0 = no filter, sync all)
                  Set to >0 to only sync recent messages, e.g., 30 for last month
            
        Returns:
            Statistics dictionary
        """
        # Get sync options (ignores any overrides)
        from .config import get_sync_options
        sync_options = get_sync_options(options)
        
        # Broadcast sync start
        if self.progress_tracker and self.sync_job:
            from communications.sync import get_sync_broadcaster
            broadcaster = get_sync_broadcaster('whatsapp')
            broadcaster.broadcast_job_update(
                sync_job_id=str(self.sync_job.id),
                celery_task_id=self.sync_job.celery_task_id,
                user_id=str(self.sync_job.user_id),
                status='running'
            )
            
            # Also broadcast initial progress with 0 counts
            initial_progress = {
                'current_phase': 'initializing',
                'conversations_processed': 0,
                'messages_processed': 0,
                'attendees_processed': 0,
            }
            broadcaster.broadcast_progress(
                sync_job_id=str(self.sync_job.id),
                celery_task_id=self.sync_job.celery_task_id,
                user_id=str(self.sync_job.user_id),
                progress_data=initial_progress,
                force=True  # Force initial broadcast
            )
        
        stats = {
            'conversations_synced': 0,
            'messages_synced': 0,
            'attendees_synced': 0,
            'conversations_created': 0,
            'messages_created': 0,
            'errors': [],
            'started_at': timezone.now().isoformat(),
            'completed_at': None
        }
        
        try:
            # Phase 1: Sync conversations
            conv_stats = self._sync_conversations_phase(sync_options)
            stats['conversations_synced'] = conv_stats['conversations_synced']
            stats['conversations_created'] = conv_stats['conversations_created']
            stats['attendees_synced'] += conv_stats.get('attendees_synced', 0)
            stats['errors'].extend(conv_stats.get('errors', []))
            
            # Phase 1.5: Sync attendees from chat level (not from messages)
            attendee_stats = self._sync_attendees_phase(sync_options)
            stats['attendees_synced'] += attendee_stats.get('attendees_synced', 0)
            stats['errors'].extend(attendee_stats.get('errors', []))
            
            # Phase 2: Sync messages for each conversation
            msg_stats = self._sync_messages_phase(sync_options)
            stats['messages_synced'] = msg_stats['messages_synced']
            stats['messages_created'] = msg_stats['messages_created']
            stats['incomplete_conversations'] = msg_stats.get('incomplete_conversations', [])
            # Attendees are now counted in Phase 1.5, not from messages
            stats['errors'].extend(msg_stats.get('errors', []))
            
            # Phase 3: Final cleanup and optimization
            self._cleanup_phase()
            
            stats['completed_at'] = timezone.now().isoformat()
            
            # Finalize progress tracking
            if self.progress_tracker:
                self.progress_tracker.finalize(
                    status=SyncJobStatus.COMPLETED if not stats['errors'] else SyncJobStatus.COMPLETED
                )
            
            # Only show final result and any issues
            if stats.get('incomplete_conversations'):
                issues = [f"{name}: {count}/{target}" for name, count, target in stats['incomplete_conversations'][:3]]
                logger.warning(f"⚠️ Incomplete: {', '.join(issues)}")
            
            logger.info(f"✅ {stats['conversations_synced']} conversations, {stats['messages_synced']} messages")
            
        except Exception as e:
            error_msg = f"Comprehensive sync failed: {e}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
            stats['completed_at'] = timezone.now().isoformat()
            
            # Mark job as failed
            if self.progress_tracker:
                self.progress_tracker.add_error(error_msg)
                self.progress_tracker.finalize(status=SyncJobStatus.FAILED)
        
        return stats
    
    def _sync_conversations_phase(
        self,
        sync_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Phase 1: Sync conversations"""
        max_conversations = sync_options['max_conversations']
        
        # Don't broadcast 0 again - we already did initial broadcast in run_comprehensive_sync
        # Just log that we're starting
        logger.info(f"📱 Starting conversation sync phase (max={max_conversations}) for channel {self.channel.id} ({self.channel.unipile_account_id})")
        
        # Sync conversations with pagination
        conv_stats = self.conversation_service.sync_conversations_paginated(
            max_total=max_conversations,
            batch_size=min(50, max_conversations)
        )
        
        # Don't call update_progress at phase end - it broadcasts messages_processed=0
        # The increment_stat calls during processing are sufficient
        logger.debug(f"Conversations phase completed: {conv_stats['conversations_synced']} conversations")
        
        # Silent completion
        
        return conv_stats
    
    def _sync_attendees_phase(
        self,
        sync_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Phase 1.5: Sync attendees from chat level"""
        from asgiref.sync import async_to_sync
        from ..service import WhatsAppService
        
        stats = {
            'attendees_synced': 0,
            'errors': []
        }
        
        # Get account ID from connection
        account_id = None
        if self.connection:
            account_id = self.connection.unipile_account_id
        
        if not account_id:
            error_msg = "No account ID available for attendee sync"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
            return stats
        
        # Initialize WhatsApp service for API calls
        whatsapp_service = WhatsAppService(channel=self.channel)
        
        # Get all conversations that were just synced
        from communications.models import Conversation
        conversations = Conversation.objects.filter(
            channel=self.channel
        ).order_by('-created_at')[:sync_options['max_conversations']]
        
        # Just log the phase transition - don't broadcast with messages=0
        logger.info(f"👥 Starting attendee sync phase ({conversations.count()} conversations)")
        
        # For each conversation, fetch attendees from API
        for idx, conversation in enumerate(conversations):
            try:
                chat_id = conversation.external_thread_id
                
                # Fetch attendees from API
                attendees_result = async_to_sync(whatsapp_service.client.get_attendees)(
                    account_id=account_id,
                    chat_id=chat_id
                )
                
                if attendees_result.get('success'):
                    attendees_data = {
                        'attendees': attendees_result.get('attendees', []),
                        'id': chat_id
                    }
                    
                    # Sync attendees using the attendee service
                    synced_attendees = self.attendee_service.sync_attendees_from_chat(
                        attendees_data,
                        conversation
                    )
                    
                    stats['attendees_synced'] += len(synced_attendees)
                    
                    # Update cumulative stats in tracker
                    if self.progress_tracker and len(synced_attendees) > 0:
                        self.progress_tracker.increment_stat('attendees_synced', len(synced_attendees))
                
                # Don't call update_progress - rely on increment_stat to broadcast
                # This prevents showing messages_processed=0 during attendees phase
                if (idx + 1) % 10 == 0:
                    logger.debug(f"Processed {idx + 1}/{conversations.count()} chats for attendees")
                    
            except Exception as e:
                error_msg = f"Failed to sync attendees for conversation {conversation.external_thread_id}: {e}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
        
        # Don't call update_progress here - it would broadcast with messages=0 since messages haven't been synced yet
        # The increment_stat calls during processing are sufficient
        logger.info(f"✅ Attendees phase complete: {stats['attendees_synced']} attendees synced")
        
        return stats
    
    def _sync_messages_phase(
        self,
        sync_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Phase 2: Sync messages for conversations"""
        from .config import SYNC_CONFIG
        max_messages_per_chat = sync_options['max_messages_per_chat']
        days_back = sync_options.get('days_back', 0)  # Default to 0 (no filter)
        
        # Calculate since date - only apply if days_back is explicitly set and > 0
        since_date = None
        if days_back and days_back > 0:
            since_date = timezone.now() - timedelta(days=days_back)
        
        # Get conversations to sync messages for
        # Use the same max_conversations as Phase 1 to ensure consistency
        max_conversations = sync_options['max_conversations']  # No defaults, use config value
        conversations = self.conversation_service.get_conversations_for_sync(
            limit=max_conversations
        )
        
        # Just log the phase transition - don't broadcast yet to avoid showing messages=0
        logger.info(f"📨 Starting messages sync phase ({len(conversations)} conversations)")
        
        # Sync messages for each conversation
        total_stats = {
            'messages_synced': 0,
            'messages_created': 0,
            'attendees_synced': 0,
            'errors': [],
            'incomplete_conversations': []  # Track which didn't get full messages
        }
        
        for idx, conversation in enumerate(conversations):
            try:
                # Don't broadcast here - let increment_stat handle it when messages are actually synced
                
                # Sync messages for this conversation
                msg_stats = self.message_service.sync_messages_for_conversation(
                    conversation,
                    max_messages=max_messages_per_chat,
                    since_date=since_date
                )
                
                # Update totals
                total_stats['messages_synced'] += msg_stats['messages_synced']
                total_stats['messages_created'] += msg_stats['messages_created']
                # Attendees are counted in Phase 1.5, not from messages
                total_stats['errors'].extend(msg_stats.get('errors', []))
                
                # Track incomplete conversations
                conv_name = conversation.subject or conversation.external_thread_id[:30]
                if msg_stats['messages_synced'] < max_messages_per_chat and msg_stats['messages_synced'] > 0:
                    total_stats['incomplete_conversations'].append(
                        (conv_name, msg_stats['messages_synced'], max_messages_per_chat)
                    )
                
                # Update conversation sync timestamp
                conversation.last_synced_at = timezone.now()
                conversation.save(update_fields=['last_synced_at'])
                
                # Don't call update_progress - let increment_stat in message service handle broadcasting
                # This prevents resetting the visual display when switching phases
                logger.debug(f"Processed conversation {idx + 1}/{len(conversations)}: {msg_stats['messages_synced']} messages")
                
                
            except Exception as e:
                error_msg = f"Failed to sync messages for conversation {conversation.id}: {e}"
                logger.error(error_msg)
                total_stats['errors'].append(error_msg)
        
        # Stats already incremented during message processing
        
        # Include incomplete conversations in returned stats
        total_stats['incomplete_conversations'] = total_stats.get('incomplete_conversations', [])
        return total_stats
    
    def _cleanup_phase(self) -> None:
        """Phase 3: Cleanup and optimization"""
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
            # Use update() to avoid triggering signals
            if self.connection:
                from communications.models import UserChannelConnection
                UserChannelConnection.objects.filter(pk=self.connection.pk).update(
                    last_sync_at=timezone.now()
                )
            
            
        except Exception as e:
            logger.error(f"Cleanup phase failed: {e}")
    
    def estimate_sync_time(
        self,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Estimate time required for sync
        
        Args:
            options: Sync options
            
        Returns:
            Estimation dictionary
        """
        sync_options = {**DEFAULT_SYNC_OPTIONS, **(options or {})}
        
        # Rough estimates based on experience
        conversations = sync_options['max_conversations']
        messages_per = sync_options['max_messages_per_chat']
        
        # Assume 0.5 seconds per conversation and 0.01 seconds per message
        estimated_seconds = (conversations * 0.5) + (conversations * messages_per * 0.01)
        
        return {
            'estimated_seconds': int(estimated_seconds),
            'estimated_minutes': round(estimated_seconds / 60, 1),
            'conversations_to_sync': conversations,
            'messages_per_conversation': messages_per,
            'total_messages_estimate': conversations * messages_per
        }
    
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
        
        # Check connection if required
        if self.connection:
            if not self.connection.is_active:
                validation['warnings'].append("Connection is not active")
            
            if not self.connection.unipile_account_id:
                validation['valid'] = False
                validation['errors'].append("No UniPile account ID configured")
        
        # Check for existing sync job
        if self.sync_job:
            if self.sync_job.status == SyncJobStatus.RUNNING:
                validation['warnings'].append("Sync job already in progress")
        
        return validation