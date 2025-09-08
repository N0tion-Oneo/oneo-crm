"""
DRF ViewSets for Authentication Management
Clean, RESTful API endpoints using Django REST Framework
"""

from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import (
    UserType, UserSession, UserTypePipelinePermission, 
    UserTypeFieldPermission, UserPipelinePermissionOverride
)
from .serializers import (
    UserSerializer, UserTypeSerializer, UserSessionSerializer,
    ChangePasswordSerializer, UserCreateSerializer, UserUpdateSerializer,
    UserTypePipelinePermissionSerializer, UserTypeFieldPermissionSerializer,
    UserPipelinePermissionOverrideSerializer
)
from .jwt_authentication import TenantAwareJWTAuthentication
from .permissions import SyncPermissionManager
from .permissions_registry import (
    get_complete_permission_schema, 
    get_permission_matrix_configuration
)
from tenants.models import Tenant

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    Comprehensive user management ViewSet with UserType assignment
    """
    queryset = User.objects.all()  # Base queryset - will be filtered in get_queryset()
    authentication_classes = [TenantAwareJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user_type', 'is_active', 'is_staff']
    search_fields = ['email', 'first_name', 'last_name', 'username']
    ordering_fields = ['email', 'first_name', 'last_name', 'date_joined', 'last_login']
    ordering = ['-date_joined']
    
    def get_queryset(self):
        """Filter users based on permissions"""
        user = self.request.user
        
        # Use comprehensive permission system
        permission_manager = SyncPermissionManager(user)
        
        # Check if user can manage all users
        if permission_manager.has_permission('action', 'users', 'read_all'):
            return User.objects.select_related('user_type').all()
        
        # Check if user can read users
        if permission_manager.has_permission('action', 'users', 'read'):
            return User.objects.select_related('user_type').all()
        
        # Users can at minimum see themselves
        return User.objects.filter(id=user.id).select_related('user_type')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer
    
    def perform_create(self, serializer):
        """Create user with proper permissions and tracking"""
        user = self.request.user
        
        # Check create permission
        permission_manager = SyncPermissionManager(user)
        if not permission_manager.has_permission('action', 'users', 'create'):
            raise PermissionError("You don't have permission to create users")
        
        # Set created_by
        serializer.save(created_by=user)
    
    def perform_update(self, serializer):
        """Update user with proper permissions"""
        user = self.request.user
        target_user = self.get_object()
        
        # Check update permission
        permission_manager = SyncPermissionManager(user)
        
        # Check if user can modify this target user
        if not permission_manager.can_modify_user(target_user):
            raise PermissionError("You don't have permission to modify this user")
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """Soft delete user instead of hard delete"""
        user = self.request.user
        permission_manager = SyncPermissionManager(user)
        
        # Check delete permission
        if not permission_manager.has_permission('action', 'users', 'delete'):
            raise PermissionError("You don't have permission to delete users")
        
        # Don't allow deleting yourself
        if instance.id == user.id:
            raise PermissionError("You cannot delete your own account")
        
        # Soft delete by deactivating
        instance.is_active = False
        instance.save(update_fields=['is_active'])
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user information"""
        serializer = self.get_serializer(request.user)
        
        # Get comprehensive permissions
        permission_manager = SyncPermissionManager(request.user)
        user_permissions = permission_manager.get_user_permissions()
        
        return Response({
            'user': serializer.data,
            'permissions': user_permissions
        })
    
    @action(detail=True, methods=['post'])
    def assign_user_type(self, request, pk=None):
        """Assign a user type to a user"""
        target_user = self.get_object()
        user_type_id = request.data.get('user_type_id')
        
        if not user_type_id:
            return Response(
                {'error': 'user_type_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check permission
        permission_manager = SyncPermissionManager(request.user)
        if not permission_manager.has_permission('action', 'users', 'assign_roles'):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            user_type = UserType.objects.get(id=user_type_id)
            target_user.user_type = user_type
            target_user.save(update_fields=['user_type'])
            
            # Clear permission cache for the user
            permission_manager_target = SyncPermissionManager(target_user)
            permission_manager_target.clear_cache()
            
            serializer = self.get_serializer(target_user)
            return Response(serializer.data)
            
        except UserType.DoesNotExist:
            return Response(
                {'error': 'User type not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a user account"""
        target_user = self.get_object()
        
        # Check permission
        permission_manager = SyncPermissionManager(request.user)
        if not permission_manager.has_permission('action', 'users', 'update'):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        target_user.is_active = True
        target_user.save(update_fields=['is_active'])
        
        serializer = self.get_serializer(target_user)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a user account"""
        target_user = self.get_object()
        
        # Check permission
        permission_manager = SyncPermissionManager(request.user)
        if not permission_manager.has_permission('action', 'users', 'update'):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Don't allow deactivating yourself
        if target_user.id == request.user.id:
            return Response(
                {'error': 'You cannot deactivate your own account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        target_user.is_active = False
        target_user.save(update_fields=['is_active'])
        
        serializer = self.get_serializer(target_user)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """Reset user password (admin only)"""
        target_user = self.get_object()
        new_password = request.data.get('new_password')
        
        if not new_password:
            return Response(
                {'error': 'new_password is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check permission
        permission_manager = SyncPermissionManager(request.user)
        if not permission_manager.has_permission('action', 'users', 'update'):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        target_user.set_password(new_password)
        target_user.save()
        
        return Response({'message': 'Password reset successfully'})
    
    @action(detail=True, methods=['get'])
    def permissions(self, request, pk=None):
        """Get user's permissions"""
        target_user = self.get_object()
        
        # Check permission to view permissions
        permission_manager = SyncPermissionManager(request.user)
        if not permission_manager.can_access_user(target_user):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get target user's permissions
        target_permission_manager = SyncPermissionManager(target_user)
        permissions = target_permission_manager.get_user_permissions()
        
        return Response({
            'user_id': target_user.id,
            'permissions': permissions,
            'user_type': target_user.user_type.name if target_user.user_type else None
        })
    
    @action(detail=True, methods=['get'])
    def sessions(self, request, pk=None):
        """Get user's active sessions"""
        target_user = self.get_object()
        
        # Check permission
        permission_manager = SyncPermissionManager(request.user)
        if not permission_manager.can_access_user(target_user):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        sessions = UserSession.objects.filter(
            user=target_user,
            expires_at__gt=timezone.now()
        ).order_by('-last_activity')
        
        serializer = UserSessionSerializer(sessions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get user statistics"""
        # Check permission
        permission_manager = SyncPermissionManager(request.user)
        if not permission_manager.has_permission('action', 'users', 'read'):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        queryset = self.get_queryset()
        
        stats = {
            'total_users': queryset.count(),
            'active_users': queryset.filter(is_active=True).count(),
            'inactive_users': queryset.filter(is_active=False).count(),
            'user_types': {}
        }
        
        # User type breakdown
        user_type_counts = queryset.values('user_type__name').annotate(
            count=Count('id')
        ).order_by('user_type__name')
        
        for item in user_type_counts:
            type_name = item['user_type__name'] or 'No Type'
            stats['user_types'][type_name] = item['count']
        
        return Response(stats)
    
    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        """Change user password"""
        user = self.get_object()
        
        # Only allow users to change their own password unless admin
        if user != request.user and not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            # Verify old password if changing own password
            if user == request.user:
                if not user.check_password(serializer.validated_data['old_password']):
                    return Response(
                        {'error': 'Current password is incorrect'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Set new password
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            return Response({'message': 'Password changed successfully'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def update_permission_overrides(self, request, pk=None):
        """Update permission overrides for a specific user"""
        target_user = self.get_object()
        new_overrides = request.data.get('permission_overrides', {})
        
        # Check permission
        permission_manager = SyncPermissionManager(request.user)
        if not permission_manager.has_permission('action', 'users', 'update'):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate overrides structure
        if not isinstance(new_overrides, dict):
            return Response(
                {'error': 'Permission overrides must be a dictionary'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update permission overrides
        target_user.permission_overrides = new_overrides
        target_user.save(update_fields=['permission_overrides'])
        
        # Clear permission cache for the user
        permission_manager_target = SyncPermissionManager(target_user)
        permission_manager_target.clear_cache()
        
        serializer = self.get_serializer(target_user)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_permission_override(self, request, pk=None):
        """Add a specific permission override to a user"""
        target_user = self.get_object()
        category = request.data.get('category')
        action = request.data.get('action')
        
        if not category or not action:
            return Response(
                {'error': 'Category and action are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check permission
        permission_manager = SyncPermissionManager(request.user)
        if not permission_manager.has_permission('action', 'users', 'update'):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Add permission override
        overrides = target_user.permission_overrides.copy()
        if category not in overrides:
            overrides[category] = []
        
        if action not in overrides[category]:
            overrides[category].append(action)
            target_user.permission_overrides = overrides
            target_user.save(update_fields=['permission_overrides'])
            
            # Clear cache
            permission_manager_target = SyncPermissionManager(target_user)
            permission_manager_target.clear_cache()
        
        serializer = self.get_serializer(target_user)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def remove_permission_override(self, request, pk=None):
        """Remove a specific permission override from a user"""
        target_user = self.get_object()
        category = request.data.get('category')
        action = request.data.get('action')
        
        if not category or not action:
            return Response(
                {'error': 'Category and action are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check permission
        permission_manager = SyncPermissionManager(request.user)
        if not permission_manager.has_permission('action', 'users', 'update'):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Remove permission override
        overrides = target_user.permission_overrides.copy()
        if category in overrides and action in overrides[category]:
            overrides[category].remove(action)
            
            # Remove empty categories
            if not overrides[category]:
                del overrides[category]
            
            target_user.permission_overrides = overrides
            target_user.save(update_fields=['permission_overrides'])
            
            # Clear cache
            permission_manager_target = SyncPermissionManager(target_user)
            permission_manager_target.clear_cache()
        
        serializer = self.get_serializer(target_user)
        return Response(serializer.data)


class UserTypeViewSet(viewsets.ModelViewSet):
    """
    UserType management ViewSet
    """
    queryset = UserType.objects.all()
    serializer_class = UserTypeSerializer
    authentication_classes = [TenantAwareJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_system_default', 'is_custom']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Filter user types based on permissions"""
        user = self.request.user
        
        # Check permission
        permission_manager = SyncPermissionManager(user)
        if not permission_manager.has_permission('action', 'user_types', 'read'):
            return UserType.objects.none()
        
        return UserType.objects.all()
    
    def perform_create(self, serializer):
        """Create user type with proper permissions"""
        user = self.request.user
        
        # Check create permission
        permission_manager = SyncPermissionManager(user)
        if not permission_manager.has_permission('action', 'user_types', 'create'):
            raise PermissionError("You don't have permission to create user types")
        
        # Set created_by and mark as custom
        serializer.save(created_by=user, is_custom=True, is_system_default=False)
    
    def perform_update(self, serializer):
        """Update user type with restrictions on system defaults"""
        user = self.request.user
        user_type = self.get_object()
        
        # Check update permission
        permission_manager = SyncPermissionManager(user)
        if not permission_manager.has_permission('action', 'user_types', 'update'):
            raise PermissionError("You don't have permission to update user types")
        
        # Prevent modification of system default types (except permissions)
        if user_type.is_system_default:
            # Only allow updating base_permissions
            allowed_fields = {'base_permissions', 'description'}
            update_fields = set(serializer.validated_data.keys())
            
            if not update_fields.issubset(allowed_fields):
                raise PermissionError("System default user types can only have permissions and description updated")
        
        serializer.save()
        
        # Clear cache for all users of this type
        from asgiref.sync import async_to_sync
        from .permissions import AsyncPermissionManager
        async_to_sync(AsyncPermissionManager.clear_user_type_cache)(user_type.id)
    
    def perform_destroy(self, instance):
        """Prevent deletion of system default types"""
        user = self.request.user
        
        # Check delete permission
        permission_manager = SyncPermissionManager(user)
        if not permission_manager.has_permission('action', 'user_types', 'delete'):
            raise PermissionError("You don't have permission to delete user types")
        
        # Prevent deletion of system default types
        if instance.is_system_default:
            raise PermissionError("Cannot delete system default user types")
        
        # Check if any users have this type
        if User.objects.filter(user_type=instance).exists():
            raise PermissionError("Cannot delete user type that is assigned to users")
        
        instance.delete()
    
    @action(detail=True, methods=['get'])
    def users(self, request, pk=None):
        """Get users assigned to this user type"""
        user_type = self.get_object()
        
        # Check permission
        permission_manager = SyncPermissionManager(request.user)
        if not permission_manager.has_permission('action', 'users', 'read'):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        users = User.objects.filter(user_type=user_type).select_related('user_type')
        serializer = UserSerializer(users, many=True)
        
        return Response({
            'user_type': user_type.name,
            'users': serializer.data,
            'count': users.count()
        })
    
    @action(detail=False, methods=['get'])
    def defaults(self, request):
        """Get system default user types"""
        default_types = UserType.objects.filter(is_system_default=True)
        serializer = self.get_serializer(default_types, many=True)
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def update_permissions(self, request, pk=None):
        """Update permissions for a user type"""
        user_type = self.get_object()
        new_permissions = request.data.get('permissions', {})
        
        # Check update permission
        permission_manager = SyncPermissionManager(request.user)
        if not permission_manager.has_permission('action', 'user_types', 'update'):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate permissions structure
        if not isinstance(new_permissions, dict):
            return Response(
                {'error': 'Permissions must be a dictionary'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # For system default types, only allow updating certain permissions
        if user_type.is_system_default:
            # Get current permissions and only update allowed changes
            current_permissions = user_type.base_permissions.copy()
            # Allow updating individual permissions but preserve core structure
            for category, actions in new_permissions.items():
                if category in current_permissions:
                    current_permissions[category] = actions
            user_type.base_permissions = current_permissions
        else:
            # For custom types, allow full permission updates
            user_type.base_permissions = new_permissions
        
        user_type.save()
        
        # Clear cache for all users of this type
        from asgiref.sync import async_to_sync
        from .permissions import AsyncPermissionManager
        async_to_sync(AsyncPermissionManager.clear_user_type_cache)(user_type.id)
        
        serializer = self.get_serializer(user_type)
        return Response(serializer.data)
    
    def _normalize_category_name(self, category):
        """Normalize category names to prevent conflicts"""
        # Map singular forms to plural forms
        category_mapping = {
            'user': 'users',
            'record': 'records',
            'field': 'fields',
            'pipeline': 'pipelines',
            'workflow': 'workflows',
            'relationship': 'relationships',
            'communication': 'communications',
            'business': 'business_rules',
            'ai': 'ai_features',
            'api': 'api_access'
        }
        
        # Return normalized form if mapping exists, otherwise return original
        return category_mapping.get(category.lower(), category.lower())
    
    @action(detail=True, methods=['post'])
    def add_permission(self, request, pk=None):
        """Add a specific permission to a user type"""
        user_type = self.get_object()
        category = request.data.get('category')
        action = request.data.get('action')
        
        if not category or not action:
            return Response(
                {'error': 'Category and action are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Normalize category name to prevent conflicts
        normalized_category = self._normalize_category_name(category)
        
        # Check permission - user needs both user_types.update AND permissions.manage
        permission_manager = SyncPermissionManager(request.user)
        if not (permission_manager.has_permission('action', 'user_types', 'update') and 
                permission_manager.has_permission('action', 'permissions', 'manage')):
            return Response(
                {'error': 'Permission denied: Requires user_types.update and permissions.manage'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Add permission using normalized category
        permissions = user_type.base_permissions.copy()
        
        # Handle both flat array and nested object formats
        if normalized_category not in permissions:
            # For settings, use nested format, for others use flat array
            if normalized_category == 'settings':
                permissions[normalized_category] = {'actions': []}
            else:
                permissions[normalized_category] = []
        
        # Check current format and add permission accordingly
        category_perms = permissions[normalized_category]
        if isinstance(category_perms, dict) and 'actions' in category_perms:
            # Nested format (e.g., settings)
            if action not in category_perms['actions']:
                category_perms['actions'].append(action)
                user_type.base_permissions = permissions
                user_type.save()
        elif isinstance(category_perms, list):
            # Flat array format
            if action not in category_perms:
                category_perms.append(action)
                user_type.base_permissions = permissions
                user_type.save()
            
        
        serializer = self.get_serializer(user_type)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def remove_permission(self, request, pk=None):
        """Remove a specific permission from a user type"""
        user_type = self.get_object()
        category = request.data.get('category')
        action = request.data.get('action')
        
        if not category or not action:
            return Response(
                {'error': 'Category and action are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Normalize category name to prevent conflicts
        normalized_category = self._normalize_category_name(category)
        
        # Check permission - user needs both user_types.update AND permissions.manage
        permission_manager = SyncPermissionManager(request.user)
        if not (permission_manager.has_permission('action', 'user_types', 'update') and 
                permission_manager.has_permission('action', 'permissions', 'manage')):
            return Response(
                {'error': 'Permission denied: Requires user_types.update and permissions.manage'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Prevent removing critical permissions from Admin
        if user_type.slug == 'admin' and normalized_category == 'system' and action == 'full_access':
            return Response(
                {'error': 'Cannot remove full_access from Admin user type'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Remove permission using normalized category
        permissions = user_type.base_permissions.copy()
        
        if normalized_category in permissions:
            category_perms = permissions[normalized_category]
            
            # Handle both flat array and nested object formats
            if isinstance(category_perms, dict) and 'actions' in category_perms:
                # Nested format (e.g., settings)
                if action in category_perms['actions']:
                    category_perms['actions'].remove(action)
                    
                    # Don't remove settings category even if empty, maintain structure
                    user_type.base_permissions = permissions
                    user_type.save()
            elif isinstance(category_perms, list):
                # Flat array format
                if action in category_perms:
                    category_perms.remove(action)
                    
                    # Remove empty categories for flat format
                    if not category_perms:
                        del permissions[normalized_category]
                    
                    user_type.base_permissions = permissions
                    user_type.save()
            
        
        serializer = self.get_serializer(user_type)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def grant_pipeline_access(self, request, pk=None):
        """Grant access to a specific pipeline for this user type"""
        user_type = self.get_object()
        pipeline_id = request.data.get('pipeline_id')
        access_level = request.data.get('access_level', 'read')
        permissions = request.data.get('permissions', [])
        
        if not pipeline_id:
            return Response(
                {'error': 'pipeline_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check permission
        permission_manager = SyncPermissionManager(request.user)
        if not permission_manager.has_permission('action', 'user_types', 'update'):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Use helper method to get default permissions if none provided
        if not permissions:
            permissions = self._get_default_pipeline_permissions(access_level)
        
        # Create or update pipeline permission
        pipeline_perm, created = UserTypePipelinePermission.objects.update_or_create(
            user_type=user_type,
            pipeline_id=pipeline_id,
            defaults={
                'access_level': access_level,
                'permissions': permissions,
                'can_view_all_records': access_level in ['read', 'write', 'admin'],
                'can_edit_all_records': access_level in ['write', 'admin'],
                'can_delete_records': access_level == 'admin',
                'can_export_data': access_level in ['read', 'write', 'admin'],
                'can_import_data': access_level in ['write', 'admin'],
                'created_by': request.user if created else pipeline_perm.created_by,
            }
        )
        
        # Clear cache for all users of this type
        from asgiref.sync import async_to_sync
        from .permissions import AsyncPermissionManager
        async_to_sync(AsyncPermissionManager.clear_user_type_cache)(user_type.id)
        
        serializer = UserTypePipelinePermissionSerializer(pipeline_perm)
        
        return Response({
            'message': f'Pipeline access {"created" if created else "updated"}',
            'pipeline_permission': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def revoke_pipeline_access(self, request, pk=None):
        """Revoke access to a specific pipeline for this user type"""
        user_type = self.get_object()
        pipeline_id = request.data.get('pipeline_id')
        
        if not pipeline_id:
            return Response(
                {'error': 'pipeline_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check permission
        permission_manager = SyncPermissionManager(request.user)
        if not permission_manager.has_permission('action', 'user_types', 'update'):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Delete the pipeline permission
        try:
            pipeline_perm = UserTypePipelinePermission.objects.get(
                user_type=user_type,
                pipeline_id=pipeline_id
            )
            pipeline_perm.delete()
            
            # Clear cache for all users of this type
            from asgiref.sync import async_to_sync
            from .permissions import AsyncPermissionManager
            async_to_sync(AsyncPermissionManager.clear_user_type_cache)(user_type.id)
            
            return Response({'message': 'Pipeline access revoked successfully'})
            
        except UserTypePipelinePermission.DoesNotExist:
            return Response(
                {'error': 'Pipeline permission not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def pipeline_access(self, request, pk=None):
        """Get all pipeline permissions for this user type"""
        user_type = self.get_object()
        
        # Check permission
        permission_manager = SyncPermissionManager(request.user)
        if not permission_manager.has_permission('action', 'user_types', 'read'):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get all pipeline permissions for this user type
        pipeline_permissions = UserTypePipelinePermission.objects.filter(
            user_type=user_type
        ).order_by('pipeline_id')
        
        serializer = UserTypePipelinePermissionSerializer(pipeline_permissions, many=True)
        
        return Response({
            'user_type': user_type.name,
            'pipeline_permissions': serializer.data,
            'count': pipeline_permissions.count()
        })
    
    def _get_default_pipeline_permissions(self, access_level):
        """Get default permissions based on access level"""
        permission_mapping = {
            'none': [],
            'read': ['read'],
            'write': ['read', 'create', 'update'],
            'admin': ['read', 'create', 'update', 'delete', 'export', 'import', 'clone']
        }
        return permission_mapping.get(access_level, ['read'])
    
    def _determine_access_level(self, permissions):
        """Determine access level based on permissions list"""
        if not permissions:
            return 'none'
        elif 'delete' in permissions or 'clone' in permissions:
            return 'admin'
        elif 'create' in permissions or 'update' in permissions:
            return 'write'
        elif 'read' in permissions:
            return 'read'
        else:
            return 'none'


class UserSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    User session management (read-only)
    """
    serializer_class = UserSessionSerializer
    authentication_classes = [TenantAwareJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['user']
    ordering_fields = ['created_at', 'last_activity', 'expires_at']
    ordering = ['-last_activity']
    
    def get_queryset(self):
        """Filter sessions based on permissions"""
        user = self.request.user
        
        # Check permission
        permission_manager = SyncPermissionManager(user)
        
        # Users can see their own sessions
        if permission_manager.has_permission('action', 'users', 'read_all'):
            return UserSession.objects.select_related('user').all()
        else:
            return UserSession.objects.filter(user=user).select_related('user')
    
    @action(detail=True, methods=['post'])
    def terminate(self, request, pk=None):
        """Terminate a session"""
        session = self.get_object()
        user = request.user
        
        # Check permission - users can terminate their own sessions or admins can terminate any
        permission_manager = SyncPermissionManager(user)
        
        if not (session.user == user or permission_manager.has_permission('action', 'users', 'update')):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Don't allow terminating current session via this method
        current_session_key = getattr(request.session, 'session_key', None)
        if session.session_key == current_session_key:
            return Response(
                {'error': 'Cannot terminate current session. Use logout instead.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Terminate the session
        session.delete()
        
        return Response({'message': 'Session terminated successfully'})
    
    @action(detail=False, methods=['delete'])
    def destroy_all(self, request):
        """Destroy all user sessions except current one"""
        current_session_key = getattr(request.session, 'session_key', None)
        
        # Delete all sessions except current
        deleted_count = 0
        if current_session_key:
            deleted_count = UserSession.objects.filter(
                user=request.user
            ).exclude(session_key=current_session_key).delete()[0]
        else:
            deleted_count = UserSession.objects.filter(user=request.user).delete()[0]
        
        return Response({
            'message': f'Destroyed {deleted_count} sessions',
            'destroyed_count': deleted_count
        })


class UserTypePipelinePermissionViewSet(viewsets.ModelViewSet):
    """
    Pipeline-specific permissions for user types
    """
    queryset = UserTypePipelinePermission.objects.all()
    authentication_classes = [TenantAwareJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['user_type', 'pipeline_id', 'access_level']
    ordering = ['user_type', 'pipeline_id']
    
    def get_serializer_class(self):
        return UserTypePipelinePermissionSerializer
    
    def get_queryset(self):
        """Return pipeline permissions based on user access level"""
        user = self.request.user
        permission_manager = SyncPermissionManager(user)
        
        if not user.is_authenticated:
            return UserTypePipelinePermission.objects.none()
        
        # If user has pipeline access management permission, show all pipeline access entries
        if permission_manager.has_permission('action', 'pipelines', 'access'):
            return UserTypePipelinePermission.objects.select_related('user_type').all()
        
        # Otherwise, only show current user's pipeline access (for runtime access checking)
        if user.user_type:
            return UserTypePipelinePermission.objects.filter(
                user_type=user.user_type
            ).select_related('user_type')
        
        return UserTypePipelinePermission.objects.none()
    
    @action(detail=False, methods=['get'])
    def by_user_type(self, request):
        """Get pipeline permissions for a specific user type"""
        user_type_id = request.query_params.get('user_type_id')
        if not user_type_id:
            return Response(
                {'error': 'user_type_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        permissions = self.get_queryset().filter(user_type_id=user_type_id)
        serializer = self.get_serializer(permissions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_pipeline(self, request):
        """Get all user type permissions for a specific pipeline"""
        pipeline_id = request.query_params.get('pipeline_id')
        if not pipeline_id:
            return Response(
                {'error': 'pipeline_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        permissions = self.get_queryset().filter(pipeline_id=pipeline_id)
        serializer = self.get_serializer(permissions, many=True)
        return Response(serializer.data)
    

    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """Bulk update pipeline permissions for multiple user types"""
        data = request.data
        pipeline_id = data.get('pipeline_id')
        user_type_permissions = data.get('user_type_permissions', [])
        
        if not pipeline_id or not user_type_permissions:
            return Response(
                {'error': 'pipeline_id and user_type_permissions are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check permission
        permission_manager = SyncPermissionManager(request.user)
        if not permission_manager.has_permission('action', 'user_types', 'update'):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        updated_permissions = []
        for perm_data in user_type_permissions:
            user_type_id = perm_data.get('user_type_id')
            access_level = perm_data.get('access_level', 'read')
            permissions = perm_data.get('permissions', [])
            
            pipeline_perm, created = UserTypePipelinePermission.objects.update_or_create(
                user_type_id=user_type_id,
                pipeline_id=pipeline_id,
                defaults={
                    'access_level': access_level,
                    'permissions': permissions,
                    'can_view_all_records': perm_data.get('can_view_all_records', True),
                    'can_edit_all_records': perm_data.get('can_edit_all_records', False),
                    'can_delete_records': perm_data.get('can_delete_records', False),
                    'can_export_data': perm_data.get('can_export_data', True),
                    'can_import_data': perm_data.get('can_import_data', False),
                    'created_by': request.user if created else None,
                }
            )
            updated_permissions.append(pipeline_perm)
        
        serializer = self.get_serializer(updated_permissions, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Create a new pipeline access entry - requires pipelines.access"""
        permission_manager = SyncPermissionManager(request.user)
        
        # Check for pipeline access management permission
        if not permission_manager.has_permission('action', 'pipelines', 'access'):
            return Response(
                {'error': 'Permission denied: Requires pipelines.access'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Update a pipeline access entry - requires pipelines.access"""
        permission_manager = SyncPermissionManager(request.user)
        
        if not permission_manager.has_permission('action', 'pipelines', 'access'):
            return Response(
                {'error': 'Permission denied: Requires pipelines.access'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """Partially update a pipeline access entry - requires pipelines.access"""
        permission_manager = SyncPermissionManager(request.user)
        
        if not permission_manager.has_permission('action', 'pipelines', 'access'):
            return Response(
                {'error': 'Permission denied: Requires pipelines.access'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().partial_update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Delete a pipeline access entry - requires pipelines.access"""
        permission_manager = SyncPermissionManager(request.user)
        
        # Check for pipeline access management permission
        if not permission_manager.has_permission('action', 'pipelines', 'access'):
            return Response(
                {'error': 'Permission denied: Requires pipelines.access'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().destroy(request, *args, **kwargs)


class UserTypeFieldPermissionViewSet(viewsets.ModelViewSet):
    """
    Field-level permissions for user types
    """
    queryset = UserTypeFieldPermission.objects.all()
    authentication_classes = [TenantAwareJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['user_type', 'pipeline_id', 'field_id', 'visibility']
    ordering = ['user_type', 'pipeline_id', 'field_id']
    
    def get_serializer_class(self):
        return UserTypeFieldPermissionSerializer
    
    def get_queryset(self):
        """Filter field permissions based on user permissions"""
        user = self.request.user
        permission_manager = SyncPermissionManager(user)
        
        if not permission_manager.has_permission('action', 'user_types', 'read'):
            return UserTypeFieldPermission.objects.none()
        
        return UserTypeFieldPermission.objects.select_related('user_type').all()
    
    @action(detail=False, methods=['get'])
    def by_pipeline(self, request):
        """Get field permissions for a specific pipeline"""
        pipeline_id = request.query_params.get('pipeline_id')
        user_type_id = request.query_params.get('user_type_id')
        
        if not pipeline_id:
            return Response(
                {'error': 'pipeline_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(pipeline_id=pipeline_id)
        if user_type_id:
            queryset = queryset.filter(user_type_id=user_type_id)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_update_pipeline_fields(self, request):
        """Bulk update field permissions for a pipeline"""
        data = request.data
        pipeline_id = data.get('pipeline_id')
        user_type_id = data.get('user_type_id')
        field_permissions = data.get('field_permissions', [])
        
        if not all([pipeline_id, user_type_id, field_permissions]):
            return Response(
                {'error': 'pipeline_id, user_type_id, and field_permissions are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check permission
        permission_manager = SyncPermissionManager(request.user)
        if not permission_manager.has_permission('action', 'user_types', 'update'):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        updated_permissions = []
        for field_perm_data in field_permissions:
            field_id = field_perm_data.get('field_id')
            
            field_perm, created = UserTypeFieldPermission.objects.update_or_create(
                user_type_id=user_type_id,
                pipeline_id=pipeline_id,
                field_id=field_id,
                defaults={
                    'can_view': field_perm_data.get('can_view', True),
                    'can_edit': field_perm_data.get('can_edit', False),
                    'can_require': field_perm_data.get('can_require', False),
                    'visibility': field_perm_data.get('visibility', 'visible'),
                    'visibility_conditions': field_perm_data.get('visibility_conditions', {}),
                    'default_value': field_perm_data.get('default_value'),
                    'value_constraints': field_perm_data.get('value_constraints', {}),
                    'created_by': request.user if created else None,
                }
            )
            updated_permissions.append(field_perm)
        
        serializer = self.get_serializer(updated_permissions, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Create a new field permission - requires permissions.manage"""
        permission_manager = SyncPermissionManager(request.user)
        
        if not permission_manager.has_permission('action', 'permissions', 'manage'):
            return Response(
                {'error': 'Permission denied: Requires permissions.manage'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Update a field permission - requires permissions.manage"""
        permission_manager = SyncPermissionManager(request.user)
        
        if not permission_manager.has_permission('action', 'permissions', 'manage'):
            return Response(
                {'error': 'Permission denied: Requires permissions.update'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """Partially update a field permission - requires permissions.manage"""
        permission_manager = SyncPermissionManager(request.user)
        
        if not permission_manager.has_permission('action', 'permissions', 'manage'):
            return Response(
                {'error': 'Permission denied: Requires permissions.update'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().partial_update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Delete a field permission - requires permissions.manage"""
        permission_manager = SyncPermissionManager(request.user)
        
        if not permission_manager.has_permission('action', 'permissions', 'manage'):
            return Response(
                {'error': 'Permission denied: Requires permissions.manage'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().destroy(request, *args, **kwargs)


class UserPipelinePermissionOverrideViewSet(viewsets.ModelViewSet):
    """
    Individual user overrides for pipeline permissions
    """
    queryset = UserPipelinePermissionOverride.objects.all()
    authentication_classes = [TenantAwareJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['user', 'pipeline_id', 'access_level']
    ordering = ['user', 'pipeline_id']
    
    def get_serializer_class(self):
        return UserPipelinePermissionOverrideSerializer
    
    def get_queryset(self):
        """Filter user overrides based on permissions"""
        user = self.request.user
        permission_manager = SyncPermissionManager(user)
        
        if not permission_manager.has_permission('action', 'users', 'read'):
            return UserPipelinePermissionOverride.objects.none()
        
        return UserPipelinePermissionOverride.objects.select_related('user').all()
    
    @action(detail=False, methods=['get'])
    def by_user(self, request):
        """Get pipeline permission overrides for a specific user"""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        overrides = self.get_queryset().filter(user_id=user_id)
        serializer = self.get_serializer(overrides, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke a permission override (soft delete by setting expiry)"""
        override = self.get_object()
        
        # Check permission
        permission_manager = SyncPermissionManager(request.user)
        if not permission_manager.has_permission('action', 'users', 'update'):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Set expiry to now to effectively revoke
        override.expires_at = timezone.now()
        override.save(update_fields=['expires_at'])
        
        serializer = self.get_serializer(override)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Create a new user permission override - requires permissions.manage"""
        permission_manager = SyncPermissionManager(request.user)
        
        if not permission_manager.has_permission('action', 'permissions', 'manage'):
            return Response(
                {'error': 'Permission denied: Requires permissions.manage'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Update a user permission override - requires permissions.manage"""
        permission_manager = SyncPermissionManager(request.user)
        
        if not permission_manager.has_permission('action', 'permissions', 'manage'):
            return Response(
                {'error': 'Permission denied: Requires permissions.update'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """Partially update a user permission override - requires permissions.manage"""
        permission_manager = SyncPermissionManager(request.user)
        
        if not permission_manager.has_permission('action', 'permissions', 'manage'):
            return Response(
                {'error': 'Permission denied: Requires permissions.update'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().partial_update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Delete a user permission override - requires permissions.manage"""
        permission_manager = SyncPermissionManager(request.user)
        
        if not permission_manager.has_permission('action', 'permissions', 'manage'):
            return Response(
                {'error': 'Permission denied: Requires permissions.manage'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().destroy(request, *args, **kwargs)