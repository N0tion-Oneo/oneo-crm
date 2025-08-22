"""
WebSocket URL routing for Communications System
Includes real-time sync progress consumers
"""
from django.urls import path, re_path
from . import consumers
from .consumers_sync import SyncProgressConsumer, SyncOverviewConsumer

websocket_urlpatterns = [
    # Real-time conversation updates
    re_path(
        r'ws/conversations/(?P<conversation_id>[0-9a-f-]+)/$',
        consumers.ConversationConsumer.as_asgi()
    ),
    
    # Channel-wide updates and sync notifications
    re_path(
        r'ws/channels/(?P<channel_id>[0-9a-f-]+)/$',
        consumers.ChannelConsumer.as_asgi()
    ),
    
    # Background sync progress tracking
    re_path(
        r'ws/sync-progress/(?P<sync_job_id>[0-9a-f-]+)/$',
        SyncProgressConsumer.as_asgi()
    ),
    
    # Sync overview dashboard
    path(
        'ws/sync-overview/',
        SyncOverviewConsumer.as_asgi()
    ),
]