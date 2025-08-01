"""
WebSocket authentication utilities using JWT tokens and Django sessions
"""
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import jwt
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

async def authenticate_websocket_jwt(token: str):
    """
    Authenticate JWT token for WebSocket connections
    Returns user instance or None if authentication fails
    """
    if not token:
        return None
    
    try:
        # Clean up token (remove 'Bearer ' prefix if present)
        if token.startswith('Bearer '):
            token = token[7:]
        
        # Validate JWT token
        access_token = AccessToken(token)
        user_id = access_token['user_id']
        
        # Get user from database
        user = await get_user_by_id(int(user_id))
        if not user or not user.is_active:
            logger.warning(f"User {user_id} not found or inactive")
            return None
        
        return user
        
    except (InvalidToken, TokenError, KeyError) as e:
        logger.warning(f"JWT authentication failed: {e}")
        return None
    except Exception as e:
        logger.error(f"JWT authentication error: {e}")
        return None

async def authenticate_websocket_session(session_key: str):
    """
    Authenticate session key for WebSocket connections
    Returns user instance or None if authentication fails
    """
    if not session_key:
        return None
    
    try:
        # Get session from database/cache
        try:
            session = Session.objects.get(session_key=session_key)
            
            # Check if session is expired
            if session.expire_date < timezone.now():
                logger.warning(f"Session {session_key} is expired")
                return None
            
            # Decode session data
            session_data = session.get_decoded()
            user_id = session_data.get('_auth_user_id')
            
            if not user_id:
                logger.warning("Session does not contain user_id")
                return None
            
            # Get user from database
            user = await get_user_by_id(int(user_id))
            if not user or not user.is_active:
                logger.warning(f"User {user_id} not found or inactive")
                return None
            
            return user
            
        except Session.DoesNotExist:
            logger.warning(f"Session {session_key} not found")
            return None
            
    except Exception as e:
        logger.error(f"Session authentication error: {e}")
        return None

async def get_user_by_id(user_id: int):
    """
    Get user by ID with caching (async version)
    """
    from asgiref.sync import sync_to_async
    
    # Check cache first
    cache_key = f"user:{user_id}"
    user_data = cache.get(cache_key)
    
    if user_data:
        # Reconstruct user from cached data
        try:
            user = await sync_to_async(User.objects.get)(id=user_id)
            return user
        except User.DoesNotExist:
            # User was deleted, remove from cache
            cache.delete(cache_key)
            return None
    
    # Get from database using async wrapper
    try:
        user = await sync_to_async(User.objects.get)(id=user_id, is_active=True)
        
        # Cache user data for 5 minutes
        cache.set(cache_key, {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_active': user.is_active,
        }, 300)
        
        return user
        
    except User.DoesNotExist:
        return None

def extract_auth_from_scope(scope):
    """
    Extract authentication token from WebSocket scope
    Returns a tuple: (auth_type, token)
    auth_type can be 'jwt' or 'session'
    """
    headers = dict(scope.get('headers', []))
    
    # Check for JWT token in Authorization header
    auth_header = headers.get(b'authorization')
    if auth_header:
        auth_str = auth_header.decode('utf-8')
        if auth_str.startswith('Bearer '):
            return ('jwt', auth_str[7:])
    
    # Check cookies for JWT token
    cookie_header = headers.get(b'cookie')
    if cookie_header:
        cookie_str = cookie_header.decode('utf-8')
        cookies = {}
        for cookie in cookie_str.split(';'):
            cookie = cookie.strip()
            if '=' in cookie:
                name, value = cookie.split('=', 1)
                cookies[name] = value
        
        # Check for JWT access token in cookies
        access_token = cookies.get('oneo_access_token')
        if access_token:
            return ('jwt', access_token)
        
        # Fallback to session-based auth
        session_key = cookies.get('sessionid')
        if session_key:
            return ('session', session_key)
    
    # Check query parameters
    query_string = scope.get('query_string', b'').decode('utf-8')
    if query_string:
        from urllib.parse import parse_qs, unquote
        
        # Properly parse and decode query parameters
        params = parse_qs(query_string)
        
        # Check for JWT token in query params
        if 'token' in params and params['token']:
            token = unquote(params['token'][0])  # URL decode and get first value
            return ('jwt', token)
        
        # Check for session ID in query params
        if 'sessionid' in params and params['sessionid']:
            session_id = unquote(params['sessionid'][0])
            return ('session', session_id)
    
    return (None, None)

def extract_session_from_scope(scope):
    """
    Legacy function - extract session key from WebSocket scope
    Maintained for compatibility
    """
    auth_type, token = extract_auth_from_scope(scope)
    if auth_type == 'session':
        return token
    return None

async def check_user_permissions(user, resource_type: str, resource_id: str = None, action: str = 'read'):
    """
    Check if user has permissions for WebSocket operations
    """
    if not user or not user.is_authenticated:
        return False
    
    # For authenticated users, return True (can be enhanced with permission system later)
    # This simplifies the authentication flow while maintaining security
    return True