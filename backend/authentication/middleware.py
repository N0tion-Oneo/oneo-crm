"""
Async session-based authentication middleware for Oneo CRM
Handles user authentication and session management using Django's async capabilities
"""

import logging
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.conf import settings
from asgiref.sync import sync_to_async
from .models import UserSession

logger = logging.getLogger(__name__)
User = get_user_model()


class AsyncSessionAuthenticationMiddleware(MiddlewareMixin):
    """
    Async middleware for session-based authentication
    Integrates with Django's session framework and custom UserSession model
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    async def __call__(self, scope, receive, send):
        """ASGI 3 interface for async middleware"""
        if scope['type'] == 'http':
            # Process HTTP requests
            from django.core.handlers.asgi import ASGIRequest
            request = ASGIRequest(scope, '')
            
            # Process authentication
            await self.process_request_async(request)
            
            # Continue with next middleware/view
            response = await self.get_response(request)
            
            # Process response
            await self.process_response_async(request, response)
            
            return response
        else:
            # Pass through non-HTTP requests (WebSocket, etc.)
            return await self.get_response(scope, receive, send)
    
    async def process_request_async(self, request):
        """
        Async request processing for authentication
        """
        try:
            # Get session key from request
            session_key = request.session.session_key
            if not session_key:
                request.user = None
                return
            
            # Look up user session
            user_session = await self.get_user_session(session_key)
            if not user_session:
                request.user = None
                return
            
            # Check if session is expired
            if await self.is_session_expired(user_session):
                await self.cleanup_expired_session(user_session)
                request.user = None
                return
            
            # Set authenticated user
            request.user = user_session.user
            request.user_session = user_session
            
            # Update last activity
            await self.update_session_activity(user_session, request)
            
        except Exception as e:
            logger.error(f"Authentication middleware error: {e}")
            request.user = None
    
    async def process_response_async(self, request, response):
        """
        Async response processing
        """
        try:
            # Update session info if user is authenticated
            if hasattr(request, 'user_session') and request.user_session:
                await self.update_session_info(request, response)
                
        except Exception as e:
            logger.error(f"Response processing error: {e}")
        
        return response
    
    @sync_to_async
    def get_user_session(self, session_key):
        """Get user session by session key"""
        try:
            return UserSession.objects.select_related('user').get(
                session_key=session_key
            )
        except UserSession.DoesNotExist:
            return None
    
    async def is_session_expired(self, user_session):
        """Check if session is expired"""
        return user_session.expires_at < timezone.now()
    
    @sync_to_async
    def cleanup_expired_session(self, user_session):
        """Remove expired session"""
        user_session.delete()
    
    async def update_session_activity(self, user_session, request):
        """Update session last activity and user last activity"""
        now = timezone.now()
        
        # Update user session
        user_session.last_activity = now
        await sync_to_async(user_session.save)(update_fields=['last_activity'])
        
        # Update user last activity
        if hasattr(user_session.user, 'aupdate_last_activity'):
            await user_session.user.aupdate_last_activity()
    
    async def update_session_info(self, request, response):
        """Update session information based on request/response"""
        if not hasattr(request, 'user_session'):
            return
            
        user_session = request.user_session
        
        # Update IP address if changed
        current_ip = self.get_client_ip(request)
        if user_session.ip_address != current_ip:
            user_session.ip_address = current_ip
            await sync_to_async(user_session.save)(update_fields=['ip_address'])
    
    def get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AsyncAPIAuthenticationMiddleware:
    """
    Async API authentication middleware for REST endpoints
    Provides session-based authentication for API requests
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    async def __call__(self, scope, receive, send):
        """ASGI interface for API authentication"""
        if scope['type'] == 'http' and scope['path'].startswith('/api/'):
            from django.core.handlers.asgi import ASGIRequest
            request = ASGIRequest(scope, '')
            
            # Authenticate API request
            authenticated = await self.authenticate_api_request(request)
            
            if not authenticated and self.requires_authentication(request):
                # Return 401 for unauthenticated API requests
                response = JsonResponse(
                    {'error': 'Authentication required'}, 
                    status=401
                )
                await send({
                    'type': 'http.response.start',
                    'status': response.status_code,
                    'headers': [
                        (b'content-type', b'application/json'),
                    ],
                })
                await send({
                    'type': 'http.response.body',
                    'body': response.content,
                })
                return
        
        # Continue with next middleware/view
        return await self.get_response(scope, receive, send)
    
    async def authenticate_api_request(self, request):
        """
        Authenticate API request using session
        Returns True if authenticated, False otherwise
        """
        try:
            # Check for session authentication
            session_key = request.session.session_key
            if not session_key:
                return False
            
            # Get user session
            user_session = await sync_to_async(
                UserSession.objects.select_related('user').get
            )(session_key=session_key)
            
            # Check expiration
            if user_session.expires_at < timezone.now():
                await sync_to_async(user_session.delete)()
                return False
            
            # Set user on request
            request.user = user_session.user
            request.user_session = user_session
            
            return True
            
        except UserSession.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"API authentication error: {e}")
            return False
    
    def requires_authentication(self, request):
        """
        Check if the API endpoint requires authentication
        """
        # Public endpoints that don't require authentication
        public_endpoints = [
            '/api/auth/login/',
            '/api/auth/register/',
            '/api/health/',
        ]
        
        return request.path not in public_endpoints


class AsyncTenantMiddleware:
    """
    Middleware to ensure tenant context is maintained in async views
    Works with django-tenants to provide proper schema context
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    async def __call__(self, scope, receive, send):
        """Ensure tenant context is available"""
        if scope['type'] == 'http':
            from django.core.handlers.asgi import ASGIRequest
            from django.db import connection
            
            request = ASGIRequest(scope, '')
            
            # Ensure we have a tenant context
            if not hasattr(connection, 'tenant'):
                # This should be handled by django-tenants middleware
                # but we ensure it's available for async operations
                pass
            
            # Add tenant to request for async views
            request.tenant = getattr(connection, 'tenant', None)
        
        return await self.get_response(scope, receive, send)


class AsyncPermissionMiddleware:
    """
    Middleware to set up async permission checking context
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    async def __call__(self, scope, receive, send):
        """Set up permission context for async views"""
        if scope['type'] == 'http':
            from django.core.handlers.asgi import ASGIRequest
            from .permissions import AsyncPermissionManager
            
            request = ASGIRequest(scope, '')
            
            # Add permission manager to authenticated users
            if hasattr(request, 'user') and request.user and request.user.is_authenticated:
                request.permission_manager = AsyncPermissionManager(request.user)
        
        return await self.get_response(scope, receive, send)






