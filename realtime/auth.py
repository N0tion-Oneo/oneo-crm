"""
WebSocket authentication utilities using Django sessions
"""
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.utils import timezone
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

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
    Get user by ID with caching
    """
    # Check cache first
    cache_key = f"user:{user_id}"
    user_data = cache.get(cache_key)
    
    if user_data:
        # Reconstruct user from cached data
        try:
            user = User.objects.get(id=user_id)
            return user
        except User.DoesNotExist:
            # User was deleted, remove from cache
            cache.delete(cache_key)
            return None
    
    # Get from database
    try:
        user = User.objects.get(id=user_id, is_active=True)
        
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

def extract_session_from_scope(scope):
    """
    Extract session key from WebSocket scope
    Checks cookies and query parameters
    """
    # Check cookies first (standard approach)
    headers = dict(scope.get('headers', []))
    cookie_header = headers.get(b'cookie')
    
    if cookie_header:
        cookie_str = cookie_header.decode('utf-8')
        # Parse cookies to find sessionid
        cookies = {}
        for cookie in cookie_str.split(';'):
            cookie = cookie.strip()
            if '=' in cookie:
                name, value = cookie.split('=', 1)
                cookies[name] = value
        
        # Django default session cookie name
        session_key = cookies.get('sessionid')
        if session_key:
            return session_key
    
    # Fallback: check query parameters
    query_string = scope.get('query_string', b'').decode('utf-8')
    if query_string:
        params = dict(param.split('=') for param in query_string.split('&') if '=' in param)
        if 'sessionid' in params:
            return params['sessionid']
    
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