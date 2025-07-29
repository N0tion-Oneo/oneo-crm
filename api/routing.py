from django.urls import re_path, path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from .consumers import SSEConsumer, GraphQLSubscriptionConsumer
from .middleware import JWTWebSocketAuthMiddleware


websocket_urlpatterns = [
    # SSE-style WebSocket endpoint for real-time updates
    re_path(r'ws/sse/$', SSEConsumer.as_asgi()),
    
    # GraphQL subscriptions endpoint
    re_path(r'ws/graphql/$', GraphQLSubscriptionConsumer.as_asgi()),
    
    # Pipeline-specific real-time updates
    re_path(r'ws/pipelines/(?P<pipeline_id>\w+)/$', SSEConsumer.as_asgi()),
    
    # Record-specific real-time updates
    re_path(r'ws/records/(?P<record_id>\w+)/$', SSEConsumer.as_asgi()),
]

# WebSocket application with JWT authentication and security
websocket_application = ProtocolTypeRouter({
    'websocket': AllowedHostsOriginValidator(
        JWTWebSocketAuthMiddleware(
            URLRouter(websocket_urlpatterns)
        )
    ),
})


# HTTP routing for SSE endpoints (fallback)
sse_urlpatterns = [
    path('sse/records/', SSEConsumer.as_asgi()),
    path('sse/pipelines/', SSEConsumer.as_asgi()),
    path('sse/activity/', SSEConsumer.as_asgi()),
]