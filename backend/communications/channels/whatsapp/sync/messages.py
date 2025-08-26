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
            
            # Don't update progress here - it would reset visual counts
            logger.debug(f"Fetching messages for {external_id[:20]}...")
            
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
            
            # Don't update progress here - it would reset visual counts
            if messages_data:
                logger.debug(f"Processing {len(messages_data)} messages...")
            
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
            'skipped': 0,
            'errors': 0,
            'date_filtered': 0
        }
        
        logger.info(f"📦 Processing batch of {len(messages_data)} messages for conversation {conversation.external_thread_id[:20]}...")
        
        # Attendees are now synced in Phase 1.5 by comprehensive.py
        
        for idx, msg_data in enumerate(messages_data):
            try:
                # Don't call update_progress during processing - it resets the display
                # increment_stat at the end will handle the broadcast
                
                # Check date filter
                if since_date:
                    msg_date = self._parse_message_date(msg_data)
                    if msg_date and msg_date < since_date:
                        stats['skipped'] += 1
                        stats['date_filtered'] += 1
                        logger.debug(f"⏭️ SKIP: Message dated {msg_date} is before {since_date}")
                        continue
                
                # Store message with its own transaction
                with transaction.atomic():
                    message, created = self._store_message(msg_data, conversation)
                    
                    if message:
                        stats['total'] += 1
                        if created:
                            stats['created'] += 1
                        else:
                            stats['updated'] += 1
                    else:
                        stats['errors'] += 1
                        logger.debug(f"⚠️ Message not stored (likely error or skip)")
                        
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
        
        # Update cumulative stats in tracker
        if self.progress_tracker and stats['total'] > 0:
            logger.info(f"💬 INCREMENTING messages_synced by {stats['total']}")
            self.progress_tracker.increment_stat('messages_synced', stats['total'])
            
            # Don't update progress here - increment_stat already broadcasts the update
            logger.debug(f"Completed processing {stats['total']} messages")
        
        # Log batch processing summary
        logger.info(f"📊 Batch processing complete:")
        logger.info(f"   Input: {len(messages_data)} messages")
        logger.info(f"   Stored: {stats['total']} ({stats['created']} new, {stats['updated']} updated)")
        logger.info(f"   Skipped: {stats['skipped']} (date filtered: {stats.get('date_filtered', 0)})")
        logger.info(f"   Errors: {stats.get('errors', 0)}")
        
        if stats['total'] < len(messages_data):
            missing = len(messages_data) - stats['total'] - stats.get('skipped', 0)
            if missing > 0:
                logger.warning(f"⚠️ MISSING: {missing} messages not accounted for!")
        
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
                logger.warning(f"🚫 SKIP: Message has no external ID - data keys: {list(msg_data.keys())[:10]}")
                return None, False
            
            # Parse the WhatsApp message timestamp
            whatsapp_timestamp = self._parse_message_date(msg_data)
            
            # Try to get existing message
            try:
                message = Message.objects.get(
                    external_message_id=external_id,
                    conversation=conversation
                )
                # Log duplicate detection
                logger.debug(f"📝 UPDATE: Message {external_id} already exists - updating")
                
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
                    try:
                        from django.db import connection
                        with connection.cursor() as cursor:
                            cursor.execute(
                                "UPDATE communications_message SET created_at = %s WHERE id = %s",
                                [whatsapp_timestamp, message.id]
                            )
                    except Exception as sql_error:
                        logger.debug(f"Could not update created_at timestamp: {sql_error}")
                created = False
            except Message.DoesNotExist:
                # Log new message creation
                logger.debug(f"✅ CREATE: New message {external_id} - {whatsapp_timestamp}")
                
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
                    try:
                        from django.db import connection
                        with connection.cursor() as cursor:
                            cursor.execute(
                                "UPDATE communications_message SET created_at = %s WHERE id = %s",
                                [whatsapp_timestamp, message.id]
                            )
                    except Exception as sql_error:
                        logger.debug(f"Could not update created_at timestamp: {sql_error}")
                created = True
            
            return message, created
            
        except Exception as e:
            logger.error(f"❌ ERROR storing message {external_id if 'external_id' in locals() else 'unknown'}: {e}")
            logger.error(f"   Message data sample: {str(msg_data)[:200]}")
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
        
        # If we have an explicit status, use it
        if api_status in status_map:
            return status_map[api_status]
        
        # For synced messages without explicit status, mark as READ
        # This prevents all historical messages from appearing as unread
        # New incoming messages via webhook will have proper status
        return MessageStatus.READ
    
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
                
                # Don't call update_progress - rely on increment_stat for broadcasting
                logger.debug(f"Conversation {idx + 1}/{len(conversations)}: {conv_stats['messages_synced']} messages synced")
                    
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
            
            logger.info(f"📨 Starting paginated sync for conversation {external_id[:20]} - target: {max_messages} messages")
            
            cursor = None
            total_synced = 0
            all_messages = []
            last_cursor = None  # Track the last cursor for debugging
            
            # Don't update progress here - it would reset visual counts
            logger.debug(f"Starting paginated fetch for {external_id[:20]}...")
            
            # Paginate through messages - continue until we have enough OR no more available
            while total_synced < max_messages:
                # Calculate batch size for this iteration
                remaining = max_messages - total_synced
                current_batch_size = min(batch_size, remaining)
                
                # Log API calls for debugging pagination
                logger.info(f"  📡 API call {stats['api_calls'] + 1}: fetching up to {current_batch_size} messages (have {total_synced}/{max_messages}, cursor={cursor is not None})")
                
                # Don't update progress during fetching - just log
                logger.debug(f"Fetching batch {stats['api_calls'] + 1} ({total_synced}/{max_messages} messages)...")
                
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
                    logger.debug(f"  No messages in batch {stats['api_calls']} - stopping")
                    break
                
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
                last_cursor = cursor  # Save for debugging
                
                # Log pagination details for debugging
                logger.info(f"  📦 Batch {stats['api_calls']} result: got {len(messages_batch)} messages, total={total_synced}, cursor={cursor is not None}, has_more={has_more}")
                
                # Check for potential issues
                if not has_more and len(messages_batch) == current_batch_size:
                    logger.warning(f"  ⚠️ SUSPICIOUS: Got full batch of {len(messages_batch)} messages but has_more=False!")
                
                # Continue pagination if has_more is True (which now correctly reflects cursor presence)
                if not has_more:
                    logger.warning(f"  🛑 API says no more messages - stopping at {total_synced}/{max_messages} (cursor={cursor})")
                    if total_synced < max_messages:
                        logger.error(f"  ❌ INCOMPLETE: Only got {total_synced}/{max_messages} messages for {external_id[:20]}")
                    break
            
            # Only log if there's an issue
            if total_synced < max_messages and last_cursor:
                logger.warning(f"  ⚠️ PAGINATION ISSUE: Stopped at {total_synced} with cursor still present!")
            
            # Now process all collected messages
            if all_messages:
                logger.info(f"  📊 Total API messages fetched: {len(all_messages)}")
                logger.debug(f"  Processing {len(all_messages)} total messages...")
                
                # Don't call update_progress with 0 here - it resets the visual progress
                logger.info(f"  Starting to process {len(all_messages)} messages...")
                
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
                # Keep errors as a list, but track error count separately
                error_count = processed_stats.get('errors', 0)
                if error_count > 0:
                    stats['errors'].append(f"Failed to process {error_count} messages")
                stats['skipped'] = processed_stats.get('skipped', 0)
                
                # Log the final results
                logger.info(f"  ✅ Sync complete for {conversation.external_thread_id[:20]}:")
                logger.info(f"     - API fetched: {len(all_messages)} messages")
                logger.info(f"     - DB stored: {stats['messages_synced']} messages")
                logger.info(f"     - Created: {stats['messages_created']}, Updated: {stats['messages_updated']}")
                logger.info(f"     - Errors: {len(stats['errors'])}, Skipped: {stats['skipped']}")
                
                if len(all_messages) != stats['messages_synced']:
                    discrepancy = len(all_messages) - stats['messages_synced']
                    logger.error(f"  ❌ DISCREPANCY: {discrepancy} messages lost between API and DB!")
                    logger.error(f"     This explains why only {stats['messages_synced']} of {len(all_messages)} messages are saved")
                
                # Update conversation metadata
                self._update_conversation_from_messages(conversation, all_messages)
            
            # Only log if there's an issue
            if stats['messages_synced'] < max_messages and last_cursor:
                logger.warning(f"  ⚠️ Only got {stats['messages_synced']}/{max_messages} but cursor was present!")
            
        except Exception as e:
            error_msg = f"Error in paginated sync for {conversation.id}: {e}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
        
        return stats