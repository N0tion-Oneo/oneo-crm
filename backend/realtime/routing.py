"""
WebSocket routing for real-time features
"""
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    # Base real-time WebSocket
    path('ws/realtime/', consumers.BaseRealtimeConsumer.as_asgi()),
    
    # Collaborative editing WebSocket
    path('ws/collaborate/', consumers.CollaborativeEditingConsumer.as_asgi()),
    
    # Document-specific collaborative editing
    path('ws/collaborate/<str:document_id>/', consumers.CollaborativeEditingConsumer.as_asgi()),
    
    # Workflow execution WebSocket
    path('ws/workflows/', consumers.WorkflowExecutionConsumer.as_asgi()),
    
    # Specific workflow execution WebSocket
    path('ws/workflows/<uuid:workflow_id>/', consumers.WorkflowExecutionConsumer.as_asgi()),
    
    # Specific execution tracking WebSocket
    path('ws/executions/<uuid:execution_id>/', consumers.WorkflowExecutionConsumer.as_asgi()),
]