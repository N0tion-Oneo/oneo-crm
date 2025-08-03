"""
Clean JWT Authentication Views using DRF
Replaces the complex async authentication system
"""

from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from .serializers import UserSerializer
from .models import UserType
from .jwt_authentication import TenantAwareJWTAuthentication
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with user info and permissions"""
    
    username_field = 'email'  # Use email as username field
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['username'] = user.username  # Add username field
        token['email'] = user.email
        token['user_type'] = user.user_type.slug if user.user_type else None
        
        # Add tenant information to JWT claims
        from django.db import connection
        tenant_schema = connection.schema_name
        token['tenant_schema'] = tenant_schema
        
        logger.info(f"Generated JWT token for user {user.email} in tenant {tenant_schema}")
        
        return token
    
    def validate(self, attrs):
        """
        Tenant-aware validation that ensures user lookup happens in correct tenant context
        """
        from django.contrib.auth import authenticate
        from django.db import connection
        
        # Get current tenant context
        tenant_schema = connection.schema_name
        logger.debug(f"JWT validation in tenant schema: {tenant_schema}")
        
        # Extract credentials
        username = attrs.get(self.username_field)
        password = attrs.get('password')
        
        logger.debug(f"Attempting authentication for email: {username} in tenant: {tenant_schema}")
        
        if username and password:
            # Ensure we're in the correct tenant context for user lookup
            # Note: django-tenants middleware should already set this, but let's be explicit
            try:
                # Attempt authentication in current tenant context
                user = authenticate(
                    request=self.context.get('request'),
                    username=username,
                    password=password
                )
                
                if user is None:
                    logger.warning(f"Authentication failed for {username} in tenant {tenant_schema}")
                    raise InvalidToken('No active account found with the given credentials')
                
                if not user.is_active:
                    logger.warning(f"Inactive user {username} attempted login in tenant {tenant_schema}")
                    raise InvalidToken('User account is disabled')
                
                logger.info(f"Successfully authenticated user {user.email} (ID: {user.id}) in tenant {tenant_schema}")
                
                # Store the authenticated user
                self.user = user
                
                # Generate refresh and access tokens for the correct tenant user
                refresh = self.get_token(user)
                
                # Prepare response data
                data = {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
                
                # Add user information to response
                user_serializer = UserSerializer(self.user)
                user_data = user_serializer.data
                
                # Add permissions and user type name to user data
                user_permissions = {}
                if self.user.user_type:
                    user_permissions = self.user.user_type.base_permissions
                    user_data['user_type_name'] = self.user.user_type.name
                else:
                    user_data['user_type_name'] = 'User'
                    
                user_data['permissions'] = user_permissions
                data['user'] = user_data
                data['permissions'] = user_permissions  # Keep this for backwards compatibility
                
                logger.debug(f"JWT validation successful for {user.email} in tenant {tenant_schema}")
                return data
                
            except Exception as e:
                logger.error(f"Authentication error for {username} in tenant {tenant_schema}: {str(e)}")
                raise InvalidToken('Authentication failed')
        else:
            logger.error("Missing username or password in JWT validation")
            raise InvalidToken('Must include email and password')


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT login view"""
    serializer_class = CustomTokenObtainPairSerializer


class CustomTokenRefreshView(TokenRefreshView):
    """Custom JWT refresh view"""
    pass


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    """
    Logout view - blacklist the refresh token
    """
    try:
        refresh_token = request.data.get("refresh_token")
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        return Response({
            'message': 'Successfully logged out'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'error': 'Invalid token'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([TenantAwareJWTAuthentication])
@permission_classes([permissions.IsAuthenticated])
def current_user_view(request):
    """
    Get current authenticated user information
    """
    # Debug JWT authentication
    print(f"DEBUG: Request user: {request.user}")
    print(f"DEBUG: Is authenticated: {request.user.is_authenticated}")
    print(f"DEBUG: Auth header: {request.META.get('HTTP_AUTHORIZATION', 'No auth header')}")
    
    if not request.user.is_authenticated:
        return Response({
            'error': 'Not authenticated',
            'debug_user': str(request.user),
            'auth_header': request.META.get('HTTP_AUTHORIZATION', 'No auth header')[:50]
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    user_serializer = UserSerializer(request.user)
    user_data = user_serializer.data
    
    # Get permissions and add them to user data
    user_permissions = {}
    if request.user.user_type:
        user_permissions = request.user.user_type.base_permissions
    
    # Add permissions and user type name to user data
    user_data['permissions'] = user_permissions
    user_data['user_type_name'] = request.user.user_type.name if request.user.user_type else 'User'
    
    return Response({
        'user': user_data,
        'permissions': user_permissions  # Keep this for backwards compatibility
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def health_check_view(request):
    """
    Health check endpoint
    """
    return Response({
        'status': 'healthy',
        'auth_type': 'JWT',
        'message': 'Authentication service is running'
    }, status=status.HTTP_200_OK)