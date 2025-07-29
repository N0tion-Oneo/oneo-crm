import jwt
import logging
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from django.conf import settings
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from urllib.parse import parse_qs

logger = logging.getLogger(__name__)
User = get_user_model()


class JWTWebSocketAuthMiddleware(BaseMiddleware):
    """
    JWT authentication middleware for WebSocket connections.
    Supports token in query parameters or Authorization header.
    """
    
    async def __call__(self, scope, receive, send):
        """Authenticate WebSocket connection using JWT token."""
        # Try to get token from query parameters first
        token = None
        query_string = scope.get('query_string', b'').decode()
        
        if query_string:
            query_params = parse_qs(query_string)
            token = query_params.get('token', [None])[0]
        
        # Try Authorization header if no token in query params
        if not token:
            headers = dict(scope.get('headers', []))
            auth_header = headers.get(b'authorization', b'').decode()
            
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Authenticate user
        scope['user'] = await self.get_user_from_token(token)
        
        return await super().__call__(scope, receive, send)
    
    @database_sync_to_async
    def get_user_from_token(self, token):
        """Get user from JWT token."""
        if not token:
            return AnonymousUser()
        
        try:
            # Decode JWT token
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )
            
            user_id = payload.get('user_id')
            if not user_id:
                return AnonymousUser()
            
            # Get user from database
            user = User.objects.get(id=user_id, is_active=True)
            return user
            
        except (jwt.DecodeError, jwt.ExpiredSignatureError, User.DoesNotExist) as e:
            logger.warning(f"JWT authentication failed: {e}")
            return AnonymousUser()
        except Exception as e:
            logger.error(f"Unexpected error in JWT authentication: {e}")
            return AnonymousUser()


class RateLimitMiddleware(BaseMiddleware):
    """
    Rate limiting middleware for WebSocket connections.
    Prevents abuse of real-time subscriptions.
    """
    
    def __init__(self, inner):
        super().__init__(inner)
        self.rate_limits = {}  # {user_id: {'count': int, 'reset_time': timestamp}}
        self.max_connections_per_user = 10
        self.rate_limit_window = 60  # seconds
        self.max_messages_per_minute = 60
    
    async def __call__(self, scope, receive, send):
        """Apply rate limiting to WebSocket connections."""
        user = scope.get('user')
        
        if user and user.is_authenticated:
            user_id = user.id
            
            # Check connection limit
            if not await self.check_connection_limit(user_id):
                await send({
                    'type': 'websocket.close',
                    'code': 4029  # Too Many Requests
                })
                return
            
            # Wrap receive to check message rate limit
            original_receive = receive
            
            async def rate_limited_receive():
                message = await original_receive()
                
                if message['type'] == 'websocket.receive':
                    if not await self.check_message_rate_limit(user_id):
                        await send({
                            'type': 'websocket.close',
                            'code': 4029  # Too Many Requests
                        })
                        return message
                
                return message
            
            scope['receive'] = rate_limited_receive
        
        return await super().__call__(scope, receive, send)
    
    async def check_connection_limit(self, user_id):
        """Check if user has exceeded connection limit."""
        # In production, use Redis or database to track connections
        # For now, this is a simplified in-memory implementation
        return True  # Allow all connections for now
    
    async def check_message_rate_limit(self, user_id):
        """Check if user has exceeded message rate limit."""
        import time
        current_time = time.time()
        
        if user_id not in self.rate_limits:
            self.rate_limits[user_id] = {
                'count': 1,
                'reset_time': current_time + self.rate_limit_window
            }
            return True
        
        rate_limit = self.rate_limits[user_id]
        
        # Reset counter if window has passed
        if current_time > rate_limit['reset_time']:
            rate_limit['count'] = 1
            rate_limit['reset_time'] = current_time + self.rate_limit_window
            return True
        
        # Check if under limit
        if rate_limit['count'] < self.max_messages_per_minute:
            rate_limit['count'] += 1
            return True
        
        return False


class SecurityHeadersMiddleware(BaseMiddleware):
    """
    Add security headers to WebSocket connections.
    """
    
    async def __call__(self, scope, receive, send):
        """Add security validations to WebSocket connections."""
        # Validate origin
        headers = dict(scope.get('headers', []))
        origin = headers.get(b'origin', b'').decode()
        
        allowed_origins = getattr(settings, 'ALLOWED_WEBSOCKET_ORIGINS', [])
        
        if allowed_origins and origin and origin not in allowed_origins:
            await send({
                'type': 'websocket.close',
                'code': 4003  # Forbidden
            })
            return
        
        return await super().__call__(scope, receive, send)


class WebSocketLoggingMiddleware(BaseMiddleware):
    """
    Log WebSocket connection events for monitoring.
    """
    
    async def __call__(self, scope, receive, send):
        """Log WebSocket connection events."""
        user = scope.get('user', AnonymousUser())
        path = scope.get('path', 'unknown')
        
        logger.info(f"WebSocket connection opened: {path} (user: {user})")
        
        async def logging_send(message):
            if message['type'] == 'websocket.close':
                code = message.get('code', 'unknown')
                logger.info(f"WebSocket connection closed: {path} (user: {user}, code: {code})")
            await send(message)
        
        try:
            await super().__call__(scope, receive, logging_send)
        except Exception as e:
            logger.error(f"WebSocket error: {path} (user: {user}, error: {e})")
            raise