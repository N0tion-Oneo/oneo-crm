"""
Server-Sent Events (SSE) views for real-time notifications and activity feeds
"""
import json
import asyncio
import time
from typing import AsyncGenerator, Dict, Any, Optional
from django.http import StreamingHttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.http import HttpResponseForbidden
from channels.layers import get_channel_layer
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class SSEHandler:
    """Handles Server-Sent Events streaming"""
    
    def __init__(self, user: User):
        self.user = user
        self.channel_layer = get_channel_layer()
        self.heartbeat_interval = 30  # seconds
        self.max_retry_delay = 30000  # milliseconds
        self.connection_timeout = 3600  # 1 hour
    
    async def create_event_stream(
        self, 
        channels: list, 
        initial_data: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """Create SSE event stream"""
        
        start_time = time.time()
        
        # Send initial connection event
        yield self._format_sse_message('connected', {
            'user_id': self.user.id,
            'timestamp': start_time,
            'retry': self.max_retry_delay
        })
        
        # Send initial data if provided
        if initial_data:
            yield self._format_sse_message('initial_data', initial_data)
        
        # Start heartbeat and message loop
        last_heartbeat = start_time
        message_count = 0
        
        try:
            while True:
                current_time = time.time()
                
                # Check connection timeout
                if current_time - start_time > self.connection_timeout:
                    yield self._format_sse_message('timeout', {
                        'message': 'Connection timeout',
                        'duration': self.connection_timeout
                    })
                    break
                
                # Check for new messages
                messages = await self._get_pending_messages(channels)
                
                for message in messages:
                    yield self._format_sse_message(message['type'], message['data'])
                    message_count += 1
                
                # Send heartbeat if needed
                if current_time - last_heartbeat >= self.heartbeat_interval:
                    yield self._format_sse_message('heartbeat', {
                        'timestamp': current_time,
                        'messages_sent': message_count
                    })
                    last_heartbeat = current_time
                
                # Short sleep to prevent busy waiting
                await asyncio.sleep(0.5)
                
        except asyncio.CancelledError:
            # Client disconnected
            logger.info(f"SSE stream cancelled for user {self.user.id}")
        except Exception as e:
            logger.error(f"SSE stream error for user {self.user.id}: {e}")
            yield self._format_sse_message('error', {
                'message': 'Stream error occurred',
                'retry': self.max_retry_delay
            })
    
    async def _get_pending_messages(self, channels: list) -> list:
        """Get pending messages for user from subscribed channels"""
        messages = []
        
        # Check each subscribed channel for messages
        for channel in channels:
            message_key = f"sse_messages:{self.user.id}:{channel}"
            channel_messages = cache.get(message_key, [])
            
            if channel_messages:
                messages.extend(channel_messages)
                # Clear processed messages
                cache.delete(message_key)
        
        # Sort messages by timestamp if available
        messages.sort(key=lambda msg: msg.get('timestamp', 0))
        return messages
    
    def _format_sse_message(self, event_type: str, data: Dict[str, Any]) -> str:
        """Format message as SSE format"""
        data_str = json.dumps(data, default=str)  # Handle datetime serialization
        return f"event: {event_type}\ndata: {data_str}\n\n"


@require_http_methods(["GET"])
@login_required
def notifications_stream(request):
    """SSE endpoint for user notifications"""
    
    def event_stream():
        """Generator for notification events"""
        handler = SSEHandler(request.user)
        
        # Subscribe to user-specific notification channels
        channels = [
            f"user_notifications:{request.user.id}",
            f"system_notifications"
        ]
        
        # Add tenant-specific notifications if user has tenant
        if hasattr(request.user, 'tenant'):
            channels.append(f"tenant_announcements:{request.user.tenant.id}")
        
        # Get initial notification data
        initial_data = {
            'unread_count': get_unread_notification_count(request.user),
            'recent_notifications': get_recent_notifications(request.user, limit=5)
        }
        
        # Create async event stream
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async_generator = handler.create_event_stream(channels, initial_data)
            
            while True:
                try:
                    message = loop.run_until_complete(async_generator.__anext__())
                    yield message
                except StopAsyncIteration:
                    break
        except GeneratorExit:
            loop.close()
        finally:
            loop.close()
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    
    # Set SSE headers
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    response['X-Accel-Buffering'] = 'no'  # For nginx
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Headers'] = 'Cache-Control'
    
    return response


@require_http_methods(["GET"])
@login_required  
def activity_stream(request):
    """SSE endpoint for activity feed"""
    
    def event_stream():
        handler = SSEHandler(request.user)
        
        # Get pipeline IDs user has access to
        accessible_pipelines = get_accessible_pipeline_ids(request.user)
        
        # Subscribe to activity channels
        channels = []
        for pipeline_id in accessible_pipelines:
            channels.append(f"pipeline_activity:{pipeline_id}")
        
        # Add user-specific activity
        channels.extend([
            f"user_activity:{request.user.id}",
            "global_activity"
        ])
        
        # Get initial activity data
        initial_data = {
            'recent_activity': get_recent_activity(request.user, limit=20)
        }
        
        # Create async stream
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async_generator = handler.create_event_stream(channels, initial_data)
            
            while True:
                try:
                    message = loop.run_until_complete(async_generator.__anext__())
                    yield message
                except StopAsyncIteration:
                    break
        except GeneratorExit:
            loop.close()
        finally:
            loop.close()
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    response['X-Accel-Buffering'] = 'no'
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Headers'] = 'Cache-Control'
    
    return response


@require_http_methods(["GET"])
@login_required
def dashboard_stream(request, dashboard_id):
    """SSE endpoint for live dashboard updates"""
    
    # Validate dashboard access
    if not can_access_dashboard(request.user, dashboard_id):
        return HttpResponseForbidden("Dashboard access denied")
    
    def event_stream():
        handler = SSEHandler(request.user)
        
        # Subscribe to dashboard-specific channels
        channels = [
            f"dashboard_updates:{dashboard_id}",
            f"dashboard_data:{dashboard_id}"
        ]
        
        # Add pipeline data channels for dashboard
        dashboard_pipelines = get_dashboard_pipeline_ids(dashboard_id)
        for pipeline_id in dashboard_pipelines:
            channels.append(f"pipeline_data:{pipeline_id}")
        
        # Get initial dashboard data
        initial_data = get_dashboard_data(dashboard_id, request.user)
        
        # Create async stream
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async_generator = handler.create_event_stream(channels, initial_data)
            
            while True:
                try:
                    message = loop.run_until_complete(async_generator.__anext__())
                    yield message
                except StopAsyncIteration:
                    break
        except GeneratorExit:
            loop.close()
        finally:
            loop.close()
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    response['X-Accel-Buffering'] = 'no'
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Headers'] = 'Cache-Control'
    
    return response


@require_http_methods(["GET"])
@login_required
def pipeline_stream(request, pipeline_id):
    """SSE endpoint for pipeline-specific updates"""
    
    # Check pipeline access
    if not can_access_pipeline(request.user, pipeline_id):
        return HttpResponseForbidden("Pipeline access denied")
    
    def event_stream():
        handler = SSEHandler(request.user)
        
        # Subscribe to pipeline-specific channels
        channels = [
            f"pipeline_updates:{pipeline_id}",
            f"pipeline_records:{pipeline_id}",
            f"pipeline_activity:{pipeline_id}"
        ]
        
        # Get initial pipeline data
        initial_data = {
            'pipeline_info': get_pipeline_info(pipeline_id),
            'recent_records': get_recent_pipeline_records(pipeline_id, limit=10),
            'pipeline_stats': get_pipeline_stats(pipeline_id)
        }
        
        # Create async stream
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async_generator = handler.create_event_stream(channels, initial_data)
            
            while True:
                try:
                    message = loop.run_until_complete(async_generator.__anext__())
                    yield message
                except StopAsyncIteration:
                    break
        except GeneratorExit:
            loop.close()
        finally:
            loop.close()
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    response['X-Accel-Buffering'] = 'no'
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Headers'] = 'Cache-Control'
    
    return response


# Utility functions for SSE data
def get_unread_notification_count(user: User) -> int:
    """Get count of unread notifications for user"""
    # Integration with notification system would go here
    return cache.get(f"unread_notifications:{user.id}", 0)


def get_recent_notifications(user: User, limit: int = 10) -> list:
    """Get recent notifications for user"""
    # Integration with notification system would go here
    notifications_key = f"recent_notifications:{user.id}"
    return cache.get(notifications_key, [])[:limit]


def get_accessible_pipeline_ids(user: User) -> list:
    """Get pipeline IDs that user has access to"""
    # Integration with permission system
    try:
        from authentication.permissions import AsyncPermissionManager
        from django_tenants.utils import schema_context
        from pipelines.models import Pipeline
        
        # Get pipelines user can access (simplified)
        accessible_ids = []
        
        # This would normally be done asynchronously with proper permission checking
        if hasattr(user, 'tenant'):
            with schema_context(user.tenant.schema_name):
                pipelines = Pipeline.objects.filter(is_active=True)[:100]  # Limit for performance
                accessible_ids = [str(p.id) for p in pipelines]
        
        return accessible_ids
    except Exception as e:
        logger.error(f"Error getting accessible pipelines for user {user.id}: {e}")
        return []


def get_recent_activity(user: User, limit: int = 20) -> list:
    """Get recent activity for user"""
    # Integration with activity tracking system
    activity_key = f"recent_activity:{user.id}"
    return cache.get(activity_key, [])[:limit]


def can_access_dashboard(user: User, dashboard_id: str) -> bool:
    """Check if user can access dashboard"""
    # Integration with dashboard permission system
    return True  # Simplified for now


def can_access_pipeline(user: User, pipeline_id: str) -> bool:
    """Check if user can access pipeline"""
    # Integration with pipeline permission system
    return True  # Simplified for now


def get_dashboard_data(dashboard_id: str, user: User) -> dict:
    """Get dashboard data for initial load"""
    dashboard_key = f"dashboard_data:{dashboard_id}"
    return cache.get(dashboard_key, {
        'dashboard_id': dashboard_id,
        'title': f'Dashboard {dashboard_id}',
        'widgets': [],
        'last_updated': time.time()
    })


def get_dashboard_pipeline_ids(dashboard_id: str) -> list:
    """Get pipeline IDs associated with dashboard"""
    dashboard_pipelines_key = f"dashboard_pipelines:{dashboard_id}"
    return cache.get(dashboard_pipelines_key, [])


def get_pipeline_info(pipeline_id: str) -> dict:
    """Get basic pipeline information"""
    try:
        from django_tenants.utils import schema_context
        from pipelines.models import Pipeline
        
        # This should be done in proper tenant context
        pipeline_data = cache.get(f"pipeline_info:{pipeline_id}")
        if not pipeline_data:
            pipeline_data = {
                'id': pipeline_id,
                'name': f'Pipeline {pipeline_id}',
                'record_count': 0,
                'last_updated': time.time()
            }
        
        return pipeline_data
    except Exception as e:
        logger.error(f"Error getting pipeline info {pipeline_id}: {e}")
        return {'id': pipeline_id, 'name': 'Unknown Pipeline'}


def get_recent_pipeline_records(pipeline_id: str, limit: int = 10) -> list:
    """Get recent records for pipeline"""
    records_key = f"recent_records:{pipeline_id}"
    return cache.get(records_key, [])[:limit]


def get_pipeline_stats(pipeline_id: str) -> dict:
    """Get pipeline statistics"""
    stats_key = f"pipeline_stats:{pipeline_id}"
    return cache.get(stats_key, {
        'total_records': 0,
        'records_today': 0,
        'active_users': 0,
        'last_activity': None
    })


# SSE message broadcasting utilities
async def broadcast_notification(user_id: int, notification_data: dict):
    """Broadcast notification to user via SSE"""
    message_key = f"sse_messages:{user_id}:user_notifications:{user_id}"
    messages = cache.get(message_key, [])
    
    messages.append({
        'type': 'notification',
        'data': notification_data,
        'timestamp': time.time()
    })
    
    # Keep only recent messages
    if len(messages) > 50:
        messages = messages[-50:]
    
    cache.set(message_key, messages, 300)  # 5 minute TTL


async def broadcast_activity(activity_data: dict, channels: list = None):
    """Broadcast activity to multiple channels"""
    if not channels:
        channels = ['global_activity']
    
    for channel in channels:
        # Find users subscribed to this channel
        # In a real implementation, this would be more efficient
        for user_id in get_users_subscribed_to_channel(channel):
            message_key = f"sse_messages:{user_id}:{channel}"
            messages = cache.get(message_key, [])
            
            messages.append({
                'type': 'activity',
                'data': activity_data,
                'timestamp': time.time()
            })
            
            if len(messages) > 20:
                messages = messages[-20:]
            
            cache.set(message_key, messages, 300)


def get_users_subscribed_to_channel(channel: str) -> list:
    """Get list of user IDs subscribed to a channel"""
    # This would integrate with the connection manager
    # For now, return empty list
    return []