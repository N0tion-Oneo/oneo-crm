"""
Enhanced Message Persistence Service
Provides intelligent sync operations with local-first architecture
"""
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from asgiref.sync import sync_to_async, async_to_sync
from django.db import transaction
from django.utils import timezone as django_timezone
from django.core.cache import cache
from django.contrib.auth import get_user_model

from ..models import (
    UserChannelConnection, Channel, Conversation, Message, ChatAttendee,
    MessageDirection, MessageStatus, ConversationStatus, ChannelType
)
from ..unipile_sdk import unipile_service
from core.cache import tenant_cache_key, invalidate_tenant_cache
from pipelines.models import Record

User = get_user_model()
logger = logging.getLogger(__name__)


class MessageSyncService:
    """
    Enhanced message synchronization service with local-first architecture
    Handles intelligent caching, background sync, and offline support
    """
    
    def __init__(self):
        self.unipile_service = unipile_service
        self.cache_timeout = 300  # 5 minutes for hot data
        self.conversation_list_timeout = 60   # 1 minute for conversation lists (reduced for faster refresh)
        
    # =========================================================================
    # CONVERSATION MANAGEMENT
    # =========================================================================
    
    async def get_conversations_local_first(
        self,
        channel_type: str,
        user_id: str,
        account_id: Optional[str] = None,
        limit: int = 15,
        cursor: Optional[str] = None,
        force_sync: bool = False
    ) -> Dict[str, Any]:
        """
        Get conversations with local-first strategy
        1. Check Redis cache → return if fresh
        2. Query local database → return with background sync
        3. Fallback to API → store in cache and DB
        """
        cache_key = tenant_cache_key(f"conversations:{channel_type}:{account_id}:{cursor}:{limit}")
        
        # Step 1: Check cache if not forcing sync
        if not force_sync:
            cached_data = cache.get(cache_key)
            if cached_data:
                # Debug: Log cache age to help identify stale data issues
                cache_timestamp = cached_data.get('_cache_timestamp')
                if cache_timestamp:
                    cache_age = (datetime.now(timezone.utc) - datetime.fromisoformat(cache_timestamp)).total_seconds()
                    logger.debug(f"✅ Cache hit for conversations: {cache_key} (age: {cache_age:.1f}s)")
                else:
                    logger.debug(f"✅ Cache hit for conversations: {cache_key} (no timestamp)")
                return cached_data
        
        # Step 2: Handle force_sync - use comprehensive sync when explicitly requested
        if force_sync:
            logger.debug(f"🔄 Force sync requested: running comprehensive sync for {channel_type}")
            try:
                from .comprehensive_sync import comprehensive_sync_service
                from ..models import Channel
                
                # Get the channel for comprehensive sync
                channel = await sync_to_async(Channel.objects.get)(
                    unipile_account_id=account_id,
                    channel_type=channel_type
                )
                
                # Run comprehensive sync
                stats = await comprehensive_sync_service.sync_account_comprehensive(
                    channel=channel,
                    days_back=30,
                    max_messages_per_chat=100
                )
                
                logger.debug(f"🔄 Comprehensive sync complete: {stats}")
                
                # Now get the fresh data from our database
                local_data = await self._get_conversations_from_db(
                    channel_type, user_id, account_id, limit, cursor
                )
                
                local_data['_cache_timestamp'] = datetime.now(timezone.utc).isoformat()
                local_data['_sync_stats'] = stats
                cache.set(cache_key, local_data, self.conversation_list_timeout)
                
                logger.debug(f"🔄 Force sync complete: {len(local_data['conversations'])} conversations after comprehensive sync")
                return local_data
                
            except Exception as e:
                logger.error(f"Comprehensive sync failed, falling back to local data: {e}")
                # Continue to local data if comprehensive sync fails
        
        # Step 3: Query local database - ALWAYS return local data (local-first architecture)
        try:
            local_data = await self._get_conversations_from_db(
                channel_type, user_id, account_id, limit, cursor
            )
            
            # Add cache timestamp and cache local data
            local_data['_cache_timestamp'] = datetime.now(timezone.utc).isoformat()
            cache.set(cache_key, local_data, self.conversation_list_timeout)
            
            # Schedule background sync for fresh data (but don't wait for it)
            if not force_sync:
                self._schedule_background_sync(channel_type, user_id, account_id)
            
            logger.debug(f"📄 Local-first response: {len(local_data['conversations'])} conversations from database")
            return local_data
                
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            # Even if DB fails, return empty result instead of hitting API
            return {'conversations': [], 'has_more': False, 'cursor': None}
    
    async def _get_conversations_from_db(
        self,
        channel_type: str,
        user_id: str,
        account_id: Optional[str] = None,
        limit: int = 15,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """Query conversations from local database with optimized queries"""
        
        # Get user's channel connections
        connections = await sync_to_async(list)(
            UserChannelConnection.objects.filter(
                user_id=user_id,
                channel_type=channel_type,
                is_active=True
            ).select_related('user')
        )
        
        if not connections:
            return {'conversations': [], 'has_more': False, 'cursor': None}
        
        # Filter by account if specified
        if account_id:
            connections = [conn for conn in connections if conn.unipile_account_id == account_id]
        
        conversations = []
        
        for connection in connections:
            # Get conversations for this connection with latest message
            db_conversations = await sync_to_async(list)(
                Conversation.objects.filter(
                    channel__unipile_account_id=connection.unipile_account_id,
                    channel__channel_type=channel_type,
                    status=ConversationStatus.ACTIVE
                ).select_related('channel', 'primary_contact_record')
                .prefetch_related('messages')
                .order_by('-last_message_at')[:limit]
            )
            
            for conv in db_conversations:
                # Refresh conversation from database to get latest timestamp updates
                await sync_to_async(conv.refresh_from_db)(fields=['last_message_at', 'message_count'])
                
                # Get latest message
                latest_message = await sync_to_async(
                    lambda: conv.messages.order_by('-created_at').first()
                )()
                
                # Use the actual latest message timestamp for consistency
                # This ensures we always use the most recent message time
                actual_last_message_date = latest_message.created_at if latest_message else conv.last_message_at
                
                # Debug timestamp consistency
                if latest_message and conv.last_message_at:
                    time_diff = abs((latest_message.created_at - conv.last_message_at).total_seconds())
                    if time_diff > 60:  # More than 1 minute difference
                        logger.warning(f"Timestamp mismatch in conversation {conv.id}: "
                                     f"latest_message.created_at={latest_message.created_at} vs "
                                     f"conv.last_message_at={conv.last_message_at} (diff: {time_diff}s)")
                
                # Get attendees for this specific conversation
                attendees = await self._get_conversation_attendees(conv)
                logger.debug(f"Conversation {conv.external_thread_id}: Found {len(attendees)} attendees for this specific chat")
                
                conversation_data = {
                    'id': str(conv.external_thread_id or conv.id),
                    'provider_chat_id': conv.external_thread_id,
                    'name': conv.subject or 'Unknown',
                    'is_group': conv.metadata.get('is_group', False),
                    'is_muted': conv.metadata.get('is_muted', False),
                    'is_pinned': conv.metadata.get('is_pinned', False),
                    'is_archived': conv.status == ConversationStatus.ARCHIVED,
                    'unread_count': conv.metadata.get('unread_count', 0),
                    'last_message_date': actual_last_message_date.isoformat() if actual_last_message_date else None,
                    'attendees': attendees,
                    'latest_message': None,
                    'account_id': connection.unipile_account_id,
                    'member_count': conv.metadata.get('member_count')
                }
                
                # Add latest message if available
                if latest_message:
                    # Get actual message timestamp from metadata (not sync time)
                    latest_msg_date = None
                    if latest_message.metadata and 'raw_data' in latest_message.metadata:
                        latest_msg_date = latest_message.metadata['raw_data'].get('timestamp')
                    
                    # Fallback to received_at for inbound or sent_at for outbound
                    if not latest_msg_date:
                        if latest_message.direction == MessageDirection.OUTBOUND and latest_message.sent_at:
                            latest_msg_date = latest_message.sent_at.isoformat()
                        elif latest_message.direction == MessageDirection.INBOUND and latest_message.received_at:
                            latest_msg_date = latest_message.received_at.isoformat()
                        else:
                            latest_msg_date = latest_message.created_at.isoformat()
                    
                    conversation_data['latest_message'] = {
                        'id': str(latest_message.id),
                        'text': latest_message.content,
                        'type': latest_message.metadata.get('type', 'text'),
                        'direction': 'out' if latest_message.direction == MessageDirection.OUTBOUND else 'in',
                        'date': latest_msg_date,
                        'status': latest_message.status,
                        'chat_id': conversation_data['id'],
                        'attendee_id': latest_message.metadata.get('attendee_id'),
                        'account_id': connection.unipile_account_id
                    }
                
                conversations.append(conversation_data)
        
        # Sort by last message date
        conversations.sort(key=lambda x: x.get('last_message_date') or '', reverse=True)
        
        return {
            'conversations': conversations[:limit],
            'has_more': len(conversations) == limit,
            'cursor': str(len(conversations)) if len(conversations) == limit else None
        }
    
    
    
    async def _get_conversation_attendees(self, conversation: Conversation) -> List[Dict[str, Any]]:
        """
        Get attendees for a specific conversation from ChatAttendee table
        For 1-on-1 chats, tries to identify the single relevant attendee
        """
        try:
            # Get all attendees for this channel
            all_attendees = await sync_to_async(list)(
                ChatAttendee.objects.filter(channel=conversation.channel)
            )
            
            if not all_attendees:
                return []
            
            # For WhatsApp 1-on-1 chats, try to identify the specific attendee
            chat_id = conversation.external_thread_id
            conversation_subject = conversation.subject or ""
            relevant_attendees = []
            
            # Method 1: Try to match by conversation subject/name
            for att in all_attendees:
                # Skip account owner and status@broadcast
                if att.is_self or att.provider_id == 'status@broadcast':
                    continue
                
                # Check if attendee name matches conversation subject
                if att.name and conversation_subject:
                    if att.name.lower() in conversation_subject.lower() or conversation_subject.lower() in att.name.lower():
                        relevant_attendees.append(att)
                        logger.debug(f"Matched attendee by name: {att.name} <-> {conversation_subject}")
                        break
            
            # Method 2: If no name match, try phone number matching (fallback)
            if not relevant_attendees:
                for att in all_attendees:
                    # Skip account owner and status@broadcast
                    if att.is_self or att.provider_id == 'status@broadcast':
                        continue
                    
                    # For WhatsApp, try to match the chat_id with attendee's provider_id
                    if att.provider_id and chat_id:
                        # Extract phone from WhatsApp JID
                        if '@s.whatsapp.net' in att.provider_id:
                            attendee_phone = att.provider_id.split('@s.whatsapp.net')[0]
                        else:
                            attendee_phone = att.provider_id
                        
                        # Check if chat_id contains phone or vice versa
                        if attendee_phone in chat_id or chat_id in attendee_phone:
                            relevant_attendees.append(att)
                            logger.debug(f"Matched attendee by phone: {attendee_phone} <-> {chat_id}")
                            break
            
            # If no specific match, return empty array to avoid showing all attendees
            if not relevant_attendees:
                logger.debug(f"No specific attendee found for chat {chat_id} (subject: {conversation_subject}), returning empty array")
                return []
            
            # Return the matched attendees
            return [
                {
                    'id': att.external_attendee_id,
                    'name': att.name,
                    'provider_id': att.provider_id,
                    'picture_url': att.picture_url,
                    'is_self': att.is_self,
                    'metadata': att.metadata
                }
                for att in relevant_attendees
            ]
            
        except Exception as e:
            logger.warning(f"Failed to get attendees for conversation {conversation.id}: {e}")
            return []
    
    # =========================================================================
    # CACHE MANAGEMENT
    # =========================================================================
    
    def _invalidate_conversation_cache(self, channel_type: str, account_id: Optional[str] = None):
        """Invalidate conversation cache"""
        pattern = f"conversations:{channel_type}"
        if account_id:
            pattern += f":{account_id}"
        invalidate_tenant_cache(pattern)
    
    async def _store_message_from_data(
        self,
        msg_data: Dict[str, Any],
        conversation: Conversation,
        channel: Channel
    ):
        """Store a message from API data"""
        
        try:
            direction = MessageDirection.OUTBOUND if msg_data.get('direction') == 'out' else MessageDirection.INBOUND
            
            message, created = await sync_to_async(Message.objects.get_or_create)(
                external_message_id=msg_data['id'],
                channel=channel,
                defaults={
                    'conversation': conversation,
                    'direction': direction,
                    'content': msg_data.get('text', ''),
                    'status': msg_data.get('status', MessageStatus.SENT),
                    'sent_at': datetime.fromisoformat(msg_data['date'].replace('Z', '+00:00')) if msg_data.get('date') else django_timezone.now(),
                    'metadata': {
                        'type': msg_data.get('type', 'text'),
                        'attendee_id': msg_data.get('attendee_id'),
                        'account_id': msg_data.get('account_id')
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to store message {msg_data.get('id')}: {e}")
    
    # =========================================================================
    # ACCOUNT SYNC METHODS
    # =========================================================================
    
    async def sync_account_messages(
        self,
        connection_id: str,
        initial_sync: bool = False,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Sync messages for a specific account connection
        Used by Celery tasks to populate/update local database
        """
        try:
            from ..models import UserChannelConnection
            
            # Get the connection (use sync_to_async for database queries)
            connection = await sync_to_async(
                UserChannelConnection.objects.filter(id=connection_id).first
            )()
            if not connection:
                return {'success': False, 'error': 'Connection not found'}
            
            logger.info(f"Starting sync for connection {connection_id} ({connection.channel_type})")
            
            # Get user ID safely
            user_id = await sync_to_async(lambda: str(connection.user.id))()
            
            # Step 1: Sync conversations
            conversations_result = await self.get_conversations_local_first(
                channel_type=connection.channel_type,
                user_id=user_id,
                account_id=connection.unipile_account_id,
                limit=50,  # Sync more conversations
                force_sync=True  # Always fetch from API for sync
            )
            
            conversations_synced = len(conversations_result.get('conversations', []))
            messages_synced = 0
            
            # Step 2: For each conversation, sync recent messages
            for conv_data in conversations_result.get('conversations', []):
                conv_id = conv_data.get('id')
                if conv_id:
                    try:
                        messages_result = await self.get_messages_local_first(
                            conversation_id=conv_id,
                            channel_type=connection.channel_type,
                            limit=50 if initial_sync else 20,
                            force_sync=True  # Always fetch from API for sync
                        )
                        messages_synced += len(messages_result.get('messages', []))
                        
                    except Exception as msg_error:
                        logger.warning(f"Failed to sync messages for conversation {conv_id}: {msg_error}")
                        continue
            
            logger.info(f"Sync completed for {connection_id}: {conversations_synced} conversations, {messages_synced} messages")
            
            return {
                'success': True,
                'conversations_synced': conversations_synced,
                'messages_synced': messages_synced,
                'connection_id': connection_id
            }
            
        except Exception as e:
            logger.error(f"Account sync failed for {connection_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'connection_id': connection_id
            }

    async def sync_all_active_connections(self) -> Dict[str, Any]:
        """
        Sync messages for all active connections
        Used by periodic background tasks
        """
        try:
            from ..models import UserChannelConnection
            
            # Get active connections (use sync_to_async for database queries)
            active_connections = await sync_to_async(list)(
                UserChannelConnection.objects.filter(
                    is_active=True,
                    account_status='active'
                )
            )
            
            total_conversations = 0
            total_messages = 0
            synced_connections = 0
            
            for connection in active_connections:
                try:
                    result = await self.sync_account_messages(
                        connection_id=str(connection.id),
                        initial_sync=False,
                        days_back=7  # Only sync recent messages for periodic sync
                    )
                    
                    if result.get('success'):
                        total_conversations += result.get('conversations_synced', 0)
                        total_messages += result.get('messages_synced', 0)
                        synced_connections += 1
                        
                except Exception as conn_error:
                    logger.error(f"Failed to sync connection {connection.id}: {conn_error}")
                    continue
            
            logger.info(f"Bulk sync completed: {synced_connections} connections, {total_conversations} conversations, {total_messages} messages")
            
            return {
                'success': True,
                'synced_connections': synced_connections,
                'total_conversations': total_conversations,
                'total_messages': total_messages
            }
            
        except Exception as e:
            logger.error(f"Bulk sync failed: {e}")
            return {'success': False, 'error': str(e)}

    # =========================================================================
    # CACHE MANAGEMENT
    # =========================================================================
    
    def invalidate_conversation_cache(self, channel_type: str, account_id: Optional[str] = None):
        """Invalidate conversation cache for a channel/account"""
        pattern = f"conversations:{channel_type}"
        if account_id:
            pattern += f":{account_id}"
        invalidate_tenant_cache(pattern)
    
    def _schedule_background_sync(self, channel_type: str, user_id: str, account_id: Optional[str] = None):
        """Schedule background sync task"""
        from ..tasks import sync_conversations_background
        
        # Use Celery to schedule background sync
        sync_conversations_background.delay(
            channel_type=channel_type,
            user_id=user_id,
            account_id=account_id
        )
    
    # =========================================================================
    # MESSAGE OPERATIONS
    # =========================================================================
    
    async def get_messages_local_first(
        self,
        conversation_id: str,
        channel_type: str,
        limit: int = 50,
        cursor: Optional[str] = None,
        force_sync: bool = False
    ) -> Dict[str, Any]:
        """Get messages with local-first strategy"""
        
        cache_key = tenant_cache_key(f"messages:{conversation_id}:{cursor}:{limit}")
        
        # Check cache
        if not force_sync:
            cached_data = cache.get(cache_key)
            if cached_data:
                return cached_data
        
        # Query local database ONLY - no API fallback
        try:
            local_data = await self._get_messages_from_db(conversation_id, limit, cursor)
            cache.set(cache_key, local_data, self.cache_timeout)
            return local_data
        except Exception as e:
            logger.error(f"Failed to get messages from DB: {e}")
            # Return empty result instead of falling back to API
            return {
                'messages': [],
                'cursor': None,
                'has_more': False,
                'source': 'database_error'
            }
    
    async def _get_messages_from_db(
        self,
        conversation_id: str,
        limit: int = 50,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get messages from local database"""
        
        try:
            # Find conversation
            conversation = await sync_to_async(Conversation.objects.get)(
                external_thread_id=conversation_id
            )
            
            # Get messages with pagination
            messages_query = conversation.messages.order_by('-created_at')
            
            if cursor:
                # Implement cursor-based pagination
                try:
                    cursor_dt = datetime.fromisoformat(cursor)
                    messages_query = messages_query.filter(created_at__lt=cursor_dt)
                except ValueError:
                    pass  # Invalid cursor, ignore
            
            messages = await sync_to_async(list)(messages_query[:limit])
            
            message_data = []
            for msg in messages:
                # Get actual message timestamp from metadata (not sync time)
                actual_date = None
                if msg.metadata and 'raw_data' in msg.metadata:
                    actual_date = msg.metadata['raw_data'].get('timestamp')
                
                # Fallback to received_at for inbound or sent_at for outbound
                if not actual_date:
                    if msg.direction == MessageDirection.OUTBOUND and msg.sent_at:
                        actual_date = msg.sent_at.isoformat()
                    elif msg.direction == MessageDirection.INBOUND and msg.received_at:
                        actual_date = msg.received_at.isoformat()
                    else:
                        actual_date = msg.created_at.isoformat()
                
                message_data.append({
                    'id': str(msg.id),
                    'text': msg.content,
                    'type': msg.metadata.get('type', 'text'),
                    'direction': 'out' if msg.direction == MessageDirection.OUTBOUND else 'in',
                    'date': actual_date,
                    'status': msg.status,
                    'chat_id': conversation_id,
                    'attendee_id': msg.metadata.get('attendee_id'),
                    'attachments': msg.metadata.get('attachments', []),
                    'account_id': msg.metadata.get('account_id')
                })
            
            return {
                'messages': message_data,
                'has_more': len(messages) == limit,
                'cursor': messages[-1].created_at.isoformat() if messages else None
            }
            
        except Conversation.DoesNotExist:
            return {'messages': [], 'has_more': False, 'cursor': None}
    
    async def _get_messages_from_api(
        self,
        conversation_id: str,
        channel_type: str,
        limit: int = 50,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get messages from UniPile API"""
        
        try:
            client = self.unipile_service.get_client()
            
            messages_data = await client.messaging.get_all_messages(
                chat_id=conversation_id,
                limit=limit,
                cursor=cursor
            )
            
            messages = []
            for msg_data in messages_data.get('items', []):
                message = {
                    'id': msg_data.get('id'),
                    'text': msg_data.get('text') or msg_data.get('content', ''),
                    'type': msg_data.get('type', 'text'),
                    'direction': 'out' if msg_data.get('from_me') else 'in',
                    'date': msg_data.get('date') or msg_data.get('timestamp'),
                    'status': msg_data.get('status', 'sent'),
                    'chat_id': conversation_id,
                    'attendee_id': msg_data.get('from') if not msg_data.get('from_me') else None,
                    'attachments': msg_data.get('attachments', []),
                    'account_id': msg_data.get('account_id')
                }
                messages.append(message)
            
            return {
                'messages': messages,
                'has_more': len(messages) == limit and messages_data.get('cursor'),
                'cursor': messages_data.get('cursor')
            }
            
        except Exception as e:
            logger.error(f"Failed to get messages from API: {e}")
            return {'messages': [], 'has_more': False, 'cursor': None}
    
    async def _store_messages_in_db(
        self,
        messages: List[Dict[str, Any]],
        conversation_id: str,
        channel_type: str
    ):
        """Store messages from API in local database for future local-first access"""
        
        if not messages:
            logger.debug(f"No messages to store for conversation {conversation_id}")
            return
        
        try:
            # Find the conversation first
            conversation = await sync_to_async(
                Conversation.objects.filter(external_thread_id=conversation_id).first
            )()
            
            if not conversation:
                logger.warning(f"Conversation {conversation_id} not found, cannot store messages")
                return
            
            # Get the channel for this conversation
            channel = conversation.channel
            messages_created = 0
            messages_updated = 0
            
            for msg_data in messages:
                try:
                    external_msg_id = msg_data.get('id')
                    if not external_msg_id:
                        logger.warning(f"Message missing ID, skipping: {msg_data}")
                        continue
                    
                    # Determine message direction
                    direction = MessageDirection.OUTBOUND if msg_data.get('direction') == 'out' else MessageDirection.INBOUND
                    
                    # Parse message date
                    msg_date = msg_data.get('date')
                    if msg_date:
                        try:
                            if isinstance(msg_date, str):
                                # Handle ISO format dates
                                if msg_date.endswith('Z'):
                                    msg_date = msg_date.replace('Z', '+00:00')
                                sent_at = datetime.fromisoformat(msg_date)
                            else:
                                sent_at = msg_date
                        except (ValueError, TypeError) as date_error:
                            logger.warning(f"Invalid date format for message {external_msg_id}: {msg_date}, using current time")
                            sent_at = django_timezone.now()
                    else:
                        sent_at = django_timezone.now()
                    
                    # Create or update message
                    message, created = await sync_to_async(Message.objects.get_or_create)(
                        external_message_id=external_msg_id,
                        channel=channel,
                        defaults={
                            'conversation': conversation,
                            'direction': direction,
                            'content': msg_data.get('text', '') or msg_data.get('content', ''),
                            'status': msg_data.get('status', MessageStatus.DELIVERED),
                            'sent_at': sent_at,
                            'created_at': sent_at,  # Use message timestamp for created_at
                            'metadata': {
                                'type': msg_data.get('type', 'text'),
                                'attendee_id': msg_data.get('attendee_id'),
                                'account_id': msg_data.get('account_id'),
                                'attachments': msg_data.get('attachments', []),
                                'from_me': msg_data.get('direction') == 'out'
                            }
                        }
                    )
                    
                    if created:
                        messages_created += 1
                        logger.debug(f"✅ Created message {external_msg_id} in conversation {conversation_id}")
                    else:
                        # Update existing message if needed
                        updated = False
                        if message.content != (msg_data.get('text', '') or msg_data.get('content', '')):
                            message.content = msg_data.get('text', '') or msg_data.get('content', '')
                            updated = True
                        
                        if message.status != msg_data.get('status', MessageStatus.DELIVERED):
                            message.status = msg_data.get('status', MessageStatus.DELIVERED)
                            updated = True
                        
                        if updated:
                            await sync_to_async(message.save)()
                            messages_updated += 1
                            logger.debug(f"📝 Updated message {external_msg_id} in conversation {conversation_id}")
                
                except Exception as msg_error:
                    logger.error(f"Failed to store individual message {msg_data.get('id', 'unknown')}: {msg_error}")
                    continue
            
            # Update conversation metadata
            if messages_created > 0 or messages_updated > 0:
                # Get the latest message timestamp to update conversation
                latest_message = await sync_to_async(
                    lambda: conversation.messages.order_by('-created_at').first()
                )()
                
                if latest_message:
                    conversation.last_message_at = latest_message.created_at
                    conversation.message_count = await sync_to_async(
                        lambda: conversation.messages.count()
                    )()
                    await sync_to_async(conversation.save)(update_fields=['last_message_at', 'message_count'])
                
                logger.info(f"💾 Stored {messages_created} new messages, updated {messages_updated} messages for conversation {conversation_id}")
            else:
                logger.debug(f"No new messages to store for conversation {conversation_id}")
        
        except Exception as e:
            logger.error(f"Failed to store messages in database for conversation {conversation_id}: {e}")


# Initialize global service instance
message_sync_service = MessageSyncService()