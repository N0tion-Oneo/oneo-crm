"""
ASGI config for Oneo CRM project with WebSocket support.

This module contains the ASGI application used by Django's development server
and any production ASGI deployments. It includes WebSocket routing for real-time features.
"""

import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

# Initialize Django before importing our modules
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

# Get the traditional Django ASGI application first
django_asgi_app = get_asgi_application()

# Import WebSocket modules after Django is ready
try:
    from api.routing import websocket_urlpatterns as api_websocket_patterns
    from realtime.routing import websocket_urlpatterns as realtime_websocket_patterns
    from communications.routing import websocket_urlpatterns as communications_websocket_patterns
    from api.middleware import (
        WebSocketTenantMiddleware,
        JWTWebSocketAuthMiddleware,
        RateLimitMiddleware, 
        SecurityHeadersMiddleware,
        WebSocketLoggingMiddleware
    )
    
    # Combine WebSocket URL patterns
    websocket_urlpatterns = (
        api_websocket_patterns + 
        realtime_websocket_patterns + 
        communications_websocket_patterns
    )
    websocket_enabled = True
except ImportError as e:
    print(f"Warning: WebSocket modules not available: {e}")
    websocket_enabled = False

# Create final application
if websocket_enabled:
    # Create WebSocket application with middleware stack
    # Note: WebSocketTenantMiddleware must be first to set schema context
    websocket_application = AllowedHostsOriginValidator(
        WebSocketLoggingMiddleware(
            SecurityHeadersMiddleware(
                RateLimitMiddleware(
                    WebSocketTenantMiddleware(
                        JWTWebSocketAuthMiddleware(
                            URLRouter(websocket_urlpatterns)
                        )
                    )
                )
            )
        )
    )

    # Combine HTTP and WebSocket applications
    application = ProtocolTypeRouter({
        # HTTP requests
        'http': django_asgi_app,
        
        # WebSocket connections
        'websocket': websocket_application,
    })
else:
    # Fall back to HTTP-only if WebSocket modules fail
    application = django_asgi_app
