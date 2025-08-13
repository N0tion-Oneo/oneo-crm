"""
Duplicate detection permission classes
"""
from rest_framework import permissions
from authentication.permissions import SyncPermissionManager


class DuplicatePermission(permissions.BasePermission):
    """Duplicate-specific permissions"""
    
    def has_permission(self, request, view):
        """Check if user has general duplicate access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action == 'list':
            return permission_manager.has_permission('action', 'duplicates', 'read')
        elif view.action == 'create':
            return permission_manager.has_permission('action', 'duplicates', 'create')
        elif view.action in ['retrieve', 'detect_duplicates', 'test_rule', 'statistics', 'test_extraction', 'run_test']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['update', 'partial_update']:
            return True  # Object-level check in has_object_permission
        elif view.action == 'destroy':
            return True  # Object-level check in has_object_permission
        elif view.action in ['bulk_resolve', 'resolve_matches']:
            return permission_manager.has_permission('action', 'duplicates', 'resolve')
        elif view.action in ['builder_config', 'validate_logic', 'clone']:
            return permission_manager.has_permission('action', 'duplicates', 'create')
        elif view.action == 'live_test':
            # Live testing doesn't store data, allow for users with basic duplicate read access
            return permission_manager.has_permission('action', 'duplicates', 'read')
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action in ['retrieve', 'detect_duplicates', 'test_rule', 'statistics', 'test_extraction', 'run_test']:
            return permission_manager.has_permission('action', 'duplicates', 'read', str(obj.id))
        elif view.action in ['update', 'partial_update']:
            return permission_manager.has_permission('action', 'duplicates', 'update', str(obj.id))
        elif view.action == 'destroy':
            return permission_manager.has_permission('action', 'duplicates', 'delete', str(obj.id))
        elif view.action in ['bulk_resolve', 'resolve_matches']:
            return permission_manager.has_permission('action', 'duplicates', 'resolve', str(obj.id))
        elif view.action in ['clone']:
            return permission_manager.has_permission('action', 'duplicates', 'create', str(obj.id))
        
        return False