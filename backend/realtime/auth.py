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
    Enhanced permission checking for WebSocket operations.
    Integrates with the full permission system including dynamic resources.
    """
    if not user or not user.is_authenticated:
        logger.warning("Permission check failed: User not authenticated")
        return False
    
    try:
        # Import permission manager (avoid circular imports)
        from authentication.permissions import AsyncPermissionManager
        
        # Create permission manager for the user
        permission_manager = AsyncPermissionManager(user)
        
        # Handle different resource types
        if resource_type == 'pipelines':
            # Check general pipeline permission first
            general_permission = await permission_manager.has_permission(
                'action', 'pipelines', action
            )
            
            if general_permission:
                return True
            
            # If no general permission, check specific pipeline permission
            if resource_id:
                specific_permission = await permission_manager.has_permission(
                    'action', f'pipeline_{resource_id}', action
                )
                return specific_permission
            
            return False
        
        elif resource_type == 'workflows':
            # Check general workflow permission first
            general_permission = await permission_manager.has_permission(
                'action', 'workflows', action
            )
            
            if general_permission:
                return True
            
            # If no general permission, check specific workflow permission
            if resource_id:
                specific_permission = await permission_manager.has_permission(
                    'action', f'workflow_{resource_id}', action
                )
                return specific_permission
            
            return False
        
        elif resource_type == 'forms':
            # Check general form permission first
            general_permission = await permission_manager.has_permission(
                'action', 'forms', action
            )
            
            if general_permission:
                return True
            
            # If no general permission, check specific form permission
            if resource_id:
                specific_permission = await permission_manager.has_permission(
                    'action', f'form_{resource_id}', action
                )
                return specific_permission
            
            return False
        
        elif resource_type == 'records':
            # Records require pipeline access
            # First check if user has general record permissions
            record_permission = await permission_manager.has_permission(
                'action', 'records', action
            )
            
            if record_permission:
                # Still need to check if they have access to the pipeline this record belongs to
                if resource_id:
                    # Try to get the record and check pipeline access
                    try:
                        from asgiref.sync import sync_to_async
                        from pipelines.models import Record
                        
                        # Get record to find its pipeline
                        record = await sync_to_async(Record.objects.select_related('pipeline').get)(
                            id=resource_id
                        )
                        
                        # Check pipeline access
                        pipeline_access = await check_user_permissions(
                            user, 'pipelines', str(record.pipeline.id), 'access'
                        )
                        
                        return pipeline_access
                    except:
                        # If we can't find the record, deny access
                        return False
                
                return True
            
            return False
        
        elif resource_type == 'user_presence':
            # All authenticated users can see presence (but implement privacy controls later)
            return True
        
        elif resource_type == 'notifications':
            # Users can see their own notifications
            return True
        
        elif resource_type == 'system':
            # System-level permissions
            return await permission_manager.has_permission('action', 'system', action)
        
        else:
            # For any other resource type, check general permission
            return await permission_manager.has_permission('action', resource_type, action)
    
    except Exception as e:
        logger.error(f"Permission check error for user {user.id}, resource {resource_type}:{resource_id}, action {action}: {e}")
        # Fail closed - deny access on error
        return False


async def check_channel_subscription_permission(user, channel: str):
    """
    Enhanced channel subscription permission checking.
    Maps channel patterns to appropriate permission checks.
    """
    if not user or not user.is_authenticated:
        return False
    
    try:
        # Parse different channel patterns
        if channel.startswith('pipeline:') or channel.startswith('pipeline_'):
            # Extract pipeline ID from channel name
            if ':' in channel:
                pipeline_id = channel.split(':')[1]
            else:
                # Handle pipeline_records_X format
                parts = channel.split('_')
                if len(parts) >= 3:
                    pipeline_id = parts[2]
                else:
                    return False
            
            return await check_user_permissions(user, 'pipelines', pipeline_id, 'read')
        
        elif channel.startswith('workflow:') or channel.startswith('workflow_'):
            # Extract workflow ID from channel name
            if ':' in channel:
                workflow_id = channel.split(':')[1]
            else:
                parts = channel.split('_')
                if len(parts) >= 2:
                    workflow_id = parts[1]
                else:
                    return False
            
            return await check_user_permissions(user, 'workflows', workflow_id, 'read')
        
        elif channel.startswith('document:') or channel.startswith('document_'):
            # Document-level permissions (records) - handle both formats
            if ':' in channel:
                document_id = channel.split(':')[1]
            else:
                # Handle document_21 format
                document_id = channel.split('_')[1]
            return await check_user_permissions(user, 'records', document_id, 'read')
        
        elif channel.startswith('form:') or channel.startswith('form_'):
            # Form-specific channels
            if ':' in channel:
                form_id = channel.split(':')[1]
            else:
                parts = channel.split('_')
                if len(parts) >= 2:
                    form_id = parts[1]
                else:
                    return False
            
            return await check_user_permissions(user, 'forms', form_id, 'read')
        
        elif channel in ['user_presence', 'pipelines_overview', 'pipeline_updates', 'permission_updates', 'ai_jobs', 'ai_templates', 'ai_analytics']:
            # General channels - all authenticated users can subscribe
            return True
        
        elif channel.startswith('tenant_'):
            # Tenant-specific channels - users can subscribe to their own tenant channels
            return True
        
        elif channel.startswith('user_'):
            # User-specific channels - users can only subscribe to their own channels
            user_id_from_channel = channel.split('_')[1]
            return str(user.id) == user_id_from_channel
        
        else:
            # Unknown channel pattern - deny access
            logger.warning(f"Unknown channel pattern for permission check: {channel}")
            return False
    
    except Exception as e:
        logger.error(f"Channel subscription permission error for user {user.id}, channel {channel}: {e}")
        return False


async def get_user_accessible_channels(user):
    """
    Get list of channels the user can access.
    Useful for permission-based channel filtering.
    """
    if not user or not user.is_authenticated:
        return []
    
    try:
        from authentication.permissions import AsyncPermissionManager
        
        permission_manager = AsyncPermissionManager(user)
        accessible_channels = []
        
        # Always accessible channels for authenticated users
        accessible_channels.extend([
            'user_presence',
            'pipelines_overview',
            'pipeline_updates',
            'permission_updates',
            'ai_jobs',
            'ai_templates', 
            'ai_analytics',
            f'user_{user.id}',  # User's own channel
            f'tenant_{getattr(user, "tenant_id", "default")}'  # Tenant channel
        ])
        
        # Check pipeline access
        accessible_pipelines = await permission_manager.get_accessible_pipelines()
        if accessible_pipelines == 'all':
            # User has access to all pipelines - we'd need to fetch all pipeline IDs
            # For now, return a flag that they have broad access
            accessible_channels.append('pipelines:*')
        elif isinstance(accessible_pipelines, list):
            # Add specific pipeline channels
            for pipeline_id in accessible_pipelines:
                accessible_channels.extend([
                    f'pipeline:{pipeline_id}',
                    f'pipeline_records_{pipeline_id}'
                ])
        
        # Check workflow access if user has workflow permissions
        if await permission_manager.has_permission('action', 'workflows', 'read'):
            accessible_channels.append('workflows:*')
        
        # Check form access if user has form permissions
        if await permission_manager.has_permission('action', 'forms', 'read'):
            accessible_channels.append('forms:*')
        
        return accessible_channels
    
    except Exception as e:
        logger.error(f"Error getting accessible channels for user {user.id}: {e}")
        return ['user_presence']  # Minimal fallback