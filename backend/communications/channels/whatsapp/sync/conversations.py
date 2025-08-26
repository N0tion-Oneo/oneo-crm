"""
Conversation Synchronization Service
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from asgiref.sync import async_to_sync

from communications.models import (
    Channel, Conversation, UserChannelConnection,
    ConversationType
)
from ..service import WhatsAppService
from ..utils.message_formatter import WhatsAppMessageFormatter
from .attendees import AttendeeSyncService
from .utils import SyncProgressTracker

logger = logging.getLogger(__name__)


class ConversationSyncService:
    """Handles conversation synchronization for WhatsApp"""
    
    def __init__(
        self,
        channel: Channel,
        connection: Optional[UserChannelConnection] = None,
        progress_tracker: Optional[SyncProgressTracker] = None
    ):
        self.channel = channel
        self.connection = connection
        self.progress_tracker = progress_tracker
        
        # Initialize services
        self.whatsapp_service = WhatsAppService(channel=channel)
        self.message_formatter = WhatsAppMessageFormatter()
        self.attendee_service = AttendeeSyncService(channel=channel)
    
    def sync_conversations(
        self,
        max_conversations: int = 50,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sync conversations from WhatsApp
        
        Args:
            max_conversations: Maximum number of conversations to sync
            cursor: Pagination cursor for API
            
        Returns:
            Statistics dictionary
        """
        stats = {
            'conversations_synced': 0,
            'conversations_created': 0,
            'conversations_updated': 0,
            'attendees_synced': 0,
            'errors': [],
            'next_cursor': None
        }
        
        try:
            logger.debug(f"📱 Syncing conversations for channel {self.channel.name}")
            
            # Get account ID from connection
            account_id = None
            if self.connection:
                account_id = self.connection.unipile_account_id
            
            # Fetch conversations from API
            api_result = async_to_sync(self.whatsapp_service.client.get_conversations)(
                account_id=account_id,
                limit=max_conversations,
                cursor=cursor
            )
            
            if not api_result.get('success'):
                error_msg = f"Failed to fetch conversations: {api_result.get('error')}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
                return stats
            
            conversations_data = api_result.get('conversations', [])
            stats['next_cursor'] = api_result.get('cursor')
            
            logger.debug(f"  Retrieved {len(conversations_data)} conversations from API")
            
            # Process conversations
            processed_stats = self._process_conversations_batch(conversations_data)
            
            # Update stats
            stats['conversations_synced'] = processed_stats['total']
            stats['conversations_created'] = processed_stats['created']
            stats['conversations_updated'] = processed_stats['updated']
            stats['attendees_synced'] = processed_stats['attendees']
            
            logger.debug(
                f"  ✅ Synced {stats['conversations_synced']} conversations "
                f"({stats['conversations_created']} new)"
            )
            
        except Exception as e:
            error_msg = f"Error syncing conversations: {e}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
        
        return stats
    
    def _process_conversations_batch(
        self,
        conversations_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process a batch of conversations"""
        stats = {
            'total': 0,
            'created': 0,
            'updated': 0,
            'attendees': 0
        }
        
        created_conversations = []
        
        with transaction.atomic():
            for idx, conv_data in enumerate(conversations_data):
                try:
                    # Process conversation
                    conversation, created = self._store_conversation(conv_data)
                    
                    if conversation:
                        stats['total'] += 1
                        if created:
                            stats['created'] += 1
                            created_conversations.append(conversation)
                        else:
                            stats['updated'] += 1
                        
                        # Attendees are now synced in a separate phase by comprehensive.py
                    
                    # Update progress for every conversation (not just every 10)
                    if self.progress_tracker:
                        self.progress_tracker.update_progress(
                            idx + 1,
                            len(conversations_data),
                            'conversations',
                            f"Processing conversation {idx + 1} of {len(conversations_data)}"
                        )
                    
                except Exception as e:
                    logger.error(f"Failed to process conversation: {e}")
                    continue
        
        return stats
    
    def _store_conversation(
        self,
        conv_data: Dict[str, Any]
    ) -> tuple[Optional[Conversation], bool]:
        """
        Store a single conversation
        
        Returns:
            Tuple of (Conversation instance or None, created boolean)
        """
        try:
            # Extract external ID
            external_id = conv_data.get('id') or conv_data.get('chat_id')
            if not external_id:
                logger.warning("Conversation has no external ID")
                return None, False
            
            # Extract conversation details
            conv_type = self._determine_conversation_type(conv_data)
            subject = self._extract_conversation_subject(conv_data)
            
            # Parse timestamps
            last_message_at = self._parse_timestamp(
                conv_data.get('last_message_at') or 
                conv_data.get('updated_at')
            )
            
            # Create or update conversation
            conversation, created = Conversation.objects.update_or_create(
                external_thread_id=external_id,
                channel=self.channel,
                defaults={
                    'conversation_type': conv_type,
                    'subject': subject,
                    'last_message_at': last_message_at,
                    'message_count': conv_data.get('message_count', 0),
                    'unread_count': conv_data.get('unread_count', 0),
                    'participant_count': conv_data.get('participant_count', 1),
                    'metadata': {
                        'api_data': conv_data,
                        'synced_from': 'conversation_sync_service',
                        'sync_time': timezone.now().isoformat()
                    }
                }
            )
            
            if created:
                logger.debug(f"  Created conversation: {subject or external_id[:20]}")
            
            return conversation, created
            
        except Exception as e:
            logger.error(f"Failed to store conversation: {e}")
            return None, False
    
    def _determine_conversation_type(self, conv_data: Dict[str, Any]) -> str:
        """Determine conversation type from data"""
        # Check if it's a group chat
        if conv_data.get('is_group'):
            return ConversationType.GROUP
        
        # Check participant count
        participant_count = conv_data.get('participant_count', 1)
        if participant_count > 2:
            return ConversationType.GROUP
        
        # Check for broadcast
        if conv_data.get('is_broadcast'):
            return ConversationType.BROADCAST
        
        # Default to direct message
        return ConversationType.DIRECT
    
    def _extract_conversation_subject(self, conv_data: Dict[str, Any]) -> str:
        """Extract conversation subject/name"""
        # Try various fields for conversation name
        subject = (
            conv_data.get('name') or
            conv_data.get('subject') or
            conv_data.get('title') or
            ''
        )
        
        # If no subject and it's a direct chat, try to get participant name
        if not subject and conv_data.get('participants'):
            participants = conv_data['participants']
            if len(participants) == 1:
                participant = participants[0]
                subject = (
                    participant.get('name') or
                    participant.get('push_name') or
                    participant.get('phone', '')
                )
        
        return subject[:255] if subject else ''  # Limit to field max length
    
    def _parse_timestamp(self, timestamp: Any) -> Optional[datetime]:
        """Parse various timestamp formats"""
        if not timestamp:
            return None
        
        try:
            if isinstance(timestamp, datetime):
                return timestamp if timestamp.tzinfo else timezone.make_aware(timestamp)
            elif isinstance(timestamp, str):
                # Handle ISO format
                if 'T' in timestamp:
                    return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                # Handle other string formats
                return datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            elif isinstance(timestamp, (int, float)):
                # Unix timestamp
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except Exception as e:
            logger.debug(f"Failed to parse timestamp {timestamp}: {e}")
        
        return None
    
    def sync_conversations_paginated(
        self,
        max_total: int = 50,
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """
        Sync all conversations with pagination
        
        Args:
            max_total: Maximum total conversations to sync
            batch_size: Number of conversations per API call
            
        Returns:
            Combined statistics
        """
        logger.debug(f"📱 Starting paginated conversation sync (max_total={max_total}, batch_size={batch_size})")
        
        total_stats = {
            'conversations_synced': 0,
            'conversations_created': 0,
            'conversations_updated': 0,
            'attendees_synced': 0,
            'errors': []
        }
        
        cursor = None
        synced = 0
        iteration = 0
        
        while synced < max_total:
            iteration += 1
            # Calculate batch size
            remaining = max_total - synced
            current_batch = min(batch_size, remaining)
            
            logger.debug(f"  Iteration {iteration}: synced={synced}, max_total={max_total}, current_batch={current_batch}, cursor={cursor}")
            
            # Sync batch
            batch_stats = self.sync_conversations(
                max_conversations=current_batch,
                cursor=cursor
            )
            
            # Update totals
            total_stats['conversations_synced'] += batch_stats['conversations_synced']
            total_stats['conversations_created'] += batch_stats['conversations_created']
            total_stats['conversations_updated'] += batch_stats['conversations_updated']
            total_stats['attendees_synced'] += batch_stats['attendees_synced']
            total_stats['errors'].extend(batch_stats.get('errors', []))
            
            synced += batch_stats['conversations_synced']
            
            logger.debug(f"  Batch result: synced {batch_stats['conversations_synced']} conversations, total now: {synced}")
            
            # Check if more data available
            cursor = batch_stats.get('next_cursor')
            if not cursor or batch_stats['conversations_synced'] == 0:
                logger.debug(f"  Breaking loop: cursor={cursor}, conversations_synced={batch_stats['conversations_synced']}")
                break
            
            # Update progress tracker
            if self.progress_tracker:
                self.progress_tracker.increment_stat(
                    'conversations_synced',
                    batch_stats['conversations_synced']
                )
                
                # Update overall progress
                self.progress_tracker.update_progress(
                    synced,
                    max_total,
                    'conversations_paginated',
                    f"Synced {synced} of {max_total} conversations"
                )
        
        logger.debug(
            f"Paginated sync complete: {total_stats['conversations_synced']} "
            f"conversations ({total_stats['conversations_created']} new)"
        )
        
        return total_stats
    
    def get_conversations_for_sync(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[Conversation]:
        """
        Get conversations that need message syncing
        
        Args:
            limit: Maximum number of conversations to return
            offset: Offset for pagination
            
        Returns:
            List of Conversation instances
        """
        # Get conversations ordered by last sync time (oldest first)
        conversations = Conversation.objects.filter(
            channel=self.channel
        ).order_by(
            'last_synced_at',  # Sync oldest first
            '-last_message_at'  # Then by most recent activity
        )[offset:offset + limit]
        
        return list(conversations)