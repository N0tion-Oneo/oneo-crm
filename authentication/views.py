"""
Async API views for authentication and user management
Uses Django REST Framework with async support and custom session management
"""

import logging
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from asgiref.sync import sync_to_async
from .models import UserType, UserSession
from .permissions import AsyncPermissionManager
from .session_utils import AsyncSessionManager
from .serializers import (
    LoginSerializer, UserSerializer, UserTypeSerializer,
    UserSessionSerializer, ChangePasswordSerializer
)

logger = logging.getLogger(__name__)
User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
async def login_view(request):
    """
    Async login endpoint using session-based authentication
    """
    try:
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid input', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        remember_me = serializer.validated_data.get('remember_me', False)

        # Authenticate user (sync operation)
        user = await sync_to_async(authenticate)(
            request=request,
            username=username,
            password=password
        )

        if not user:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return Response(
                {'error': 'Account is disabled'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Create user session
        session_timeout = None
        if remember_me:
            from datetime import timedelta
            session_timeout = timedelta(days=30)

        user_session = await AsyncSessionManager.create_session(
            user=user,
            request=request,
            timeout=session_timeout
        )

        # Serialize user data
        user_serializer = UserSerializer(user)
        
        # Get user permissions
        permission_manager = AsyncPermissionManager(user)
        permissions = await permission_manager.get_user_permissions()

        return Response({
            'message': 'Login successful',
            'user': user_serializer.data,
            'permissions': permissions,
            'session_expires_at': user_session.expires_at.isoformat(),
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Login error: {e}")
        return Response(
            {'error': 'Login failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def logout_view(request):
    """
    Async logout endpoint
    """
    try:
        # Get session key
        session_key = request.session.session_key
        if session_key:
            await AsyncSessionManager.destroy_session(session_key)

        # Clear Django session
        await sync_to_async(request.session.flush)()

        return Response(
            {'message': 'Logout successful'},
            status=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Logout error: {e}")
        return Response(
            {'error': 'Logout failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
async def current_user_view(request):
    """
    Get current authenticated user information
    """
    try:
        user = request.user
        serializer = UserSerializer(user)
        
        # Get user permissions
        permission_manager = AsyncPermissionManager(user)
        permissions = await permission_manager.get_user_permissions()
        
        # Get active sessions
        sessions = await AsyncSessionManager.get_user_sessions(user, active_only=True)
        session_serializer = UserSessionSerializer(sessions, many=True)

        return Response({
            'user': serializer.data,
            'permissions': permissions,
            'active_sessions': session_serializer.data,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Current user error: {e}")
        return Response(
            {'error': 'Failed to get user information'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def change_password_view(request):
    """
    Change user password
    """
    try:
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid input', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        # Check old password
        if not await sync_to_async(user.check_password)(old_password):
            return Response(
                {'error': 'Current password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set new password
        await sync_to_async(user.set_password)(new_password)
        await sync_to_async(user.save)()

        # Optionally destroy all other sessions
        destroy_sessions = serializer.validated_data.get('destroy_other_sessions', False)
        if destroy_sessions:
            current_session = getattr(request, 'user_session', None)
            if current_session:
                # Keep current session, destroy others
                await sync_to_async(
                    UserSession.objects.filter(user=user).exclude(id=current_session.id).delete
                )()

        return Response(
            {'message': 'Password changed successfully'},
            status=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Password change error: {e}")
        return Response(
            {'error': 'Failed to change password'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
async def user_sessions_view(request):
    """
    Get user's active sessions
    """
    try:
        user = request.user
        sessions = await AsyncSessionManager.get_user_sessions(user, active_only=True)
        serializer = UserSessionSerializer(sessions, many=True)

        return Response({
            'sessions': serializer.data,
            'total_count': len(sessions),
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"User sessions error: {e}")
        return Response(
            {'error': 'Failed to get sessions'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
async def destroy_session_view(request, session_id):
    """
    Destroy a specific user session
    """
    try:
        user = request.user
        
        # Get the session
        user_session = await sync_to_async(
            UserSession.objects.filter(user=user, id=session_id).first
        )()
        
        if not user_session:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Don't allow destroying current session via this endpoint
        current_session = getattr(request, 'user_session', None)
        if current_session and current_session.id == user_session.id:
            return Response(
                {'error': 'Cannot destroy current session. Use logout instead.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Destroy the session
        await AsyncSessionManager.destroy_session(user_session.session_key)

        return Response(
            {'message': 'Session destroyed successfully'},
            status=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Destroy session error: {e}")
        return Response(
            {'error': 'Failed to destroy session'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
async def destroy_all_sessions_view(request):
    """
    Destroy all user sessions except current one
    """
    try:
        user = request.user
        current_session = getattr(request, 'user_session', None)
        
        # Count sessions before deletion
        total_sessions = await sync_to_async(
            UserSession.objects.filter(user=user).count
        )()
        
        if current_session:
            # Destroy all except current
            destroyed_count = await sync_to_async(
                UserSession.objects.filter(user=user).exclude(id=current_session.id).count
            )()
            await sync_to_async(
                UserSession.objects.filter(user=user).exclude(id=current_session.id).delete
            )()
        else:
            # Destroy all sessions
            destroyed_count = await AsyncSessionManager.destroy_all_user_sessions(user)

        return Response({
            'message': f'Destroyed {destroyed_count} sessions',
            'destroyed_count': destroyed_count,
            'total_sessions': total_sessions,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Destroy all sessions error: {e}")
        return Response(
            {'error': 'Failed to destroy sessions'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
async def user_types_view(request):
    """
    Get available user types
    """
    try:
        # Check if user has permission to view user types
        permission_manager = AsyncPermissionManager(request.user)
        has_permission = await permission_manager.has_permission(
            'action', 'system', 'view_user_types'
        )
        
        if not has_permission:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        user_types = []
        async for user_type in UserType.objects.all():
            user_types.append(user_type)

        serializer = UserTypeSerializer(user_types, many=True)
        
        return Response({
            'user_types': serializer.data,
            'total_count': len(user_types),
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"User types error: {e}")
        return Response(
            {'error': 'Failed to get user types'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
async def user_permissions_view(request):
    """
    Get current user's detailed permissions
    """
    try:
        user = request.user
        permission_manager = AsyncPermissionManager(user)
        
        # Get all permissions
        permissions = await permission_manager.get_user_permissions()
        
        # Get permission details for specific resources if requested
        resource_type = request.GET.get('resource_type')
        resource_id = request.GET.get('resource_id')
        
        response_data = {
            'permissions': permissions,
            'user_type': user.user_type.name if user.user_type else None,
        }
        
        if resource_type:
            resource_permissions = await permission_manager.get_resource_permissions(
                resource_type, resource_id
            )
            response_data['resource_permissions'] = resource_permissions

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"User permissions error: {e}")
        return Response(
            {'error': 'Failed to get permissions'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def extend_session_view(request):
    """
    Extend current session expiration
    """
    try:
        current_session = getattr(request, 'user_session', None)
        if not current_session:
            return Response(
                {'error': 'No active session found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Extend session by default timeout
        success = await AsyncSessionManager.extend_session(current_session.session_key)
        
        if success:
            # Refresh session object
            updated_session = await AsyncSessionManager.get_session(current_session.session_key)
            return Response({
                'message': 'Session extended successfully',
                'expires_at': updated_session.expires_at.isoformat(),
            }, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Failed to extend session'},
                status=status.HTTP_400_BAD_REQUEST
            )

    except Exception as e:
        logger.error(f"Extend session error: {e}")
        return Response(
            {'error': 'Failed to extend session'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
async def health_check_view(request):
    """
    Health check endpoint for authentication service
    """
    try:
        # Check database connectivity
        user_count = await sync_to_async(User.objects.count)()
        session_count = await sync_to_async(UserSession.objects.count)()
        
        # Clean up expired sessions as part of health check
        cleaned_sessions = await AsyncSessionManager.cleanup_expired_sessions()
        
        return Response({
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'stats': {
                'total_users': user_count,
                'active_sessions': session_count - cleaned_sessions,
                'cleaned_sessions': cleaned_sessions,
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return Response(
            {'status': 'unhealthy', 'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
