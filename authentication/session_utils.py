"""
Async session management utilities for authentication
Handles session creation, validation, and cleanup using Django's async capabilities
"""

import secrets
import logging
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings
from asgiref.sync import sync_to_async
from .models import UserSession

logger = logging.getLogger(__name__)
User = get_user_model()


class AsyncSessionManager:
    """
    Manages user sessions with async support
    Integrates with Django's session framework and Redis backend
    """
    
    # Default session timeout (configurable via settings)
    DEFAULT_SESSION_TIMEOUT = timedelta(hours=24)
    
    @classmethod
    async def create_session(cls, user, request=None, **kwargs):
        """
        Create a new user session asynchronously
        
        Args:
            user: User instance
            request: Django request object (optional)
            **kwargs: Additional session data
            
        Returns:
            UserSession instance
        """
        try:
            # Generate unique session key
            session_key = cls.generate_session_key()
            
            # Calculate expiration time
            timeout = kwargs.get('timeout', cls.DEFAULT_SESSION_TIMEOUT)
            expires_at = timezone.now() + timeout
            
            # Extract client information from request
            client_info = cls.extract_client_info(request) if request else {}
            
            # Create session record
            session_data = {
                'user': user,
                'session_key': session_key,
                'expires_at': expires_at,
                'ip_address': client_info.get('ip_address'),
                'user_agent': client_info.get('user_agent', ''),
                'device_info': client_info.get('device_info', {}),
            }
            
            # Add any additional data
            session_data.update(kwargs)
            
            # Create session in database
            user_session = await sync_to_async(UserSession.objects.create)(**session_data)
            
            # Set session in Django's session framework
            if request and hasattr(request, 'session'):
                request.session.cycle_key()
                request.session['user_id'] = user.id
                request.session['session_id'] = user_session.id
                await sync_to_async(request.session.save)()
            
            logger.info(f"Created session {session_key[:8]}... for user {user.username}")
            return user_session
            
        except Exception as e:
            logger.error(f"Failed to create session for user {user.username}: {e}")
            raise
    
    @classmethod
    async def get_session(cls, session_key):
        """
        Get user session by session key
        
        Args:
            session_key: Session key string
            
        Returns:
            UserSession instance or None
        """
        try:
            return await sync_to_async(
                UserSession.objects.select_related('user').get
            )(session_key=session_key)
        except UserSession.DoesNotExist:
            return None
    
    @classmethod
    async def validate_session(cls, session_key):
        """
        Validate session and return user if valid
        
        Args:
            session_key: Session key to validate
            
        Returns:
            User instance if valid, None otherwise
        """
        try:
            user_session = await cls.get_session(session_key)
            if not user_session:
                return None
            
            # Check expiration
            if user_session.expires_at < timezone.now():
                await cls.destroy_session(session_key)
                return None
            
            # Update last activity
            await cls.update_session_activity(user_session)
            
            return user_session.user
            
        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return None
    
    @classmethod
    async def update_session_activity(cls, user_session):
        """
        Update session last activity timestamp
        
        Args:
            user_session: UserSession instance
        """
        try:
            user_session.last_activity = timezone.now()
            await sync_to_async(user_session.save)(update_fields=['last_activity'])
            
            # Also update user's last activity
            if hasattr(user_session.user, 'aupdate_last_activity'):
                await user_session.user.aupdate_last_activity()
                
        except Exception as e:
            logger.error(f"Failed to update session activity: {e}")
    
    @classmethod
    async def extend_session(cls, session_key, additional_time=None):
        """
        Extend session expiration time
        
        Args:
            session_key: Session key
            additional_time: Additional time delta (default: DEFAULT_SESSION_TIMEOUT)
        """
        try:
            user_session = await cls.get_session(session_key)
            if not user_session:
                return False
            
            additional_time = additional_time or cls.DEFAULT_SESSION_TIMEOUT
            user_session.expires_at = timezone.now() + additional_time
            await sync_to_async(user_session.save)(update_fields=['expires_at'])
            
            logger.info(f"Extended session {session_key[:8]}... until {user_session.expires_at}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to extend session: {e}")
            return False
    
    @classmethod
    async def destroy_session(cls, session_key):
        """
        Destroy user session
        
        Args:
            session_key: Session key to destroy
        """
        try:
            user_session = await cls.get_session(session_key)
            if user_session:
                await sync_to_async(user_session.delete)()
                logger.info(f"Destroyed session {session_key[:8]}...")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to destroy session: {e}")
            return False
    
    @classmethod
    async def destroy_all_user_sessions(cls, user):
        """
        Destroy all sessions for a specific user
        
        Args:
            user: User instance
        """
        try:
            session_count = await sync_to_async(
                UserSession.objects.filter(user=user).count
            )()
            
            await sync_to_async(
                UserSession.objects.filter(user=user).delete
            )()
            
            logger.info(f"Destroyed {session_count} sessions for user {user.username}")
            return session_count
            
        except Exception as e:
            logger.error(f"Failed to destroy user sessions: {e}")
            return 0
    
    @classmethod
    async def cleanup_expired_sessions(cls):
        """
        Clean up expired sessions
        
        Returns:
            Number of cleaned up sessions
        """
        try:
            expired_sessions = await sync_to_async(
                UserSession.objects.filter(expires_at__lt=timezone.now()).count
            )()
            
            await sync_to_async(
                UserSession.objects.filter(expires_at__lt=timezone.now()).delete
            )()
            
            logger.info(f"Cleaned up {expired_sessions} expired sessions")
            return expired_sessions
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    @classmethod
    async def get_user_sessions(cls, user, active_only=True):
        """
        Get all sessions for a user
        
        Args:
            user: User instance
            active_only: Only return non-expired sessions
            
        Returns:
            QuerySet of UserSession objects
        """
        try:
            queryset = UserSession.objects.filter(user=user)
            
            if active_only:
                queryset = queryset.filter(expires_at__gte=timezone.now())
            
            sessions = []
            async for session in queryset:
                sessions.append(session)
                
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get user sessions: {e}")
            return []
    
    @classmethod
    def generate_session_key(cls):
        """
        Generate a cryptographically secure session key
        
        Returns:
            40-character hex string
        """
        return secrets.token_hex(20)
    
    @classmethod
    def extract_client_info(cls, request):
        """
        Extract client information from request
        
        Args:
            request: Django request object
            
        Returns:
            Dict with client information
        """
        if not request:
            return {}
        
        # Get IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        
        # Get user agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Parse device info (basic parsing)
        device_info = cls.parse_user_agent(user_agent)
        
        return {
            'ip_address': ip_address,
            'user_agent': user_agent,
            'device_info': device_info,
        }
    
    @classmethod
    def parse_user_agent(cls, user_agent):
        """
        Parse user agent string to extract device information
        
        Args:
            user_agent: User agent string
            
        Returns:
            Dict with device information
        """
        if not user_agent:
            return {}
        
        # Basic parsing - could be enhanced with a proper library
        device_info = {
            'browser': 'Unknown',
            'os': 'Unknown',
            'device_type': 'Unknown',
        }
        
        user_agent_lower = user_agent.lower()
        
        # Detect browser
        if 'chrome' in user_agent_lower:
            device_info['browser'] = 'Chrome'
        elif 'firefox' in user_agent_lower:
            device_info['browser'] = 'Firefox'
        elif 'safari' in user_agent_lower:
            device_info['browser'] = 'Safari'
        elif 'edge' in user_agent_lower:
            device_info['browser'] = 'Edge'
        
        # Detect OS
        if 'windows' in user_agent_lower:
            device_info['os'] = 'Windows'
        elif 'mac' in user_agent_lower:
            device_info['os'] = 'macOS'
        elif 'linux' in user_agent_lower:
            device_info['os'] = 'Linux'
        elif 'android' in user_agent_lower:
            device_info['os'] = 'Android'
        elif 'ios' in user_agent_lower:
            device_info['os'] = 'iOS'
        
        # Detect device type
        if 'mobile' in user_agent_lower:
            device_info['device_type'] = 'Mobile'
        elif 'tablet' in user_agent_lower:
            device_info['device_type'] = 'Tablet'
        else:
            device_info['device_type'] = 'Desktop'
        
        return device_info


# Convenience functions for common operations
async def create_user_session(user, request=None, **kwargs):
    """Create a new user session"""
    return await AsyncSessionManager.create_session(user, request, **kwargs)


async def validate_user_session(session_key):
    """Validate a user session"""
    return await AsyncSessionManager.validate_session(session_key)


async def destroy_user_session(session_key):
    """Destroy a user session"""
    return await AsyncSessionManager.destroy_session(session_key)


async def cleanup_expired_sessions():
    """Clean up expired sessions"""
    return await AsyncSessionManager.cleanup_expired_sessions()