"""
Celery tasks for authentication-related async processing
"""

from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, name='authentication.tasks.process_ai_response')
def process_ai_response(self, user_id, prompt, context_data=None):
    """
    Process AI-powered responses for user queries
    Used for: AI-powered help, user onboarding assistance, etc.
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Simulate AI processing (replace with actual AI integration)
        import time
        time.sleep(2)  # Simulate processing time
        
        ai_response = {
            'user_id': user_id,
            'prompt': prompt,
            'response': f"AI response for: {prompt}",
            'status': 'completed',
            'context': context_data
        }
        
        # Cache the result for retrieval
        cache_key = f"ai_response:{self.request.id}"
        cache.set(cache_key, ai_response, timeout=3600)  # 1 hour
        
        logger.info(f"AI response processed for user {user_id}")
        return ai_response
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for AI processing")
        return {'error': 'User not found'}
    except Exception as e:
        logger.error(f"AI processing error: {e}")
        return {'error': str(e)}


@shared_task(bind=True, name='authentication.tasks.update_user_permissions')
def update_user_permissions(self, user_id, permission_changes):
    """
    Async task to update user permissions and clear caches
    """
    try:
        user = User.objects.get(id=user_id)
        
        # Update permissions
        if 'user_type_id' in permission_changes:
            user.user_type_id = permission_changes['user_type_id']
            user.save()
        
        if 'permission_overrides' in permission_changes:
            user.permission_overrides = permission_changes['permission_overrides']
            user.save()
        
        # Clear permission cache
        from .permissions import AsyncPermissionManager
        permission_manager = AsyncPermissionManager(user)
        cache.delete(permission_manager.cache_key)
        
        logger.info(f"Permissions updated for user {user_id}")
        return {'status': 'success', 'user_id': user_id}
        
    except User.DoesNotExist:
        error_msg = f"User {user_id} not found"
        logger.error(error_msg)
        return {'error': error_msg}
    except Exception as e:
        error_msg = f"Permission update error: {e}"
        logger.error(error_msg)
        return {'error': error_msg}


@shared_task(bind=True, name='authentication.tasks.cleanup_expired_sessions')
def cleanup_expired_sessions(self):
    """
    Clean up expired user sessions
    """
    try:
        from .models import UserSession
        from django.utils import timezone
        
        expired_count = UserSession.objects.filter(
            expires_at__lt=timezone.now()
        ).count()
        
        UserSession.objects.filter(expires_at__lt=timezone.now()).delete()
        
        logger.info(f"Cleaned up {expired_count} expired sessions")
        return {'cleaned_sessions': expired_count}
        
    except Exception as e:
        error_msg = f"Session cleanup error: {e}"
        logger.error(error_msg)
        return {'error': error_msg}