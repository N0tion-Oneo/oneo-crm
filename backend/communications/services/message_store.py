"""
MessageStore - Database operations with intelligent cache invalidation
Provides high-performance CRUD operations for messages and conversations
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from django.db import transaction, models
from django.utils import timezone as django_timezone
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async

from ..models import (
    Channel, Conversation, Message, UserChannelConnection,
    MessageDirection, MessageStatus, ConversationStatus, ChannelType
)
from .conversation_cache import conversation_cache
from .conversation_naming import conversation_naming_service
from core.cache import tenant_cache_key
from pipelines.models import Record

User = get_user_model()
logger = logging.getLogger(__name__)


class MessageStore:
    """
    High-performance message and conversation storage with intelligent caching
    """
    
    def __init__(self):
        self.cache = conversation_cache
    
    # =========================================================================
    # CONVERSATION OPERATIONS
    # =========================================================================
    
    async def get_conversations(
        self,
        channel_type: str,
        user_id: str,
        account_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 15,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get conversations with optimized database queries"""
        
        try:
            # Get user's channel connections
            connections = await sync_to_async(list)(
                UserChannelConnection.objects.filter(
                    user_id=user_id,
                    channel_type=channel_type,
                    is_active=True
                ).select_related('user')
            )
            
            if not connections:
                return {'conversations': [], 'total': 0, 'has_more': False}
            
            # Filter by account if specified
            if account_id:
                connections = [conn for conn in connections if conn.unipile_account_id == account_id]
            
            if not connections:
                return {'conversations': [], 'total': 0, 'has_more': False}
            
            # Build query for conversations
            account_ids = [conn.unipile_account_id for conn in connections]
            
            conversations_query = Conversation.objects.filter(
                channel__unipile_account_id__in=account_ids,
                channel__channel_type=channel_type,
                channel__is_active=True
            ).select_related('channel', 'primary_contact_record')
            
            # Apply status filter
            if status:
                if status == 'unread':
                    conversations_query = conversations_query.filter(unread_count__gt=0)
                elif status == 'archived':
                    conversations_query = conversations_query.filter(status=ConversationStatus.ARCHIVED)
                else:
                    conversations_query = conversations_query.filter(status=status)
            else:
                # Default to active conversations
                conversations_query = conversations_query.filter(status=ConversationStatus.ACTIVE)
            
            # Order by last message date
            conversations_query = conversations_query.order_by('-last_message_at', '-updated_at')
            
            # Get total count for pagination
            total_count = await sync_to_async(conversations_query.count)()
            
            # Apply pagination
            conversations = await sync_to_async(list)(
                conversations_query[offset:offset + limit]
            )
            
            # Transform conversations to API format
            conversation_data = []
            for conv in conversations:
                # Mark as accessed for hot tracking
                await self._mark_conversation_accessed(conv)
                
                # Get latest message
                latest_message = await sync_to_async(
                    lambda: conv.messages.order_by('-created_at').first()
                )()
                
                conv_data = await self._serialize_conversation(conv, latest_message)
                conversation_data.append(conv_data)
            
            return {
                'conversations': conversation_data,
                'total': total_count,
                'has_more': offset + limit < total_count
            }
            
        except Exception as e:
            logger.error(f"Failed to get conversations: {e}")
            return {'conversations': [], 'total': 0, 'has_more': False}
    
    async def get_conversation_by_id(
        self,
        conversation_id: str,
        external_id: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Get a single conversation by ID"""
        
        try:
            if external_id:
                conversation = await sync_to_async(Conversation.objects.select_related('channel', 'primary_contact_record').get)(
                    external_thread_id=conversation_id
                )
            else:
                conversation = await sync_to_async(Conversation.objects.select_related('channel', 'primary_contact_record').get)(
                    id=conversation_id
                )
            
            # Mark as accessed
            await self._mark_conversation_accessed(conversation)
            
            # Get latest message
            latest_message = await sync_to_async(
                lambda: conversation.messages.order_by('-created_at').first()
            )()
            
            return await self._serialize_conversation(conversation, latest_message)
            
        except Conversation.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Failed to get conversation {conversation_id}: {e}")
            return None
    
    async def create_conversation(
        self,
        channel_type: str,
        account_id: str,
        external_thread_id: str,
        subject: str = '',
        metadata: Optional[Dict[str, Any]] = None,
        contact_info: Optional[Dict[str, Any]] = None,
        message_content: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a new conversation with smart naming"""
        
        try:
            # Get or create channel
            channel, created = await sync_to_async(Channel.objects.get_or_create)(
                unipile_account_id=account_id,
                channel_type=channel_type,
                defaults={
                    'name': f"{channel_type.title()} Account {account_id[:8]}",
                    'auth_status': 'authenticated',
                    'is_active': True
                }
            )
            
            # Generate smart conversation name if not provided
            if not subject and contact_info:
                subject = conversation_naming_service.generate_conversation_name(
                    channel_type=channel_type,
                    contact_info=contact_info,
                    message_content=message_content,
                    external_thread_id=external_thread_id
                )
            
            # Create conversation
            conversation = await sync_to_async(Conversation.objects.create)(
                channel=channel,
                external_thread_id=external_thread_id,
                subject=subject or f"Conversation {external_thread_id[:8]}",
                status=ConversationStatus.ACTIVE,
                metadata=metadata or {},
                sync_status='pending'
            )
            
            # Invalidate cache
            self.cache.invalidate_channel(channel_type, account_id)
            
            return await self._serialize_conversation(conversation)
            
        except Exception as e:
            logger.error(f"Failed to create conversation: {e}")
            return None
    
    async def update_conversation(
        self,
        conversation_id: str,
        updates: Dict[str, Any],
        external_id: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Update a conversation"""
        
        try:
            # Get conversation
            if external_id:
                conversation = await sync_to_async(Conversation.objects.select_related('channel').get)(
                    external_thread_id=conversation_id
                )
            else:
                conversation = await sync_to_async(Conversation.objects.select_related('channel').get)(
                    id=conversation_id
                )
            
            # Apply updates
            updated_fields = []
            for field, value in updates.items():
                if hasattr(conversation, field):
                    setattr(conversation, field, value)
                    updated_fields.append(field)
            
            if updated_fields:
                updated_fields.append('updated_at')
                await sync_to_async(conversation.save)(update_fields=updated_fields)
            
            # Invalidate cache
            self.cache.invalidate_conversation(conversation_id)
            self.cache.invalidate_channel(conversation.channel.channel_type, conversation.channel.unipile_account_id)
            
            return await self._serialize_conversation(conversation)
            
        except Conversation.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Failed to update conversation {conversation_id}: {e}")
            return None
    
    # =========================================================================
    # MESSAGE OPERATIONS
    # =========================================================================
    
    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 50,
        before_date: Optional[datetime] = None,
        external_id: bool = True
    ) -> Dict[str, Any]:
        """Get messages for a conversation"""
        
        try:
            # Get conversation
            if external_id:
                conversation = await sync_to_async(Conversation.objects.get)(
                    external_thread_id=conversation_id
                )
            else:
                conversation = await sync_to_async(Conversation.objects.get)(
                    id=conversation_id
                )
            
            # Build messages query
            messages_query = conversation.messages.select_related('contact_record').order_by('-created_at')
            
            # Apply date filter for pagination
            if before_date:
                messages_query = messages_query.filter(created_at__lt=before_date)
            
            # Get messages
            messages = await sync_to_async(list)(messages_query[:limit])
            
            # Serialize messages
            message_data = []
            for msg in messages:
                msg_data = await self._serialize_message(msg)
                message_data.append(msg_data)
            
            return {
                'messages': message_data,
                'has_more': len(messages) == limit,
                'cursor': messages[-1].created_at.isoformat() if messages else None
            }
            
        except Conversation.DoesNotExist:
            logger.error(f"Conversation {conversation_id} not found")
            return {'messages': [], 'has_more': False, 'cursor': None}
        except Exception as e:
            logger.error(f"Failed to get messages for {conversation_id}: {e}")
            return {'messages': [], 'has_more': False, 'cursor': None}
    
    async def create_message(
        self,
        conversation_id: str,
        content: str,
        direction: str,
        external_message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        contact_info: Optional[Dict[str, str]] = None,
        is_local_only: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Create a new message"""
        
        try:
            # Get conversation
            conversation = await sync_to_async(Conversation.objects.select_related('channel').get)(
                external_thread_id=conversation_id
            )
            
            # Map direction
            msg_direction = MessageDirection.OUTBOUND if direction == 'out' else MessageDirection.INBOUND
            
            # Create message
            message = await sync_to_async(Message.objects.create)(
                channel=conversation.channel,
                conversation=conversation,
                external_message_id=external_message_id,
                direction=msg_direction,
                content=content,
                status=MessageStatus.PENDING if is_local_only else MessageStatus.SENT,
                contact_email=contact_info.get('email', '') if contact_info else '',
                contact_phone=contact_info.get('phone', '') if contact_info else '',
                metadata=metadata or {},
                sync_status='pending',
                is_local_only=is_local_only,
                sent_at=django_timezone.now() if msg_direction == MessageDirection.OUTBOUND else None,
                received_at=django_timezone.now() if msg_direction == MessageDirection.INBOUND else None
            )
            
            # Update conversation stats
            await self._update_conversation_stats(conversation)
            
            # Invalidate cache
            self.cache.invalidate_conversation(conversation_id)
            self.cache.invalidate_channel(
                conversation.channel.channel_type, 
                conversation.channel.unipile_account_id
            )
            
            return await self._serialize_message(message)
            
        except Conversation.DoesNotExist:
            logger.error(f"Conversation {conversation_id} not found")
            return None
        except Exception as e:
            logger.error(f"Failed to create message: {e}")
            return None
    
    async def update_message_status(
        self,
        message_id: str,
        status: str,
        sync_status: Optional[str] = None,
        external_id: bool = True
    ) -> bool:
        """Update message status"""
        
        try:
            if external_id:
                message = await sync_to_async(Message.objects.select_related('conversation', 'channel').get)(
                    external_message_id=message_id
                )
            else:
                message = await sync_to_async(Message.objects.select_related('conversation', 'channel').get)(
                    id=message_id
                )
            
            # Update status
            message.status = status
            if sync_status:
                message.sync_status = sync_status
                if sync_status == 'synced':
                    message.last_synced_at = django_timezone.now()
                    message.is_local_only = False
            
            await sync_to_async(message.save)(update_fields=['status', 'sync_status', 'last_synced_at', 'is_local_only'])
            
            # Invalidate cache
            if message.conversation:
                self.cache.invalidate_conversation(message.conversation.external_thread_id)
            
            return True
            
        except Message.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Failed to update message status: {e}")
            return False
    
    # =========================================================================
    # SYNC OPERATIONS
    # =========================================================================
    
    async def get_pending_sync_conversations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get conversations that need syncing"""
        
        try:
            conversations = await sync_to_async(list)(
                Conversation.objects.filter(
                    sync_status__in=['pending', 'failed']
                ).select_related('channel')
                .order_by('last_synced_at', 'updated_at')[:limit]
            )
            
            return [await self._serialize_conversation(conv) for conv in conversations]
            
        except Exception as e:
            logger.error(f"Failed to get pending sync conversations: {e}")
            return []
    
    async def get_pending_sync_messages(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get messages that need syncing"""
        
        try:
            messages = await sync_to_async(list)(
                Message.objects.filter(
                    sync_status__in=['pending', 'failed']
                ).select_related('conversation', 'channel')
                .order_by('last_synced_at', 'created_at')[:limit]
            )
            
            return [await self._serialize_message(msg) for msg in messages]
            
        except Exception as e:
            logger.error(f"Failed to get pending sync messages: {e}")
            return []
    
    async def mark_conversation_synced(
        self,
        conversation_id: str,
        sync_status: str = 'synced',
        error_message: str = ''
    ) -> bool:
        """Mark conversation as synced"""
        
        try:
            conversation = await sync_to_async(Conversation.objects.get)(
                external_thread_id=conversation_id
            )
            
            conversation.sync_status = sync_status
            conversation.last_synced_at = django_timezone.now()
            
            if sync_status == 'failed':
                conversation.sync_error_count += 1
                conversation.sync_error_message = error_message
            else:
                conversation.sync_error_count = 0
                conversation.sync_error_message = ''
            
            await sync_to_async(conversation.save)(update_fields=[
                'sync_status', 'last_synced_at', 'sync_error_count', 'sync_error_message'
            ])
            
            return True
            
        except Conversation.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Failed to mark conversation synced: {e}")
            return False
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    async def _serialize_conversation(
        self,
        conversation: Conversation,
        latest_message: Optional[Message] = None
    ) -> Dict[str, Any]:
        """Serialize conversation to API format"""
        
        data = {
            'id': conversation.external_thread_id or str(conversation.id),
            'provider_chat_id': conversation.external_thread_id,
            'name': conversation.subject,
            'is_group': conversation.metadata.get('is_group', False),
            'is_muted': conversation.metadata.get('is_muted', False),
            'is_pinned': conversation.metadata.get('is_pinned', False),
            'is_archived': conversation.status == ConversationStatus.ARCHIVED,
            'unread_count': conversation.unread_count,
            'last_message_date': conversation.last_message_at.isoformat() if conversation.last_message_at else None,
            'attendees': conversation.metadata.get('attendees', []),
            'latest_message': None,
            'account_id': conversation.channel.unipile_account_id,
            'member_count': conversation.metadata.get('member_count'),
            'picture_url': conversation.metadata.get('picture_url'),
            'sync_status': conversation.sync_status,
            'is_hot': conversation.is_hot
        }
        
        # Add latest message if provided
        if latest_message:
            data['latest_message'] = await self._serialize_message(latest_message)
        
        return data
    
    async def _serialize_message(self, message: Message) -> Dict[str, Any]:
        """Serialize message to API format"""
        
        return {
            'id': message.external_message_id or str(message.id),
            'text': message.content,
            'type': message.metadata.get('type', 'text'),
            'direction': 'out' if message.direction == MessageDirection.OUTBOUND else 'in',
            'date': message.created_at.isoformat(),
            'status': message.status,
            'chat_id': message.conversation.external_thread_id if message.conversation else None,
            'attendee_id': message.metadata.get('attendee_id'),
            'attachments': message.metadata.get('attachments', []),
            'account_id': message.channel.unipile_account_id,
            'sync_status': message.sync_status,
            'is_local_only': message.is_local_only
        }
    
    async def _mark_conversation_accessed(self, conversation: Conversation):
        """Mark conversation as accessed for hot tracking"""
        
        try:
            # Update last accessed time
            conversation.last_accessed_at = django_timezone.now()
            
            # Mark as hot if accessed frequently
            # Simple heuristic: mark as hot if accessed in the last hour
            if conversation.last_accessed_at and (django_timezone.now() - conversation.last_accessed_at).total_seconds() < 3600:
                conversation.is_hot = True
            
            await sync_to_async(conversation.save)(update_fields=['last_accessed_at', 'is_hot'])
            
            # Update cache hot tracking
            self.cache.mark_conversation_hot(
                conversation.external_thread_id or str(conversation.id),
                conversation.channel.channel_type,
                conversation.channel.unipile_account_id
            )
            
        except Exception as e:
            logger.error(f"Failed to mark conversation as accessed: {e}")
    
    async def _update_conversation_stats(self, conversation: Conversation):
        """Update conversation statistics"""
        
        try:
            # Get latest message
            latest_message = await sync_to_async(
                lambda: conversation.messages.order_by('-created_at').first()
            )()
            
            # Update stats
            conversation.message_count = await sync_to_async(conversation.messages.count)()
            conversation.last_message_at = latest_message.created_at if latest_message else conversation.last_message_at
            
            # Update unread count for inbound messages
            if latest_message and latest_message.direction == MessageDirection.INBOUND:
                conversation.unread_count = await sync_to_async(
                    lambda: conversation.messages.filter(
                        direction=MessageDirection.INBOUND,
                        status__in=[MessageStatus.DELIVERED, MessageStatus.SENT]
                    ).count()
                )()
            
            await sync_to_async(conversation.save)(update_fields=[
                'message_count', 'last_message_at', 'unread_count'
            ])
            
        except Exception as e:
            logger.error(f"Failed to update conversation stats: {e}")


# Initialize global message store
message_store = MessageStore()