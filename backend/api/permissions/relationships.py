"""
Relationship-specific permission classes
"""
from rest_framework import permissions
from authentication.permissions import SyncPermissionManager as PermissionManager


class RelationshipPermission(permissions.BasePermission):
    """Relationship-specific permissions"""
    
    def has_permission(self, request, view):
        """Check if user has relationship access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = PermissionManager(request.user)
        
        if view.action in ['list', 'traverse']:
            return permission_manager.has_permission('action', 'relationships', 'read')
        elif view.action == 'create':
            return permission_manager.has_permission('action', 'relationships', 'create')
        elif view.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return True  # Object-level check in has_object_permission
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = PermissionManager(request.user)
        
        if view.action == 'retrieve':
            return permission_manager.has_permission('action', 'relationships', 'read')
        elif view.action in ['update', 'partial_update']:
            return permission_manager.has_permission('action', 'relationships', 'update')
        elif view.action == 'destroy':
            return permission_manager.has_permission('action', 'relationships', 'delete')
        
        return False