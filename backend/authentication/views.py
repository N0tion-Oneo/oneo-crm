"""
DRF API views for authentication and user management
Clean DRF implementation with JWT authentication
"""

import logging
import json
from django.contrib.auth import authenticate, get_user_model, login as django_login
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
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


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(View):
    """
    Async login endpoint using session-based authentication
    """
    
    async def post(self, request):
        try:
            # Parse JSON data safely
            try:
                raw_body = request.body.decode('utf-8')
                data = json.loads(raw_body)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}, raw body: {raw_body[:100]}")
                return JsonResponse(
                    {'error': 'Invalid JSON format'},
                    status=400
                )
            except UnicodeDecodeError as e:
                logger.error(f"Unicode decode error: {e}")
                return JsonResponse(
                    {'error': 'Invalid encoding'},
                    status=400
                )
            
            serializer = LoginSerializer(data=data)
            if not serializer.is_valid():
                return JsonResponse(
                    {'error': 'Invalid input', 'details': serializer.errors},
                    status=400
                )

            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            remember_me = serializer.validated_data.get('remember_me', False)

            # Step-by-step async authentication with error isolation
            try:
                # Authenticate user (async) - TenantMainMiddleware should set correct schema
                user = await sync_to_async(authenticate)(
                    request=request,
                    username=username,
                    password=password
                )
                logger.info(f"Authentication result: {user}")
            except Exception as auth_error:
                logger.error(f"Authentication error: {auth_error}")
                return JsonResponse(
                    {'error': 'Authentication failed'},
                    status=500
                )

            if not user:
                return JsonResponse(
                    {'error': 'Invalid credentials'},
                    status=401
                )

            if not user.is_active:
                return JsonResponse(
                    {'error': 'Account is disabled'},
                    status=403
                )

            try:
                # Create user session (async)
                await sync_to_async(django_login)(request, user)
                logger.info("Django login successful")
            except Exception as login_error:
                logger.error(f"Django login error: {login_error}")
                return JsonResponse(
                    {'error': 'Login session creation failed'},
                    status=500
                )
            
            try:
                # Create session record
                session_key = 'default_key'
                if hasattr(request, 'session') and hasattr(request.session, 'session_key'):
                    session_key = request.session.session_key or 'default_key'
                
                user_session = await sync_to_async(UserSession.objects.create)(
                    user=user,
                    session_key=session_key,
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    expires_at=timezone.now() + timezone.timedelta(days=30 if remember_me else 1)
                )
                logger.info(f"User session created: {user_session.id}")
            except Exception as session_error:
                logger.error(f"Session creation error: {session_error}")
                return JsonResponse(
                    {'error': 'Session creation failed'},
                    status=500
                )

            # Serialize user data
            user_serializer = UserSerializer(user)
            
            # Get user permissions (temporarily disabled to isolate authentication issue)
            # TODO: Fix AsyncPermissionManager async context issue
            permissions = {
                'pipelines': ['create', 'read', 'update', 'delete'],  # Temporary admin permissions
                'users': ['create', 'read', 'update', 'delete'],
                'system': ['full_access']
            }

            return JsonResponse({
                'message': 'Login successful',
                'user': user_serializer.data,
                'permissions': permissions,
                'session_expires_at': user_session.expires_at.isoformat(),
            }, status=200)

        except Exception as e:
            logger.error(f"Login error: {e}")
            return JsonResponse(
                {'error': 'Login failed'},
                status=500
            )


# TODO: Convert remaining function views to async class-based views
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


class CurrentUserView(View):
    """
    Get current authenticated user information
    """
    
    async def get(self, request):
        try:
            # Check if user is authenticated
            if not request.user.is_authenticated:
                return JsonResponse(
                    {'error': 'Authentication required'},
                    status=401
                )

            # Ensure we're in the correct tenant context
            from django_tenants.utils import schema_context
            
            tenant = getattr(request, 'tenant', None)
            if not tenant:
                return JsonResponse(
                    {'error': 'Tenant context not found'},
                    status=400
                )
            
            with schema_context(tenant.schema_name):
                user = request.user
                serializer = UserSerializer(user)
                
                # Get user permissions (async)
                permission_manager = AsyncPermissionManager(user)
                permissions = await permission_manager.get_user_permissions()
                
                # Get active sessions (async)
                from .session_utils import AsyncSessionManager
                sessions = await AsyncSessionManager.get_user_sessions(user, active_only=True)
                session_serializer = UserSessionSerializer(sessions, many=True)

                return JsonResponse({
                    'user': serializer.data,
                    'permissions': permissions,
                    'active_sessions': session_serializer.data,
                }, status=200)

        except Exception as e:
            logger.error(f"Current user error: {e}")
            return JsonResponse(
                {'error': 'Failed to get user information'},
                status=500
            )


# TODO: Convert remaining function views to async class-based views
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


# TODO: Convert to async class-based view
# # @api_view(['GET'])
# # @permission_classes([IsAuthenticated])
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


# @api_view(['DELETE'])
# @permission_classes([IsAuthenticated])
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


# @api_view(['DELETE'])
# @permission_classes([IsAuthenticated])
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


# TODO: Convert to async class-based view
# # @api_view(['GET'])
# # @permission_classes([IsAuthenticated])
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


# TODO: Convert to async class-based view
# # @api_view(['GET'])
# # @permission_classes([IsAuthenticated])
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


# TODO: Convert remaining function views to async class-based views
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


# TODO: Convert to async class-based view
# # @api_view(['GET'])
# # @permission_classes([AllowAny])
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
