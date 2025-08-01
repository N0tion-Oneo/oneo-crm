"""
Tenant-aware JWT Authentication for django-tenants
Ensures JWT authentication works correctly in multi-tenant context
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import UntypedToken
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class TenantAwareJWTAuthentication(JWTAuthentication):
    """
    JWT Authentication that works correctly with django-tenants
    Ensures user lookup happens in the correct tenant schema
    """
    
    def get_user(self, validated_token):
        """
        Get user from validated token, ensuring tenant context is used
        """
        try:
            user_id = validated_token['user_id']
            
            # Get tenant from current request context
            request = getattr(self, '_current_request', None)
            tenant = getattr(request, 'tenant', None) if request else None
            
            if tenant:
                # Use tenant schema context explicitly
                with schema_context(tenant.schema_name):
                    try:
                        user = User.objects.get(id=user_id)
                        logger.debug(f"Found user {user.email} in tenant {tenant.schema_name}")
                        return user
                    except User.DoesNotExist:
                        logger.error(f"User {user_id} not found in tenant {tenant.schema_name}")
                        raise InvalidToken("User not found in tenant")
            else:
                # No tenant context, try current schema (fallback)
                try:
                    user = User.objects.get(id=user_id)
                    logger.warning(f"Found user {user.email} in current schema (no tenant context)")
                    return user
                except User.DoesNotExist:
                    logger.error(f"User {user_id} not found in any schema")
                    raise InvalidToken("User not found")
                
        except KeyError:
            logger.error("No user_id in token")
            raise InvalidToken("Token contained no recognizable user identification")
    
    def get_current_request(self):
        """
        Get the current request from thread local storage
        This is a bit of a hack but necessary for tenant context
        """
        import threading
        return getattr(threading.current_thread(), 'request', None)
    
    def authenticate(self, request):
        """
        Authenticate request with tenant-aware user lookup
        """
        try:
            # Store request for tenant context access
            self._current_request = request
            
            # Debug tenant context
            tenant = getattr(request, 'tenant', None)
            logger.debug(f"JWT authenticate called - Tenant: {tenant}")
            logger.debug(f"Request host: {request.get_host()}")
            logger.debug(f"Request path: {request.path}")
            
            # Get the header and extract the token
            header = self.get_header(request)
            if header is None:
                logger.debug("No authorization header found")
                return None
            
            raw_token = self.get_raw_token(header)
            if raw_token is None:
                logger.debug("No token in authorization header")
                return None
            
            logger.debug(f"JWT token found: {raw_token[:20]}...")
            
            # Validate the token
            validated_token = self.get_validated_token(raw_token)
            logger.debug(f"JWT token validated: {validated_token.get('user_id')}")
            
            # Get the user (this will use our custom get_user method with tenant context)
            user = self.get_user(validated_token)
            
            logger.info(f"JWT authentication successful for user: {user.email}")
            
            # Log tenant context if available
            if tenant:
                logger.info(f"Authenticated user {user.email} in tenant {tenant.schema_name}")
            else:
                logger.warning("No tenant context available during JWT authentication")
            
            return (user, validated_token)
                
        except TokenError as e:
            logger.debug(f"JWT token error: {e}")
            return None
        except Exception as e:
            logger.error(f"JWT authentication error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
        finally:
            # Clean up request reference
            if hasattr(self, '_current_request'):
                delattr(self, '_current_request')