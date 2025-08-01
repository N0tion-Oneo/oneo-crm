"""
WebSocket URL routing for Phase 8 Communication System
"""
from django.urls import path, re_path
from . import consumers

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
]