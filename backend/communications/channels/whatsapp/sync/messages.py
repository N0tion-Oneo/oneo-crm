"""
Message Synchronization Service
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from asgiref.sync import async_to_sync, sync_to_async

from communications.models import (
    Channel, Conversation, Message, UserChannelConnection,
    MessageStatus, MessageDirection
)
from communications.utils.message_direction import determine_message_direction
from ..service import WhatsAppService
from ..utils.message_formatter import WhatsAppMessageFormatter
from .attendees import AttendeeSyncService
from .utils import SyncProgressTracker

logger = logging.getLogger(__name__)


class MessageSyncService:
    """Handles message synchronization for WhatsApp"""
    
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
    
    def sync_messages_for_conversation(
        self,
        conversation: Conversation,
        max_messages: int = 100,
        since_date: Optional[datetime] = None,
        use_pagination: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Sync messages for a specific conversation
        
        Args:
            conversation: Conversation to sync messages for
            max_messages: Maximum number of messages to sync
            since_date: Only sync messages after this date
            use_pagination: Whether to use pagination (defaults to config setting)
            
        Returns:
            Statistics dictionary
        """
        # Check if pagination should be used
        from .config import SYNC_CONFIG
        if use_pagination is None:
            use_pagination = SYNC_CONFIG.get('enable_message_pagination', True)
        
        if use_pagination:
            batch_size = SYNC_CONFIG.get('messages_batch_size', 50)
            return self.sync_messages_for_conversation_paginated(
                conversation=conversation,
                max_messages=max_messages,
                since_date=since_date,
                batch_size=batch_size
            )
        
        # Original non-paginated implementation
        stats = {
            'messages_synced': 0,
            'messages_created': 0,
            'messages_updated': 0,
            'errors': []
        }
        
        try:
            external_id = conversation.external_thread_id
            if not external_id:
                logger.warning(f"No external ID for conversation {conversation.id}")
                return stats
            
            logger.debug(f"📨 Syncing messages for conversation {external_id[:20]}...")
            
            # Update progress before API call
            if self.progress_tracker:
                self.progress_tracker.update_progress(
                    0, max_messages, 'fetching_messages',
                    f"Fetching messages for {external_id[:20]}..."
                )
            
            # Fetch messages from API 
            # Note: account_id is required by the method signature but not used internally
            # The WhatsAppClient.get_messages() method only uses conversation_id for chat-specific endpoints
            api_result = async_to_sync(self.whatsapp_service.client.get_messages)(
                account_id=self.whatsapp_service.account_identifier or '',  # Pass account ID but it won't be used
                conversation_id=external_id,
                limit=max_messages
            )
            
            if not api_result.get('success'):
                error_msg = f"Failed to fetch messages: {api_result.get('error')}"
                logger.error(error_msg)
                stats['errors'].append(error_msg)
                return stats
            
            messages_data = api_result.get('messages', [])
            logger.debug(f"  Retrieved {len(messages_data)} messages from API")
            
            # Update progress after API retrieval
            if self.progress_tracker and messages_data:
                self.progress_tracker.update_progress(
                    0, len(messages_data), 'processing_messages',
                    f"Processing {len(messages_data)} messages..."
                )
            
            # Process messages
            processed_stats = self._process_messages_batch(
                messages_data,
                conversation,
                since_date
            )
            
            # Update stats
            stats['messages_synced'] = processed_stats['total']
            stats['messages_created'] = processed_stats['created']
            stats['messages_updated'] = processed_stats['updated']
            
            # Update conversation metadata
            if messages_data:
                self._update_conversation_from_messages(conversation, messages_data)
            
            logger.info(
                f"  ✅ Synced {stats['messages_synced']} messages "
                f"({stats['messages_created']} new)"
            )
            
        except Exception as e:
            error_msg = f"Error syncing messages for {conversation.id}: {e}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
        
        return stats
    
    def _process_messages_batch(
        self,
        messages_data: List[Dict[str, Any]],
        conversation: Conversation,
        since_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Process a batch of messages"""
        stats = {
            'total': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0
        }
        
        # Attendees are now synced in Phase 1.5 by comprehensive.py
        
        with transaction.atomic():
            for idx, msg_data in enumerate(messages_data):
                try:
                    # Update progress less frequently - every 25 messages or at the end
                    if self.progress_tracker and ((idx + 1) % 25 == 0 or (idx + 1) == len(messages_data)):
                        self.progress_tracker.update_progress(
                            idx + 1, len(messages_data), 'processing_messages',
                            f"Processing message {idx + 1} of {len(messages_data)}"
                        )
                    
                    # Check date filter
                    if since_date:
                        msg_date = self._parse_message_date(msg_data)
                        if msg_date and msg_date < since_date:
                            stats['skipped'] += 1
                            continue
                    
                    # Store message
                    message, created = self._store_message(msg_data, conversation)
                    
                    if message:
                        stats['total'] += 1
                        if created:
                            stats['created'] += 1
                        else:
                            stats['updated'] += 1
                        
                        # Find existing attendee to link as sender (attendees already synced in Phase 1.5)
                        provider_id = msg_data.get('attendee_provider_id')
                        if provider_id:
                            attendee = self.attendee_service.find_attendee_by_provider_id(provider_id)
                            
                            # Link attendee as sender to the message
                            if attendee and not message.sender:
                                message.sender = attendee
                                message.save(update_fields=['sender'])
                    
                except Exception as e:
                    logger.error(f"Failed to process message: {e}")
                    continue
        
        # Final progress update
        if self.progress_tracker and messages_data:
            self.progress_tracker.update_progress(
                len(messages_data), len(messages_data), 'processing_messages',
                f"Completed processing {stats['total']} messages"
            )
        
        return stats
    
    def _store_message(
        self,
        msg_data: Dict[str, Any],
        conversation: Conversation
    ) -> tuple[Optional[Message], bool]:
        """
        Store a single message
        
        Returns:
            Tuple of (Message instance or None, created boolean)
        """
        try:
            # Format message
            formatted = self.message_formatter.format_incoming_message(msg_data)
            
            # Determine direction
            direction_str = determine_message_direction(
                msg_data,
                'whatsapp',
                self.whatsapp_service.account_identifier
            )
            direction = 'inbound' if direction_str == 'in' else 'outbound'
            
            # Extract external ID
            external_id = msg_data.get('id') or msg_data.get('provider_id')
            if not external_id:
                logger.warning("Message has no external ID")
                return None, False
            
            # Parse the WhatsApp message timestamp
            whatsapp_timestamp = self._parse_message_date(msg_data)
            
            # Try to get existing message
            try:
                message = Message.objects.get(
                    external_message_id=external_id,
                    conversation=conversation
                )
                # Update existing message
                message.channel = self.channel
                message.direction = direction
                message.content = formatted.get('content', '')
                message.status = self._map_message_status(msg_data)
                message.sent_at = whatsapp_timestamp
                message.metadata = {
                    'api_data': msg_data,
                    'synced_from': 'message_sync_service',
                    'sync_time': timezone.now().isoformat(),
                    'original_timestamp': msg_data.get('timestamp')
                }
                message.save(update_fields=['channel', 'direction', 'content', 'status', 'sent_at', 'metadata'])
                
                # Update created_at separately using raw SQL to bypass Django's auto_now protection
                if whatsapp_timestamp:
                    from django.db import connection
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "UPDATE communications_message SET created_at = %s WHERE id = %s",
                            [whatsapp_timestamp, message.id]
                        )
                created = False
            except Message.DoesNotExist:
                # Create new message - first create with defaults, then update created_at
                message = Message(
                    external_message_id=external_id,
                    conversation=conversation,
                    channel=self.channel,
                    direction=direction,
                    content=formatted.get('content', ''),
                    status=self._map_message_status(msg_data),
                    sent_at=whatsapp_timestamp,
                    metadata={
                        'api_data': msg_data,
                        'synced_from': 'message_sync_service',
                        'sync_time': timezone.now().isoformat(),
                        'original_timestamp': msg_data.get('timestamp')
                    }
                )
                message.save()
                
                # Update created_at using raw SQL to bypass Django's auto_now_add
                if whatsapp_timestamp:
                    from django.db import connection
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "UPDATE communications_message SET created_at = %s WHERE id = %s",
                            [whatsapp_timestamp, message.id]
                        )
                created = True
            
            return message, created
            
        except Exception as e:
            logger.error(f"Failed to store message: {e}")
            return None, False
    
    def _parse_message_date(self, msg_data: Dict[str, Any]) -> Optional[datetime]:
        """Parse message timestamp"""
        timestamp = msg_data.get('timestamp') or msg_data.get('created_at')
        if timestamp:
            try:
                if isinstance(timestamp, str):
                    return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                elif isinstance(timestamp, (int, float)):
                    return datetime.fromtimestamp(timestamp, tz=timezone.utc)
            except Exception as e:
                logger.debug(f"Failed to parse timestamp {timestamp}: {e}")
        return None
    
    def _map_message_status(self, msg_data: Dict[str, Any]) -> str:
        """Map API status to our message status"""
        api_status = msg_data.get('status', '').lower()
        
        status_map = {
            'sent': MessageStatus.SENT,
            'delivered': MessageStatus.DELIVERED,
            'read': MessageStatus.READ,
            'failed': MessageStatus.FAILED,
            'pending': MessageStatus.PENDING
        }
        
        return status_map.get(api_status, MessageStatus.DELIVERED)
    
    def _update_conversation_from_messages(
        self,
        conversation: Conversation,
        messages_data: List[Dict[str, Any]]
    ) -> None:
        """Update conversation metadata from messages"""
        try:
            if messages_data:
                # Update last message time
                latest_msg = max(
                    messages_data,
                    key=lambda m: self._parse_message_date(m) or datetime.min.replace(tzinfo=timezone.utc)
                )
                last_msg_time = self._parse_message_date(latest_msg)
                
                if last_msg_time and (
                    not conversation.last_message_at or
                    last_msg_time > conversation.last_message_at
                ):
                    conversation.last_message_at = last_msg_time
                
                # Update message count
                conversation.message_count = Message.objects.filter(
                    conversation=conversation
                ).count()
                
                # Update unread count (messages not marked as read)
                conversation.unread_count = Message.objects.filter(
                    conversation=conversation,
                    direction='inbound',
                    status__in=[MessageStatus.SENT, MessageStatus.DELIVERED]
                ).count()
                
                conversation.save()
                
        except Exception as e:
            logger.error(f"Failed to update conversation metadata: {e}")
    
    def sync_messages_paginated(
        self,
        conversations: List[Conversation],
        max_messages_per_chat: int = 100,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Sync messages for multiple conversations with pagination
        
        Args:
            conversations: List of conversations to sync
            max_messages_per_chat: Max messages per conversation
            progress_callback: Optional callback for progress updates
            
        Returns:
            Combined statistics
        """
        total_stats = {
            'conversations_processed': 0,
            'messages_synced': 0,
            'messages_created': 0,
            'errors': []
        }
        
        for idx, conversation in enumerate(conversations):
            try:
                # Sync messages for this conversation
                conv_stats = self.sync_messages_for_conversation(
                    conversation,
                    max_messages=max_messages_per_chat
                )
                
                # Update totals
                total_stats['conversations_processed'] += 1
                total_stats['messages_synced'] += conv_stats['messages_synced']
                total_stats['messages_created'] += conv_stats['messages_created']
                total_stats['errors'].extend(conv_stats.get('errors', []))
                
                # Update progress after each conversation
                if progress_callback:
                    progress_callback(idx + 1, len(conversations))
                
                if self.progress_tracker:
                    # More detailed progress message
                    self.progress_tracker.update_progress(
                        idx + 1,
                        len(conversations),
                        'messages',
                        f"Conversation {idx + 1}/{len(conversations)}: {conv_stats['messages_synced']} messages synced"
                    )
                    
            except Exception as e:
                error_msg = f"Failed to sync messages for conversation {conversation.id}: {e}"
                logger.error(error_msg)
                total_stats['errors'].append(error_msg)
        
        return total_stats
    
    def sync_messages_for_conversation_paginated(
        self,
        conversation: Conversation,
        max_messages: int = 100,
        since_date: Optional[datetime] = None,
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """
        Sync messages for a specific conversation using pagination
        
        Args:
            conversation: Conversation to sync messages for
            max_messages: Maximum total number of messages to sync
            since_date: Only sync messages after this date
            batch_size: Number of messages per API call
            
        Returns:
            Statistics dictionary
        """
        stats = {
            'messages_synced': 0,
            'messages_created': 0,
            'messages_updated': 0,
            'errors': [],
            'api_calls': 0
        }
        
        try:
            external_id = conversation.external_thread_id
            if not external_id:
                logger.warning(f"No external ID for conversation {conversation.id}")
                return stats
            
            logger.debug(f"📨 Syncing messages for conversation {external_id[:20]} with pagination...")
            logger.debug(f"  Max messages: {max_messages}, Batch size: {batch_size}")
            
            cursor = None
            total_synced = 0
            all_messages = []
            
            # Track progress for the overall conversation
            if self.progress_tracker:
                self.progress_tracker.update_progress(
                    0, max_messages, 'fetching_messages',
                    f"Starting paginated fetch for {external_id[:20]}..."
                )
            
            # Paginate through messages
            while total_synced < max_messages:
                # Calculate batch size for this iteration
                remaining = max_messages - total_synced
                current_batch_size = min(batch_size, remaining)
                
                # Update progress before API call
                if self.progress_tracker:
                    self.progress_tracker.update_progress(
                        total_synced, max_messages, 'fetching_messages',
                        f"Fetching batch {stats['api_calls'] + 1} ({total_synced}/{max_messages} messages)..."
                    )
                
                # Fetch messages batch from API
                api_result = async_to_sync(self.whatsapp_service.client.get_messages)(
                    account_id=self.whatsapp_service.account_identifier or '',
                    conversation_id=external_id,
                    limit=current_batch_size,
                    cursor=cursor
                )
                
                stats['api_calls'] += 1
                
                if not api_result.get('success'):
                    error_msg = f"Failed to fetch messages batch {stats['api_calls']}: {api_result.get('error')}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
                    break
                
                messages_batch = api_result.get('messages', [])
                if not messages_batch:
                    logger.debug(f"  No more messages available after {stats['api_calls']} API calls")
                    break
                
                logger.debug(f"  Retrieved batch {stats['api_calls']}: {len(messages_batch)} messages")
                
                # Filter messages by date if needed
                if since_date:
                    filtered_batch = []
                    for msg in messages_batch:
                        msg_date = self._parse_message_date(msg)
                        if msg_date and msg_date >= since_date:
                            filtered_batch.append(msg)
                    messages_batch = filtered_batch
                    
                    if not messages_batch:
                        logger.debug(f"  All messages in batch filtered out by date")
                        # Still check for more messages
                        cursor = api_result.get('cursor')
                        if not cursor or not api_result.get('has_more', False):
                            break
                        continue
                
                # Add to all messages
                all_messages.extend(messages_batch)
                total_synced += len(messages_batch)
                
                # Check if we should continue
                cursor = api_result.get('cursor')
                has_more = api_result.get('has_more', False)
                
                if not cursor or not has_more or len(messages_batch) < current_batch_size:
                    logger.debug(f"  No more messages to fetch (cursor: {bool(cursor)}, has_more: {has_more})")
                    break
                
                # Log progress every few batches
                if stats['api_calls'] % 3 == 0:
                    logger.info(f"  Progress: {total_synced}/{max_messages} messages fetched in {stats['api_calls']} API calls")
            
            # Now process all collected messages
            if all_messages:
                logger.debug(f"  Processing {len(all_messages)} total messages...")
                
                if self.progress_tracker:
                    self.progress_tracker.update_progress(
                        0, len(all_messages), 'processing_messages',
                        f"Processing {len(all_messages)} messages..."
                    )
                
                # Process all messages at once
                processed_stats = self._process_messages_batch(
                    all_messages,
                    conversation,
                    since_date=None  # Already filtered above
                )
                
                # Update stats
                stats['messages_synced'] = processed_stats['total']
                stats['messages_created'] = processed_stats['created']
                stats['messages_updated'] = processed_stats['updated']
                
                # Update conversation metadata
                self._update_conversation_from_messages(conversation, all_messages)
            
            logger.info(
                f"  ✅ Synced {stats['messages_synced']} messages "
                f"({stats['messages_created']} new) in {stats['api_calls']} API calls"
            )
            
        except Exception as e:
            error_msg = f"Error in paginated sync for {conversation.id}: {e}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
        
        return stats