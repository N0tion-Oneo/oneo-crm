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
from django.contrib.auth import get_user_model
from .serializers import UserSerializer
from .models import UserType
from .jwt_authentication import TenantAwareJWTAuthentication

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with user info and permissions"""
    
    username_field = 'email'  # Use email as username field
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['email'] = user.email
        token['user_type'] = user.user_type.slug if user.user_type else None
        
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add user information to response
        user_serializer = UserSerializer(self.user)
        data['user'] = user_serializer.data
        
        # Add permissions (simplified for now)
        if self.user.user_type:
            data['permissions'] = self.user.user_type.base_permissions
        else:
            data['permissions'] = {}
            
        return data


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
    
    # Get permissions
    user_permissions = {}
    if request.user.user_type:
        user_permissions = request.user.user_type.base_permissions
    
    return Response({
        'user': user_serializer.data,
        'permissions': user_permissions
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