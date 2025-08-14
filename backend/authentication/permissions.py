"""
Async permission manager for Oneo CRM
Uses Django's native async capabilities for permission checking
"""

from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async, async_to_sync
from .models import UserType, UserTypePermission, ExtendedPermission

User = get_user_model()


class AsyncPermissionManager:
    """Async permission manager using Django's native async capabilities"""
    
    def __init__(self, user):
        self.user = user
    
    async def get_user_permissions(self):
        """Get all permissions for a user"""
        return await self._calculate_user_permissions()
    
    async def _get_user_type_permissions(self):
        """Async database query using Django's async ORM"""
        if not self.user.user_type_id:
            return {}
        
        # Use Django's native async ORM
        user_type = await UserType.objects.select_related().aget(
            id=self.user.user_type_id
        )
        return user_type.base_permissions.copy()
    
    async def _calculate_user_permissions(self):
        """Calculate user permissions using Django async ORM"""
        # Get base permissions from user type (native async DB query)
        base_permissions = await self._get_user_type_permissions()
        
        # Apply user-specific overrides (already in memory)
        overrides = self.user.permission_overrides
        for resource, actions in overrides.items():
            if resource in base_permissions:
                if isinstance(actions, dict):
                    base_permissions[resource].update(actions)
                else:
                    base_permissions[resource] = actions
            else:
                base_permissions[resource] = actions
        
        return base_permissions
    
    async def has_permission(self, permission_type, resource_type, action, resource_id=None):
        """Check if user has specific permission (async)"""
        permissions = await self.get_user_permissions()
        
        # Check system-level permissions first
        system_permissions = permissions.get('system', [])
        if isinstance(system_permissions, list) and 'full_access' in system_permissions:
            return True
        elif isinstance(system_permissions, dict) and system_permissions.get('full_access'):
            return True
        
        # Check resource-specific permissions
        resource_permissions = permissions.get(resource_type, [])
        if isinstance(resource_permissions, list):
            return action in resource_permissions
        elif isinstance(resource_permissions, dict):
            # Check specific resource ID permissions
            if resource_id and resource_id in resource_permissions:
                return action in resource_permissions[resource_id]
            # Check default permissions for resource type
            return action in resource_permissions.get('default', [])
        
        return False
    
    async def get_field_permissions(self, pipeline_id, field_name):
        """Get field-level permissions for specific pipeline field (async)"""
        permissions = await self.get_user_permissions()
        
        # Check pipeline-specific field permissions
        pipeline_perms = permissions.get('pipelines', {}).get(pipeline_id, {})
        field_perms = pipeline_perms.get('fields', {}).get(field_name, {})
        
        return {
            'read': field_perms.get('read', True),
            'write': field_perms.get('write', False),
            'delete': field_perms.get('delete', False)
        }
    
    
    
    async def can_access_user(self, target_user):
        """Check if current user can access another user's data"""
        # System admins can access anyone
        if await self.has_permission('action', 'system', 'full_access'):
            return True
        
        # Users can access themselves
        if self.user.id == target_user.id:
            return True
        
        # Check if user can manage other users
        if await self.has_permission('action', 'users', 'read'):
            return True
        
        return False
    
    async def can_modify_user(self, target_user):
        """Check if current user can modify another user"""
        # System admins can modify anyone
        if await self.has_permission('action', 'system', 'full_access'):
            return True
        
        # Users can modify themselves (limited)
        if self.user.id == target_user.id:
            return await self.has_permission('action', 'users', 'update_self')
        
        # Check if user can manage other users
        if await self.has_permission('action', 'users', 'update'):
            return True
        
        return False
    
    async def get_accessible_pipelines(self):
        """Get list of pipelines user can access"""
        permissions = await self.get_user_permissions()
        
        # If user has full system access, return all
        system_permissions = permissions.get('system', [])
        if isinstance(system_permissions, list) and 'full_access' in system_permissions:
            return 'all'
        elif isinstance(system_permissions, dict) and system_permissions.get('full_access'):
            return 'all'
        
        # Get specific pipeline permissions
        pipeline_perms = permissions.get('pipelines', [])
        if isinstance(pipeline_perms, list):
            # User has same permissions for all pipelines
            return 'all' if 'read' in pipeline_perms else []
        elif isinstance(pipeline_perms, dict):
            # Return specific pipeline IDs user can access
            accessible = []
            for pipeline_id, actions in pipeline_perms.items():
                if pipeline_id != 'default' and 'read' in actions:
                    accessible.append(pipeline_id)
            
            # If user has default read access, they can see all
            if 'read' in pipeline_perms.get('default', []):
                return 'all'
            
            return accessible
        
        return []


