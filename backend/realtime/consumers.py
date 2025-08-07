"""
Real-time WebSocket consumers for collaborative editing and live updates
"""
import json
import asyncio
from typing import Dict, Any, Optional
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import DenyConnection
from django.contrib.auth import get_user_model
from django.core.cache import cache
from .connection_manager import connection_manager
from .auth import authenticate_websocket_session, authenticate_websocket_jwt, extract_session_from_scope, extract_auth_from_scope, check_user_permissions, check_channel_subscription_permission, get_user_accessible_channels
import logging
import time

User = get_user_model()
logger = logging.getLogger(__name__)

class BaseRealtimeConsumer(AsyncWebsocketConsumer):
    """Base WebSocket consumer with authentication and connection management"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.user_id = None
        self.authenticated = False
        self.subscriptions = set()
        self.rate_limit_window = 60  # 1 minute
        self.rate_limit_max = 100   # Max messages per window
    
    async def connect(self):
        """Handle WebSocket connection"""
        logger.info("🔌 BaseRealtimeConsumer.connect() called")
        
        # Check if user is already authenticated by middleware
        middleware_user = self.scope.get('user')
        logger.info(f"Middleware user: {middleware_user}")
        logger.info(f"Middleware user authenticated: {middleware_user.is_authenticated if middleware_user else 'NO USER'}")
        
        user = None
        
        # Priority 1: Use middleware-authenticated user if available
        if middleware_user and middleware_user.is_authenticated:
            user = middleware_user
            logger.info(f"✅ Using middleware-authenticated user: {user.username}")
        else:
            # Priority 2: Try to authenticate from scope (JWT or session)
            auth_type, token = extract_auth_from_scope(self.scope)
            logger.info(f"WebSocket auth attempt: type={auth_type}, token={'YES' if token else 'NO'}")
            logger.info(f"WebSocket scope query_string: {self.scope.get('query_string', b'').decode('utf-8')}")
            
            if auth_type == 'jwt' and token:
                user = await authenticate_websocket_jwt(token)
                logger.info(f"JWT auth result: {user.username if user else 'FAILED'}")
            elif auth_type == 'session' and token:
                user = await authenticate_websocket_session(token)
                logger.info(f"Session auth result: {user.username if user else 'FAILED'}")
        
        if user and user.is_authenticated:
            await self._set_authenticated_user(user)
            await self.accept()
            
            # Get user's accessible channels for enhanced permission-based features
            accessible_channels = await get_user_accessible_channels(user)
            
            await self.send(text_data=json.dumps({
                'type': 'authenticated',
                'user_id': str(self.user_id),
                'message': 'Authentication successful',
                'auth_method': 'middleware' if middleware_user and middleware_user.is_authenticated else 'consumer',
                'accessible_channels': accessible_channels,
                'permission_info': {
                    'has_system_access': await check_user_permissions(user, 'system', None, 'full_access'),
                    'has_pipeline_access': await check_user_permissions(user, 'pipelines', None, 'read'),
                    'has_workflow_access': await check_user_permissions(user, 'workflows', None, 'read'),
                    'has_form_access': await check_user_permissions(user, 'forms', None, 'read')
                }
            }))

            # Subscribe to permission update channels
            if user:
                # Subscribe to user-specific permission updates
                await self.channel_layer.group_add(
                    f'user_{user.id}',
                    self.channel_name
                )
                
                # Subscribe to tenant-wide permission updates
                tenant_schema = getattr(self.scope.get('tenant', {}), 'schema_name', 'public')
                await self.channel_layer.group_add(
                    f'tenant_permissions_{tenant_schema}',
                    self.channel_name
                )
            
            await self.send_initial_presence()
            logger.info(f"✅ WebSocket connection authenticated for user: {user.username}")
            return
        
        # Accept connection and request authentication
        logger.warning("❌ WebSocket authentication failed, requesting manual auth")
        await self.accept()
        
        # Send authentication request
        await self.send(text_data=json.dumps({
            'type': 'auth_required',
            'message': 'Please provide authentication token',
            'supported_methods': ['jwt_cookie', 'jwt_query', 'session_cookie']
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if self.authenticated and self.user_id:
            # Clean up connection
            await connection_manager.disconnect_user(self.user_id, self.channel_name)
            
            # Leave all subscribed groups
            for subscription in self.subscriptions:
                await self.channel_layer.group_discard(subscription, self.channel_name)
            
            # Leave permission update channels
            await self.channel_layer.group_discard(f'user_{self.user_id}', self.channel_name)
            tenant_schema = getattr(self.scope.get('tenant', {}), 'schema_name', 'public')
            await self.channel_layer.group_discard(f'tenant_permissions_{tenant_schema}', self.channel_name)
        
        logger.info(f"WebSocket disconnected: {close_code}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket message"""
        try:
            message = json.loads(text_data)
            message_type = message.get('type')
            
            # Handle authentication
            if message_type == 'authenticate':
                await self.handle_authentication(message)
                return
            
            # Check authentication for all other messages
            if not self.authenticated:
                await self.send_error('Authentication required')
                return
            
            # Rate limiting
            if not await self.check_rate_limit():
                await self.send_error('Rate limit exceeded')
                return
            
            # Route message to appropriate handler
            await self.route_message(message_type, message)
            
        except json.JSONDecodeError:
            await self.send_error('Invalid JSON format')
        except Exception as e:
            logger.error(f"WebSocket message error: {e}")
            await self.send_error('Internal server error')
    
    async def handle_authentication(self, message: Dict[str, Any]):
        """Handle authentication message"""
        session_key = message.get('session_key')
        if not session_key:
            await self.send_error('Session key required')
            await self.close()
            return
        
        # Authenticate session
        user = await authenticate_websocket_session(session_key)
        if not user:
            await self.send_error('Invalid session')
            await self.close()
            return
        
        await self._set_authenticated_user(user)
        
        # Send authentication success  
        await self.send(text_data=json.dumps({
            'type': 'authenticated',
            'user_id': self.user_id,
            'message': 'Authentication successful'
        }))
        
        # Send initial presence data
        await self.send_initial_presence()
    
    async def _set_authenticated_user(self, user):
        """Set authenticated user and register connection"""
        self.user = user
        self.user_id = user.id
        self.authenticated = True
        
        # Register connection
        connection_info = {
            'connected_at': time.time(),
            'user_agent': self.get_header('user-agent'),
            'ip_address': self.get_client_ip(),
        }
        
        await connection_manager.connect_user(
            self.user_id, 
            self.channel_name, 
            connection_info
        )
    
    async def route_message(self, message_type: str, message: Dict[str, Any]):
        """Route message to appropriate handler"""
        handlers = {
            'subscribe': self.handle_subscribe,
            'unsubscribe': self.handle_unsubscribe,
            'document_join': self.handle_document_join,
            'document_leave': self.handle_document_leave,
            'cursor_update': self.handle_cursor_update,
            'field_lock': self.handle_field_lock,
            'field_unlock': self.handle_field_unlock,
            'ping': self.handle_ping,
        }
        
        handler = handlers.get(message_type)
        if handler:
            # Extract parameters from the message structure
            # The frontend sends: { type: 'subscribe', channel: 'pipelines_overview', payload: {...}, ... }
            # We need to pass the message with the right parameter names
            await handler(message)
        else:
            await self.send_error(f'Unknown message type: {message_type}')
    
    async def handle_subscribe(self, message: Dict[str, Any]):
        """Subscribe to a channel"""
        channel = message.get('channel')
        if not channel:
            await self.send_error('Channel required')
            return
        
        # Validate subscription permissions
        can_subscribe = await self.can_subscribe_to_channel(channel)
        logger.info(f"👤 User {self.user.username} requesting subscription to '{channel}': {'ALLOWED' if can_subscribe else 'DENIED'}")
        
        if not can_subscribe:
            await self.send_error('Permission denied')
            return
        
        # Handle special channel subscriptions
        if channel == 'pipelines_overview':
            # Subscribe to multiple channels for comprehensive pipeline updates
            channels_to_subscribe = [
                'pipeline_updates',  # General pipeline updates
                'pipelines_overview'  # Custom overview channel
            ]
            
            # Also subscribe to all accessible pipeline records 
            # (in production, you might want to limit this or make it opt-in)
            try:
                from pipelines.models import Pipeline
                from asgiref.sync import sync_to_async
                
                # Get pipelines user can access
                user_pipelines = await sync_to_async(list)(Pipeline.objects.filter(
                    # Add filtering based on user permissions here
                    # For now, allow access to all pipelines
                ).values_list('id', flat=True))
                
                # Subscribe to individual pipeline record channels
                for pipeline_id in user_pipelines:
                    channels_to_subscribe.append(f'pipeline_records_{pipeline_id}')
                    
            except Exception as e:
                logger.warning(f"Could not subscribe to individual pipeline channels: {e}")
            
            # Subscribe to all relevant channels
            for sub_channel in channels_to_subscribe:
                await self.channel_layer.group_add(sub_channel, self.channel_name)
                await connection_manager.subscribe_to_channel(self.user_id, self.channel_name, sub_channel)
                self.subscriptions.add(sub_channel)
            
            logger.info(f"Subscribed to pipelines overview: {channels_to_subscribe}")
        else:
            # Standard single channel subscription
            await self.channel_layer.group_add(channel, self.channel_name)
            await connection_manager.subscribe_to_channel(self.user_id, self.channel_name, channel)
            self.subscriptions.add(channel)
        
        await self.send(text_data=json.dumps({
            'type': 'subscribed',
            'channel': channel
        }))
    
    async def handle_unsubscribe(self, message: Dict[str, Any]):
        """Unsubscribe from a channel"""
        channel = message.get('channel')
        if not channel:
            await self.send_error('Channel required')
            return
        
        # Remove from group
        await self.channel_layer.group_discard(channel, self.channel_name)
        self.subscriptions.discard(channel)
        
        await self.send(text_data=json.dumps({
            'type': 'unsubscribed',
            'channel': channel
        }))
    
    async def handle_document_join(self, message: Dict[str, Any]):
        """Join a document for collaborative editing"""
        document_id = message.get('document_id')
        document_type = message.get('document_type', 'record')
        
        if not document_id:
            await self.send_error('Document ID required')
            return
        
        # Validate document access
        if not await self.can_access_document(document_id, document_type):
            await self.send_error('Document access denied')
            return
        
        # Join document group
        group_name = f"document_{document_id}"
        await self.channel_layer.group_add(group_name, self.channel_name)
        
        # Update presence
        cursor_info = message.get('cursor_info', {})
        cursor_info['timestamp'] = time.time()
        
        await connection_manager.update_document_presence(
            self.user_id, 
            self.channel_name, 
            document_id, 
            cursor_info
        )
        
        # Send current document presence to new user
        presence = await connection_manager.get_document_presence(document_id)
        await self.send(text_data=json.dumps({
            'type': 'document_joined',
            'document_id': document_id,
            'presence': presence
        }))
        
        # Notify others of new user
        await connection_manager.broadcast_to_document(
            document_id,
            {
                'type': 'user_joined_document',
                'user_id': self.user_id,
                'user_info': {
                    'id': self.user.id,
                    'username': self.user.username,
                    'first_name': self.user.first_name,
                    'last_name': self.user.last_name,
                }
            },
            exclude_user=self.user_id
        )
    
    async def handle_document_leave(self, message: Dict[str, Any]):
        """Leave a document"""
        document_id = message.get('document_id')
        if not document_id:
            await self.send_error('Document ID required')
            return
        
        # Leave document group
        group_name = f"document_{document_id}"
        await self.channel_layer.group_discard(group_name, self.channel_name)
        
        # Remove presence
        await connection_manager._remove_document_presence(self.user_id, document_id)
        
        await self.send(text_data=json.dumps({
            'type': 'document_left',
            'document_id': document_id
        }))
    
    async def handle_cursor_update(self, message: Dict[str, Any]):
        """Handle cursor position update"""
        document_id = message.get('document_id')
        cursor_info = message.get('cursor_info', {})
        
        if not document_id:
            await self.send_error('Document ID required')
            return
        
        # Update cursor position
        cursor_info['timestamp'] = time.time()
        cursor_info['user_id'] = self.user_id
        
        await connection_manager.update_document_presence(
            self.user_id,
            self.channel_name,
            document_id,
            cursor_info
        )
    
    async def handle_field_lock(self, message: Dict[str, Any]):
        """Handle field locking request"""
        document_id = message.get('document_id')
        field_name = message.get('field_name')
        
        if not all([document_id, field_name]):
            await self.send_error('Document ID and field name required')
            return
        
        # Attempt to acquire field lock
        lock_key = f"field_lock:{document_id}:{field_name}"
        lock_acquired = cache.add(lock_key, {
            'user_id': self.user_id,
            'timestamp': time.time(),
            'channel_name': self.channel_name
        }, 300)  # 5 minute lock timeout
        
        if lock_acquired:
            # Broadcast field locked to other users
            await connection_manager.broadcast_to_document(
                document_id,
                {
                    'type': 'field_locked',
                    'field_name': field_name,
                    'locked_by': self.user_id,
                    'user_info': {
                        'username': self.user.username,
                        'first_name': self.user.first_name,
                        'last_name': self.user.last_name,
                    }
                },
                exclude_user=self.user_id
            )
            
            await self.send(text_data=json.dumps({
                'type': 'field_lock_acquired',
                'field_name': field_name
            }))
        else:
            # Lock already held by another user
            lock_info = cache.get(lock_key)
            await self.send(text_data=json.dumps({
                'type': 'field_lock_denied',
                'field_name': field_name,
                'locked_by': lock_info.get('user_id') if lock_info else None
            }))
    
    async def handle_field_unlock(self, message: Dict[str, Any]):
        """Handle field unlock request"""
        document_id = message.get('document_id')
        field_name = message.get('field_name')
        
        if not all([document_id, field_name]):
            await self.send_error('Document ID and field name required')
            return
        
        # Release field lock
        lock_key = f"field_lock:{document_id}:{field_name}"
        lock_info = cache.get(lock_key)
        
        if lock_info and lock_info.get('user_id') == self.user_id:
            cache.delete(lock_key)
            
            # Broadcast field unlocked
            await connection_manager.broadcast_to_document(
                document_id,
                {
                    'type': 'field_unlocked',
                    'field_name': field_name,
                    'unlocked_by': self.user_id
                },
                exclude_user=self.user_id
            )
            
            await self.send(text_data=json.dumps({
                'type': 'field_unlocked',
                'field_name': field_name
            }))
        else:
            await self.send_error('Field not locked by you')
    
    async def handle_ping(self, message: Dict[str, Any]):
        """Handle ping message"""
        await self.send(text_data=json.dumps({
            'type': 'pong',
            'timestamp': time.time()
        }))
    
    async def send_error(self, message: str):
        """Send error message"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))
    
    async def send_initial_presence(self):
        """Send initial presence data to newly connected user"""
        # Get online users
        online_users = await connection_manager.get_online_users()
        
        await self.send(text_data=json.dumps({
            'type': 'initial_presence',
            'online_users': online_users
        }))
    
    async def can_subscribe_to_channel(self, channel: str) -> bool:
        """Enhanced channel subscription permission checking"""
        return await check_channel_subscription_permission(self.user, channel)
    
    async def can_access_document(self, document_id: str, document_type: str) -> bool:
        """Check if user can access document"""
        return await check_user_permissions(self.user, document_type, document_id, 'read')
    
    async def check_rate_limit(self) -> bool:
        """Check if user is within rate limits"""
        key = f"rate_limit:{self.user_id}"
        current_count = cache.get(key, 0)
        
        if current_count >= self.rate_limit_max:
            return False
        
        cache.set(key, current_count + 1, self.rate_limit_window)
        return True
    
    def get_client_ip(self) -> str:
        """Get client IP address"""
        headers = dict(self.scope.get('headers', []))
        x_forwarded_for = headers.get(b'x-forwarded-for')
        
        if x_forwarded_for:
            return x_forwarded_for.decode('utf-8').split(',')[0].strip()
        
        return self.scope.get('client', ['unknown'])[0]
    
    def get_header(self, header_name: str) -> str:
        """Get header value"""
        headers = dict(self.scope.get('headers', []))
        header_bytes = headers.get(header_name.lower().encode(), b'')
        return header_bytes.decode('utf-8')
    
    # Message handlers for different event types
    async def document_message(self, event):
        """Handle document-specific messages"""
        message = event['message']
        
        # Check if message should be excluded for this user
        if message.get('exclude_user') == self.user_id:
            return
        
        await self.send(text_data=json.dumps(message))
    
    async def record_update(self, event):
        """Handle record update messages from signals"""
        data = event.get('data', {})
        
        # Transform signal message format to frontend expected format
        message = {
            'type': self._normalize_record_type(data.get('type', 'record_update')),
            'payload': {
                'record_id': data.get('record_id'),
                'pipeline_id': data.get('pipeline_id'),
                'title': data.get('title'),
                'data': data.get('data'),
                'updated_at': data.get('updated_at'),
                'updated_by': data.get('updated_by'),
                'new_count': data.get('new_count')  # Include the updated record count
            },
            'user': {
                'id': data.get('updated_by', {}).get('id'),
                'name': data.get('updated_by', {}).get('username'),
                'email': None
            } if data.get('updated_by') else None,
            'timestamp': data.get('timestamp')
        }
        
        await self.send(text_data=json.dumps(message))
    
    async def record_deleted(self, event):
        """Handle record deletion messages from signals"""
        data = event.get('data', {})
        
        # Transform signal message format to frontend expected format  
        message = {
            'type': 'record_delete',  # Frontend expects 'record_delete'
            'payload': {
                'record_id': data.get('record_id'),
                'pipeline_id': data.get('pipeline_id'),
                'title': data.get('title'),
                'new_count': data.get('new_count')  # Include the updated record count
            },
            'timestamp': data.get('timestamp')
        }
        
        await self.send(text_data=json.dumps(message))
    
    async def pipeline_update(self, event):
        """Handle pipeline update messages from signals"""
        data = event.get('data', {})
        
        # Transform signal message format to frontend expected format
        message = {
            'type': 'pipeline_update',
            'payload': {
                'pipeline_id': data.get('pipeline_id'),
                'name': data.get('name'),
                'description': data.get('description'),
                'pipeline_type': data.get('pipeline_type'),
                'is_active': data.get('is_active')
            },
            'timestamp': data.get('timestamp')
        }
        
        await self.send(text_data=json.dumps(message))
    
    def _normalize_record_type(self, signal_type):
        """Convert signal types to frontend expected types"""
        type_mapping = {
            'record_created': 'record_create',
            'record_updated': 'record_update', 
            'record_deleted': 'record_delete'
        }
        return type_mapping.get(signal_type, signal_type)
    
    async def cursor_update(self, event):
        """Handle cursor update messages"""
        if event['user_id'] != self.user_id:  # Don't send back to sender
            await self.send(text_data=json.dumps({
                'type': 'cursor_update',
                'user_id': event['user_id'],
                'cursor_info': event['cursor_info']
            }))
    
    async def presence_change(self, event):
        """Handle presence change messages"""
        await self.send(text_data=json.dumps({
            'type': 'presence_change',
            'user_id': event['user_id'],
            'status': event['status']
        }))
    
    async def user_left_document(self, event):
        """Handle user left document event"""
        await self.send(text_data=json.dumps({
            'type': 'user_left_document',
            'user_id': event['user_id']
        }))
    
    async def document_updated(self, event):
        """Handle document updated event"""
        data = event.get('data', {})
        
        # Send document update to the client
        await self.send(text_data=json.dumps({
            'type': 'document_updated',
            'data': data,
            'timestamp': data.get('timestamp')
        }))
    
    async def activity_update(self, event):
        """Handle activity update event from AuditLog system"""
        data = event.get('data', {})
        
        # Send activity update to the client (for Activity tab in Record Drawer)
        await self.send(text_data=json.dumps({
            'type': 'activity_update',
            'data': data,
            'timestamp': data.get('created_at')
        }))
        
        logger.debug(f"Activity update sent to user {self.user_id}: {data.get('type', 'unknown')}")
    
    async def send_permission_update(self, event):
        """Handle permission change signals and broadcast to connected clients"""
        message = event.get('message', {})
        
        # Send permission update to the client
        await self.send(text_data=json.dumps({
            'type': 'permission_update',
            'data': message.get('data', {}),
            'timestamp': message.get('data', {}).get('timestamp')
        }))
        
        # Log the permission update for debugging
        logger.info(f"Permission update sent to user {self.user_id}: {message.get('data', {}).get('event_type', 'unknown')}")


class CollaborativeEditingConsumer(BaseRealtimeConsumer):
    """WebSocket consumer specifically for collaborative editing"""
    
    async def route_message(self, message_type: str, message: Dict[str, Any]):
        """Extended routing for collaborative editing"""
        # Add collaborative editing specific handlers
        collaborative_handlers = {
            'operation': self.handle_operation,
            'field_change': self.handle_field_change,
        }
        
        handler = collaborative_handlers.get(message_type)
        if handler:
            await handler(message)
        else:
            # Fall back to base handlers
            await super().route_message(message_type, message)
    
    async def handle_operation(self, message: Dict[str, Any]):
        """Handle operational transform operations"""
        document_id = message.get('document_id')
        operation = message.get('operation')
        field_name = message.get('field_name')
        
        if not all([document_id, operation, field_name]):
            await self.send_error('Document ID, operation, and field name required')
            return
        
        # Apply operational transform
        from .operational_transform import OperationalTransform
        ot = OperationalTransform(document_id, field_name)
        
        # Transform operation against concurrent operations
        transformed_op = await ot.transform_operation(operation, self.user_id)
        
        # Broadcast transformed operation to other users
        await connection_manager.broadcast_to_document(
            document_id,
            {
                'type': 'operation_applied',
                'field_name': field_name,
                'operation': transformed_op,
                'user_id': self.user_id,
                'timestamp': time.time()
            },
            exclude_user=self.user_id
        )
        
        # Acknowledge operation to sender
        await self.send(text_data=json.dumps({
            'type': 'operation_acknowledged',
            'operation_id': operation.get('id'),
            'transformed_operation': transformed_op
        }))
    
    async def handle_field_change(self, message: Dict[str, Any]):
        """Handle simple field change (non-operational transform)"""
        document_id = message.get('document_id')
        field_name = message.get('field_name')
        field_value = message.get('field_value')
        
        if not all([document_id, field_name]):
            await self.send_error('Document ID and field name required')
            return
        
        # Broadcast field change to other users
        await connection_manager.broadcast_to_document(
            document_id,
            {
                'type': 'field_changed',
                'field_name': field_name,
                'field_value': field_value,
                'user_id': self.user_id,
                'timestamp': time.time()
            },
            exclude_user=self.user_id
        )


class WorkflowExecutionConsumer(BaseRealtimeConsumer):
    """WebSocket consumer for real-time workflow execution updates"""
    
    async def route_message(self, message_type: str, message: Dict[str, Any]):
        """Extended routing for workflow execution tracking"""
        # Add workflow execution specific handlers
        workflow_handlers = {
            'subscribe_workflow': self.handle_subscribe_workflow,
            'unsubscribe_workflow': self.handle_unsubscribe_workflow,
            'subscribe_execution': self.handle_subscribe_execution,
            'unsubscribe_execution': self.handle_unsubscribe_execution,
        }
        
        handler = workflow_handlers.get(message_type)
        if handler:
            await handler(message)
        else:
            # Fall back to base handlers
            await super().route_message(message_type, message)
    
    async def handle_subscribe_workflow(self, message: Dict[str, Any]):
        """Subscribe to workflow execution updates"""
        workflow_id = message.get('workflow_id')
        if not workflow_id:
            await self.send_error('Workflow ID required')
            return
        
        # Check workflow access permissions
        if not await self.can_access_workflow(workflow_id):
            await self.send_error('Permission denied to access workflow')
            return
        
        # Subscribe to workflow channel
        channel = f"workflow:{workflow_id}"
        await self.channel_layer.group_add(channel, self.channel_name)
        self.subscriptions.add(channel)
        
        await self.send(text_data=json.dumps({
            'type': 'workflow_subscribed',
            'workflow_id': workflow_id
        }))
        
        # Send current workflow status
        await self.send_workflow_status(workflow_id)
    
    async def handle_unsubscribe_workflow(self, message: Dict[str, Any]):
        """Unsubscribe from workflow execution updates"""
        workflow_id = message.get('workflow_id')
        if not workflow_id:
            await self.send_error('Workflow ID required')
            return
        
        channel = f"workflow:{workflow_id}"
        await self.channel_layer.group_discard(channel, self.channel_name)
        self.subscriptions.discard(channel)
        
        await self.send(text_data=json.dumps({
            'type': 'workflow_unsubscribed',
            'workflow_id': workflow_id
        }))
    
    async def handle_subscribe_execution(self, message: Dict[str, Any]):
        """Subscribe to specific execution updates"""
        execution_id = message.get('execution_id')
        if not execution_id:
            await self.send_error('Execution ID required')
            return
        
        # Check execution access permissions
        if not await self.can_access_execution(execution_id):
            await self.send_error('Permission denied to access execution')
            return
        
        # Subscribe to execution channel
        channel = f"execution:{execution_id}"
        await self.channel_layer.group_add(channel, self.channel_name)
        self.subscriptions.add(channel)
        
        await self.send(text_data=json.dumps({
            'type': 'execution_subscribed',
            'execution_id': execution_id
        }))
        
        # Send current execution status and logs
        await self.send_execution_status(execution_id)
    
    async def handle_unsubscribe_execution(self, message: Dict[str, Any]):
        """Unsubscribe from execution updates"""
        execution_id = message.get('execution_id')
        if not execution_id:
            await self.send_error('Execution ID required')
            return
        
        channel = f"execution:{execution_id}"
        await self.channel_layer.group_discard(channel, self.channel_name)
        self.subscriptions.discard(channel)
        
        await self.send(text_data=json.dumps({
            'type': 'execution_unsubscribed',
            'execution_id': execution_id
        }))
    
    async def send_workflow_status(self, workflow_id: str):
        """Send current workflow status"""
        from workflows.models import Workflow, WorkflowExecution
        
        try:
            workflow = await Workflow.objects.aget(id=workflow_id)
            recent_executions = WorkflowExecution.objects.filter(
                workflow=workflow
            ).order_by('-started_at')[:5]
            
            executions_data = []
            async for execution in recent_executions:
                executions_data.append({
                    'id': str(execution.id),
                    'status': execution.status,
                    'started_at': execution.started_at.isoformat(),
                    'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
                    'duration_seconds': execution.duration_seconds,
                })
            
            await self.send(text_data=json.dumps({
                'type': 'workflow_status',
                'workflow_id': workflow_id,
                'workflow_name': workflow.name,
                'workflow_status': workflow.status,
                'recent_executions': executions_data
            }))
            
        except Workflow.DoesNotExist:
            await self.send_error('Workflow not found')
    
    async def send_execution_status(self, execution_id: str):
        """Send current execution status and logs"""
        from workflows.models import WorkflowExecution, WorkflowExecutionLog
        
        try:
            execution = await WorkflowExecution.objects.select_related('workflow').aget(id=execution_id)
            logs = WorkflowExecutionLog.objects.filter(execution=execution).order_by('started_at')
            
            logs_data = []
            async for log in logs:
                logs_data.append({
                    'id': str(log.id),
                    'node_id': log.node_id,
                    'node_name': log.node_name,
                    'node_type': log.node_type,
                    'status': log.status,
                    'started_at': log.started_at.isoformat(),
                    'completed_at': log.completed_at.isoformat() if log.completed_at else None,
                    'duration_ms': log.duration_ms,
                    'input_data': log.input_data,
                    'output_data': log.output_data,
                    'error_details': log.error_details
                })
            
            await self.send(text_data=json.dumps({
                'type': 'execution_status',
                'execution_id': execution_id,
                'workflow_id': str(execution.workflow.id),
                'workflow_name': execution.workflow.name,
                'status': execution.status,
                'started_at': execution.started_at.isoformat(),
                'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
                'duration_seconds': execution.duration_seconds,
                'trigger_data': execution.trigger_data,
                'final_output': execution.final_output,
                'error_message': execution.error_message,
                'logs': logs_data
            }))
            
        except WorkflowExecution.DoesNotExist:
            await self.send_error('Execution not found')
    
    async def can_access_workflow(self, workflow_id: str) -> bool:
        """Check if user can access workflow"""
        from workflows.models import Workflow
        from django.db.models import Q
        
        try:
            workflow = await Workflow.objects.aget(
                Q(id=workflow_id) & (
                    Q(created_by=self.user) |
                    Q(is_public=True) |
                    Q(allowed_users=self.user)
                )
            )
            return True
        except Workflow.DoesNotExist:
            return False
    
    async def can_access_execution(self, execution_id: str) -> bool:
        """Check if user can access execution"""
        from workflows.models import WorkflowExecution
        from django.db.models import Q
        
        try:
            execution = await WorkflowExecution.objects.select_related('workflow').aget(
                Q(id=execution_id) & (
                    Q(workflow__created_by=self.user) |
                    Q(workflow__is_public=True) |
                    Q(workflow__allowed_users=self.user) |
                    Q(triggered_by=self.user)
                )
            )
            return True
        except WorkflowExecution.DoesNotExist:
            return False
    
    # Message handlers for workflow events
    async def workflow_execution_started(self, event):
        """Handle workflow execution started event"""
        await self.send(text_data=json.dumps({
            'type': 'execution_started',
            'execution_id': event['execution_id'],
            'workflow_id': event['workflow_id'],
            'workflow_name': event['workflow_name'],
            'triggered_by': event['triggered_by'],
            'started_at': event['started_at']
        }))
    
    async def workflow_execution_completed(self, event):
        """Handle workflow execution completed event"""
        await self.send(text_data=json.dumps({
            'type': 'execution_completed',
            'execution_id': event['execution_id'],
            'workflow_id': event['workflow_id'],
            'status': event['status'],
            'completed_at': event['completed_at'],
            'duration_seconds': event['duration_seconds'],
            'final_output': event.get('final_output'),
            'error_message': event.get('error_message')
        }))
    
    async def workflow_node_started(self, event):
        """Handle workflow node started event"""
        await self.send(text_data=json.dumps({
            'type': 'node_started',
            'execution_id': event['execution_id'],
            'log_id': event['log_id'],
            'node_id': event['node_id'],
            'node_name': event['node_name'],
            'node_type': event['node_type'],
            'started_at': event['started_at'],
            'input_data': event.get('input_data')
        }))
    
    async def workflow_node_completed(self, event):
        """Handle workflow node completed event"""
        await self.send(text_data=json.dumps({
            'type': 'node_completed',
            'execution_id': event['execution_id'],
            'log_id': event['log_id'],
            'node_id': event['node_id'],
            'node_name': event['node_name'],
            'status': event['status'],
            'completed_at': event['completed_at'],
            'duration_ms': event['duration_ms'],
            'output_data': event.get('output_data'),
            'error_details': event.get('error_details')
        }))
    
    async def workflow_approval_requested(self, event):
        """Handle workflow approval requested event"""
        await self.send(text_data=json.dumps({
            'type': 'approval_requested',
            'execution_id': event['execution_id'],
            'approval_id': event['approval_id'],
            'title': event['title'],
            'description': event['description'],
            'assigned_to': event['assigned_to'],
            'requested_at': event['requested_at']
        }))
    
    async def workflow_approval_responded(self, event):
        """Handle workflow approval response event"""
        await self.send(text_data=json.dumps({
            'type': 'approval_responded',
            'execution_id': event['execution_id'],
            'approval_id': event['approval_id'],
            'approved': event['approved'],
            'approved_by': event['approved_by'],
            'approved_at': event['approved_at'],
            'notes': event.get('notes')
        }))


# Workflow execution broadcasting utilities
class WorkflowExecutionBroadcaster:
    """Utility class for broadcasting workflow execution events"""
    
    def __init__(self, channel_layer):
        self.channel_layer = channel_layer
    
    async def broadcast_execution_started(self, execution):
        """Broadcast execution started event"""
        await self.channel_layer.group_send(
            f"workflow:{execution.workflow.id}",
            {
                'type': 'workflow_execution_started',
                'execution_id': str(execution.id),
                'workflow_id': str(execution.workflow.id),
                'workflow_name': execution.workflow.name,
                'triggered_by': execution.triggered_by.username if execution.triggered_by else 'System',
                'started_at': execution.started_at.isoformat()
            }
        )
        
        # Also send to execution-specific channel
        await self.channel_layer.group_send(
            f"execution:{execution.id}",
            {
                'type': 'workflow_execution_started',
                'execution_id': str(execution.id),
                'workflow_id': str(execution.workflow.id),
                'workflow_name': execution.workflow.name,
                'triggered_by': execution.triggered_by.username if execution.triggered_by else 'System',
                'started_at': execution.started_at.isoformat()
            }
        )
    
    async def broadcast_execution_completed(self, execution):
        """Broadcast execution completed event"""
        message = {
            'type': 'workflow_execution_completed',
            'execution_id': str(execution.id),
            'workflow_id': str(execution.workflow.id),
            'status': execution.status,
            'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
            'duration_seconds': execution.duration_seconds,
            'final_output': execution.final_output,
            'error_message': execution.error_message
        }
        
        await self.channel_layer.group_send(f"workflow:{execution.workflow.id}", message)
        await self.channel_layer.group_send(f"execution:{execution.id}", message)
    
    async def broadcast_node_started(self, log):
        """Broadcast node started event"""
        message = {
            'type': 'workflow_node_started',
            'execution_id': str(log.execution.id),
            'log_id': str(log.id),
            'node_id': log.node_id,
            'node_name': log.node_name,
            'node_type': log.node_type,
            'started_at': log.started_at.isoformat(),
            'input_data': log.input_data
        }
        
        await self.channel_layer.group_send(f"execution:{log.execution.id}", message)
    
    async def broadcast_node_completed(self, log):
        """Broadcast node completed event"""
        message = {
            'type': 'workflow_node_completed',
            'execution_id': str(log.execution.id),
            'log_id': str(log.id),
            'node_id': log.node_id,
            'node_name': log.node_name,
            'status': log.status,
            'completed_at': log.completed_at.isoformat() if log.completed_at else None,
            'duration_ms': log.duration_ms,
            'output_data': log.output_data,
            'error_details': log.error_details
        }
        
        await self.channel_layer.group_send(f"execution:{log.execution.id}", message)
    
    async def broadcast_approval_requested(self, approval):
        """Broadcast approval requested event"""
        message = {
            'type': 'workflow_approval_requested',
            'execution_id': str(approval.execution.id),
            'approval_id': str(approval.id),
            'title': approval.title,
            'description': approval.description,
            'assigned_to': approval.assigned_to.username if approval.assigned_to else None,
            'requested_at': approval.requested_at.isoformat()
        }
        
        await self.channel_layer.group_send(f"execution:{approval.execution.id}", message)
    
    async def broadcast_approval_responded(self, approval):
        """Broadcast approval response event"""
        message = {
            'type': 'workflow_approval_responded',
            'execution_id': str(approval.execution.id),
            'approval_id': str(approval.id),
            'approved': approval.approved,
            'approved_by': approval.approved_by.username if approval.approved_by else None,
            'approved_at': approval.approved_at.isoformat() if approval.approved_at else None,
            'notes': approval.approval_notes
        }
        
        await self.channel_layer.group_send(f"execution:{approval.execution.id}", message)