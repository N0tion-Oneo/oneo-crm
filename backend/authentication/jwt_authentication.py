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
    
    def get_user(self, validated_token, request=None, tenant_schema=None):
        """
        Get user from validated token with direct request context (no instance variables)
        """
        try:
            user_id = validated_token['user_id']
            token_tenant_schema = validated_token.get('tenant_schema')
            
            # ✅ Use passed parameters instead of instance variables
            if request:
                tenant = getattr(request, 'tenant', None)
                current_schema = tenant.schema_name if tenant else tenant_schema
            else:
                # Fallback to connection tenant context
                from django.db import connection
                tenant = getattr(connection, 'tenant', None)
                current_schema = tenant.schema_name if tenant else tenant_schema
            
            logger.debug(f"JWT token validation - User ID: {user_id}, Token tenant: {token_tenant_schema}, Current tenant: {current_schema}")
            
            # Validate tenant context matches token
            if token_tenant_schema and current_schema and token_tenant_schema != current_schema:
                logger.warning(f"Tenant mismatch - Token tenant: {token_tenant_schema}, Current tenant: {current_schema}")
                raise InvalidToken("Token not valid for current tenant")
            
            if current_schema:
                # ✅ Use tenant schema context with additional retry logic for threading issues
                with schema_context(current_schema):
                    try:
                        # ✅ Add select_related to reduce DB queries and potential race conditions
                        user = User.objects.select_related().get(id=user_id, is_active=True)
                        logger.debug(f"Found user {user.email} (ID: {user.id}) in tenant {current_schema}")
                        
                        # Additional validation: ensure user exists in the correct tenant
                        if token_tenant_schema and token_tenant_schema != current_schema:
                            logger.error(f"User {user_id} token tenant {token_tenant_schema} != current tenant {current_schema}")
                            raise InvalidToken("User not valid for current tenant")
                        
                        return user
                    except User.DoesNotExist:
                        logger.error(f"User {user_id} not found in tenant {current_schema} (active users only)")
                        # ✅ Log additional debug info for threading issues
                        try:
                            inactive_user = User.objects.get(id=user_id)
                            logger.error(f"User {user_id} exists but is inactive: {inactive_user.is_active}")
                        except User.DoesNotExist:
                            logger.error(f"User {user_id} does not exist at all in tenant {current_schema}")
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
                
        except KeyError as e:
            logger.error(f"Missing required field in token: {e}")
            raise InvalidToken("Token contained no recognizable user identification")
    
    # ✅ Removed get_current_request method - no longer needed without instance variables
    
    def authenticate(self, request):
        """
        Authenticate request with tenant-aware user lookup (NO INSTANCE VARIABLES)
        """
        try:
            # ✅ Get tenant context directly from request (no instance storage)
            tenant = getattr(request, 'tenant', None)
            tenant_schema = tenant.schema_name if tenant else None
            
            logger.debug(f"JWT authenticate called - Tenant: {tenant} (schema: {tenant_schema})")
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
            
            # ✅ Pass request directly to get_user (no instance variables)
            user = self.get_user(validated_token, request=request, tenant_schema=tenant_schema)
            
            logger.info(f"JWT authentication successful for user: {user.email} (ID: {user.id})")
            
            # Log tenant context if available
            if tenant:
                logger.info(f"Authenticated user {user.email} (ID: {user.id}) in tenant {tenant.schema_name}")
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