class PermissionDecorator:
    """Decorator for checking permissions on async views"""
    
    def __init__(self, permission_type, resource_type, action, resource_id_param=None):
        self.permission_type = permission_type
        self.resource_type = resource_type
        self.action = action
        self.resource_id_param = resource_id_param
    
    def __call__(self, func):
        async def wrapper(view_instance, request, *args, **kwargs):
            # Get user from request
            user = getattr(request, 'user', None)
            if not user or not user.is_authenticated:
                from rest_framework.response import Response
                return Response({'error': 'Authentication required'}, status=401)
            
            # Get resource ID if specified
            resource_id = None
            if self.resource_id_param:
                resource_id = kwargs.get(self.resource_id_param)
            
            # Check permission
            permission_manager = AsyncPermissionManager(user)
            has_permission = await permission_manager.has_permission(
                self.permission_type,
                self.resource_type,
                self.action,
                resource_id
            )
            
            if not has_permission:
                from rest_framework.response import Response
                return Response({'error': 'Permission denied'}, status=403)
            
            # Call the original function
            return await func(view_instance, request, *args, **kwargs)
        
        return wrapper


def require_permission(permission_type, resource_type, action, resource_id_param=None):
    """Decorator factory for permission checking"""
    return PermissionDecorator(permission_type, resource_type, action, resource_id_param)


class TenantPermissionMixin:
    """Mixin for views that need tenant-aware permission checking"""
    
    async def check_permission(self, permission_type, resource_type, action, resource_id=None):
        """Check permission for current user"""
        user = getattr(self.request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        
        permission_manager = AsyncPermissionManager(user)
        return await permission_manager.has_permission(
            permission_type, resource_type, action, resource_id
        )
    
    async def get_user_permissions(self):
        """Get all permissions for current user"""
        user = getattr(self.request, 'user', None)
        if not user or not user.is_authenticated:
            return {}
        
        permission_manager = AsyncPermissionManager(user)
        return await permission_manager.get_user_permissions()
    
    async def filter_by_permissions(self, queryset, permission_type, resource_type, action):
        """Filter queryset based on user permissions"""
        user = getattr(self.request, 'user', None)
        if not user or not user.is_authenticated:
            return queryset.none()
        
        permission_manager = AsyncPermissionManager(user)
        
        # Check if user has full access
        if await permission_manager.has_permission(permission_type, 'system', 'full_access'):
            return queryset
        
        # Check if user has general permission for resource type
        if await permission_manager.has_permission(permission_type, resource_type, action):
            return queryset
        
        # No access
        return queryset.none()


class SyncPermissionManager:
    """Synchronous wrapper for AsyncPermissionManager for use in Django ViewSets"""
    
    def __init__(self, user):
        self.user = user
        self.async_manager = AsyncPermissionManager(user)
    
    def get_user_permissions(self):
        """Get all permissions for a user (sync wrapper)"""
        return async_to_sync(self.async_manager.get_user_permissions)()
    
    def has_permission(self, permission_type, resource_type, action, resource_id=None):
        """Check if user has specific permission (sync wrapper)"""
        return async_to_sync(self.async_manager.has_permission)(
            permission_type, resource_type, action, resource_id
        )
    
    def get_field_permissions(self, pipeline_id, field_name):
        """Get field-level permissions for specific pipeline field (sync wrapper)"""
        return async_to_sync(self.async_manager.get_field_permissions)(pipeline_id, field_name)
    
    def can_access_user(self, target_user):
        """Check if current user can access another user's data (sync wrapper)"""
        return async_to_sync(self.async_manager.can_access_user)(target_user)
    
    def can_modify_user(self, target_user):
        """Check if current user can modify another user (sync wrapper)"""
        return async_to_sync(self.async_manager.can_modify_user)(target_user)
    
    def get_accessible_pipelines(self):
        """Get list of pipelines user can access (sync wrapper)"""
        return async_to_sync(self.async_manager.get_accessible_pipelines)()
    
    def check_permission(self, permission_type, resource_type, action, resource_id=None):
        """Check permission for current user (sync wrapper)"""
        return async_to_sync(self.async_manager.has_permission)(
            permission_type, resource_type, action, resource_id
        )
    
    def filter_by_permissions(self, queryset, permission_type, resource_type, action):
        """Filter queryset based on user permissions (sync wrapper)"""
        # Check if user has full access
        if self.has_permission(permission_type, 'system', 'full_access'):
            return queryset
        
        # Check if user has general permission for resource type
        if self.has_permission(permission_type, resource_type, action):
            return queryset
        
        # No access
        return queryset.none()


class PermissionManager:
    """Factory class that returns the appropriate permission manager"""
    
    @staticmethod
    def get_manager(user, async_context=False):
        """Get permission manager - async or sync based on context"""
        if async_context:
            return AsyncPermissionManager(user)
        else:
            return SyncPermissionManager(user)