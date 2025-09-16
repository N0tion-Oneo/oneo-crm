"""
WebSocket routing for workflow consumers
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Real-time workflow execution updates
    re_path(
        r'ws/workflows/updates/$',
        consumers.WorkflowConsumer.as_asgi()
    ),
    
    # Collaborative workflow editing
    re_path(
        r'ws/workflows/(?P<workflow_id>[^/]+)/collaborate/$',
        consumers.WorkflowCollaborationConsumer.as_asgi()
    ),
]
