"""
WebSocket Consumers for Phase 8 Communication System
Real-time messaging and communication updates
"""
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.core.cache import cache
from asgiref.sync import sync_to_async

from .models import Conversation, Message, Channel
from .serializers import MessageSerializer, ConversationDetailSerializer
from realtime.auth import authenticate_websocket_session, extract_session_from_scope

logger = logging.getLogger(__name__)
User = get_user_model()


class ConversationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time conversation updates"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conversation_id = None
        self.conversation_group_name = None
        self.user = None
        self.is_authenticated = False
    
    async def connect(self):
        """Handle WebSocket connection"""
        try:
            # Extract conversation ID from URL
            self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
            self.conversation_group_name = f"conversation_{self.conversation_id}"
            
            # Authenticate user
            session_key = extract_session_from_scope(self.scope)
            self.user = await authenticate_websocket_session(session_key)
            
            if not self.user:
                await self.close(code=4001)  # Unauthorized
                return
            
            # Verify access to conversation
            has_access = await self._check_conversation_access()
            if not has_access:
                await self.close(code=4003)  # Forbidden
                return
            
            # Join conversation group
            await self.channel_layer.group_add(
                self.conversation_group_name,
                self.channel_name
            )
            
            self.is_authenticated = True
            await self.accept()
            
            # Send initial conversation data
            await self._send_conversation_state()
            
            # Track user presence
            await self._add_user_presence()
            
            logger.info(f"User {self.user.id} connected to conversation {self.conversation_id}")
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
            await self.close(code=4000)
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if self.is_authenticated and self.conversation_group_name:
            # Remove user presence
            await self._remove_user_presence()
            
            # Leave conversation group
            await self.channel_layer.group_discard(
                self.conversation_group_name,
                self.channel_name
            )
            
            logger.info(f"User {self.user.id if self.user else 'Unknown'} disconnected from conversation {self.conversation_id}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'message.send':
                await self._handle_send_message(data)
            elif message_type == 'message.typing':
                await self._handle_typing_indicator(data)
            elif message_type == 'message.read':
                await self._handle_message_read(data)
            elif message_type == 'conversation.assign':
                await self._handle_conversation_assignment(data)
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'error': f'Unknown message type: {message_type}'
                }))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'error': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.error(f"Message handling error: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'error': 'Internal server error'
            }))
    
    async def message_update(self, event):
        """Handle message update broadcast"""
        await self.send(text_data=json.dumps({
            'type': 'message.update',
            'message': event['message']
        }))
    
    async def conversation_update(self, event):
        """Handle conversation update broadcast"""
        await self.send(text_data=json.dumps({
            'type': 'conversation.update',
            'conversation': event['conversation']
        }))
    
    async def user_typing(self, event):
        """Handle typing indicator broadcast"""
        # Don't send typing indicators back to the sender
        if event.get('user_id') != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'user.typing',
                'user_id': event['user_id'],
                'user_name': event['user_name'],
                'is_typing': event['is_typing']
            }))
    
    async def presence_update(self, event):
        """Handle user presence update broadcast"""
        await self.send(text_data=json.dumps({
            'type': 'presence.update',
            'users_online': event['users_online']
        }))
    
    @database_sync_to_async
    def _check_conversation_access(self) -> bool:
        """Check if user has access to the conversation"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            
            # Check if user is assigned to conversation
            if conversation.assigned_to_id == self.user.id:
                return True
            
            # Check if user has access to the channel
            # This would integrate with the permission system
            return True  # Simplified for now
            
        except Conversation.DoesNotExist:
            return False
    
    async def _send_conversation_state(self):
        """Send initial conversation state to user"""
        try:
            conversation = await database_sync_to_async(
                lambda: Conversation.objects.select_related('channel', 'assigned_to').get(
                    id=self.conversation_id
                )
            )()
            
            serializer = ConversationDetailSerializer(conversation)
            
            await self.send(text_data=json.dumps({
                'type': 'conversation.state',
                'conversation': serializer.data
            }))
            
        except Exception as e:
            logger.error(f"Failed to send conversation state: {e}")
    
    async def _handle_send_message(self, data):
        """Handle sending a new message"""
        try:
            content = data.get('content', '').strip()
            if not content:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'error': 'Message content cannot be empty'
                }))
                return
            
            # Create message record
            message = await database_sync_to_async(Message.objects.create)(
                conversation_id=self.conversation_id,
                content=content,
                content_type=data.get('content_type', 'text'),
                direction='outbound',
                created_by=self.user,
                status='sent'
            )
            
            # Update conversation
            await database_sync_to_async(self._update_conversation_last_message)(message)
            
            # Serialize message
            serializer = MessageSerializer(message)
            
            # Broadcast to conversation group
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'message_update',
                    'message': serializer.data
                }
            )
            
            # Send via UniPile if configured
            await self._send_via_unipile(message)
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'error': 'Failed to send message'
            }))
    
    async def _handle_typing_indicator(self, data):
        """Handle typing indicator"""
        is_typing = data.get('is_typing', False)
        
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'user_typing',
                'user_id': str(self.user.id),
                'user_name': self.user.get_full_name(),
                'is_typing': is_typing
            }
        )
    
    async def _handle_message_read(self, data):
        """Handle message read status update"""
        try:
            message_id = data.get('message_id')
            if not message_id:
                return
            
            # Update message read status
            await database_sync_to_async(
                lambda: Message.objects.filter(
                    id=message_id,
                    conversation_id=self.conversation_id
                ).update(
                    status='read',
                    read_at=datetime.now(timezone.utc)
                )
            )()
            
            # Broadcast read status update
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'message_update',
                    'message': {
                        'id': message_id,
                        'status': 'read',
                        'read_at': datetime.now(timezone.utc).isoformat()
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to update message read status: {e}")
    
    async def _handle_conversation_assignment(self, data):
        """Handle conversation assignment"""
        try:
            user_id = data.get('user_id')
            
            # Update conversation assignment
            conversation = await database_sync_to_async(
                lambda: Conversation.objects.get(id=self.conversation_id)
            )()
            
            if user_id:
                assigned_user = await database_sync_to_async(
                    lambda: User.objects.get(id=user_id)
                )()
                conversation.assigned_to = assigned_user
                conversation.assigned_at = datetime.now(timezone.utc)
            else:
                conversation.assigned_to = None
                conversation.assigned_at = None
            
            await database_sync_to_async(conversation.save)()
            
            # Broadcast assignment update
            serializer = ConversationDetailSerializer(conversation)
            await self.channel_layer.group_send(
                self.conversation_group_name,
                {
                    'type': 'conversation_update',
                    'conversation': serializer.data
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to update conversation assignment: {e}")
    
    def _update_conversation_last_message(self, message):
        """Update conversation last message timestamp"""
        conversation = message.conversation
        conversation.last_message_at = message.created_at
        if message.direction == 'outbound':
            conversation.last_outbound_at = message.created_at
        conversation.message_count += 1
        conversation.save()
    
    async def _send_via_unipile(self, message):
        """Send message via UniPile (if configured)"""
        try:
            from .unipile_service import unipile_service
            
            conversation = await database_sync_to_async(
                lambda: message.conversation
            )()
            
            channel = await database_sync_to_async(
                lambda: conversation.channel
            )()
            
            if channel.unipile_account_id and channel.can_send_messages():
                # Get recipient from conversation participants
                participants = conversation.participants or []
                if participants:
                    recipient = participants[0].get('email')
                    
                    if recipient:
                        result = await unipile_service.send_message(
                            channel=channel,
                            recipient=recipient,
                            content=message.content,
                            thread_id=conversation.external_thread_id
                        )
                        
                        if result['success']:
                            # Update message with external ID
                            message.external_message_id = result.get('external_message_id')
                            await database_sync_to_async(message.save)()
                        else:
                            logger.error(f"UniPile send failed: {result['error']}")
            
        except Exception as e:
            logger.error(f"UniPile integration error: {e}")
    
    async def _add_user_presence(self):
        """Add user to conversation presence"""
        cache_key = f"conversation_presence_{self.conversation_id}"
        
        # Get current users
        online_users = await sync_to_async(cache.get)(cache_key, {})
        
        # Add current user
        online_users[str(self.user.id)] = {
            'name': self.user.get_full_name(),
            'connected_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Update cache (5 minute TTL)
        await sync_to_async(cache.set)(cache_key, online_users, 300)
        
        # Broadcast presence update
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'presence_update',
                'users_online': list(online_users.values())
            }
        )
    
    async def _remove_user_presence(self):
        """Remove user from conversation presence"""
        cache_key = f"conversation_presence_{self.conversation_id}"
        
        # Get current users
        online_users = await sync_to_async(cache.get)(cache_key, {})
        
        # Remove current user
        online_users.pop(str(self.user.id), None)
        
        # Update cache
        await sync_to_async(cache.set)(cache_key, online_users, 300)
        
        # Broadcast presence update
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'presence_update',
                'users_online': list(online_users.values())
            }
        )


class ChannelConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for channel-wide updates"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.channel_id = None
        self.channel_group_name = None
        self.user = None
        self.is_authenticated = False
    
    async def connect(self):
        """Handle WebSocket connection"""
        try:
            # Extract channel ID from URL
            self.channel_id = self.scope['url_route']['kwargs']['channel_id']
            self.channel_group_name = f"channel_{self.channel_id}"
            
            # Authenticate user
            session_key = extract_session_from_scope(self.scope)
            self.user = await authenticate_websocket_session(session_key)
            
            if not self.user:
                await self.close(code=4001)  # Unauthorized
                return
            
            # Verify access to channel
            has_access = await self._check_channel_access()
            if not has_access:
                await self.close(code=4003)  # Forbidden
                return
            
            # Join channel group
            await self.channel_layer.group_add(
                self.channel_group_name,
                self.channel_name
            )
            
            self.is_authenticated = True
            await self.accept()
            
            logger.info(f"User {self.user.id} connected to channel {self.channel_id}")
            
        except Exception as e:
            logger.error(f"Channel connection error: {e}")
            await self.close(code=4000)
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if self.is_authenticated and self.channel_group_name:
            # Leave channel group
            await self.channel_layer.group_discard(
                self.channel_group_name,
                self.channel_name
            )
            
            logger.info(f"User {self.user.id if self.user else 'Unknown'} disconnected from channel {self.channel_id}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'channel.sync':
                await self._handle_channel_sync()
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'error': f'Unknown message type: {message_type}'
                }))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'error': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.error(f"Channel message handling error: {e}")
    
    async def channel_update(self, event):
        """Handle channel update broadcast"""
        await self.send(text_data=json.dumps({
            'type': 'channel.update',
            'channel': event['channel']
        }))
    
    async def new_conversation(self, event):
        """Handle new conversation broadcast"""
        await self.send(text_data=json.dumps({
            'type': 'conversation.new',
            'conversation': event['conversation']
        }))
    
    async def sync_status(self, event):
        """Handle sync status broadcast"""
        await self.send(text_data=json.dumps({
            'type': 'sync.status',
            'status': event['status'],
            'progress': event.get('progress', {}),
            'message': event.get('message', '')
        }))
    
    @database_sync_to_async
    def _check_channel_access(self) -> bool:
        """Check if user has access to the channel"""
        try:
            channel = Channel.objects.get(id=self.channel_id)
            # Simplified access check - would integrate with permission system
            return True
            
        except Channel.DoesNotExist:
            return False
    
    async def _handle_channel_sync(self):
        """Handle manual channel sync request"""
        try:
            from .unipile_service import unipile_service
            
            channel = await database_sync_to_async(
                lambda: Channel.objects.get(id=self.channel_id)
            )()
            
            # Broadcast sync start
            await self.channel_layer.group_send(
                self.channel_group_name,
                {
                    'type': 'sync_status',
                    'status': 'started',
                    'message': 'Starting message sync...'
                }
            )
            
            # Perform sync
            result = await unipile_service.sync_account_messages(channel)
            
            # Broadcast sync result
            await self.channel_layer.group_send(
                self.channel_group_name,
                {
                    'type': 'sync_status',
                    'status': 'completed' if result['success'] else 'failed',
                    'progress': {
                        'processed': result.get('processed_count', 0),
                        'total': result.get('total_messages', 0)
                    },
                    'message': result.get('error', 'Sync completed successfully')
                }
            )
            
        except Exception as e:
            logger.error(f"Channel sync error: {e}")
            await self.channel_layer.group_send(
                self.channel_group_name,
                {
                    'type': 'sync_status',
                    'status': 'failed',
                    'message': str(e)
                }
            )