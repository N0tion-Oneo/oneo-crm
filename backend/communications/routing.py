"""
WebSocket URL routing for Communications System
Note: Sync progress is now handled via realtime app consumers
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
    
    # Note: Sync progress broadcasting is now handled via channel groups
    # in the realtime app. Frontend subscribes to channels like:
    # - sync_progress_{celery_task_id}
    # - sync_jobs_{user_id}
    # - sync_{provider}_{user_id}
]