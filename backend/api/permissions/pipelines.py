"""
Pipeline-specific permission classes
"""
from rest_framework import permissions
from authentication.permissions import SyncPermissionManager as PermissionManager


class PipelinePermission(permissions.BasePermission):
    """Pipeline-specific permissions"""
    
    def has_permission(self, request, view):
        """Check if user has general pipeline access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = PermissionManager(request.user)
        
        if view.action == 'list':
            return permission_manager.has_permission('action', 'pipelines', 'read')
        elif view.action == 'create':
            return permission_manager.has_permission('action', 'pipelines', 'create')
        elif view.action in ['retrieve', 'analytics', 'export']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['update', 'partial_update']:
            return True  # Object-level check in has_object_permission
        elif view.action == 'destroy':
            return True  # Object-level check in has_object_permission
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = PermissionManager(request.user)
        
        if view.action in ['retrieve', 'analytics', 'export']:
            return permission_manager.has_permission('action', 'pipelines', 'read', str(obj.id))
        elif view.action in ['update', 'partial_update']:
            return permission_manager.has_permission('action', 'pipelines', 'update', str(obj.id))
        elif view.action == 'destroy':
            return permission_manager.has_permission('action', 'pipelines', 'delete', str(obj.id))
        
        return False


class RecordPermission(permissions.BasePermission):
    """Record-specific permissions"""
    
    def has_permission(self, request, view):
        """Check if user has general record access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = PermissionManager(request.user)
        pipeline_id = view.kwargs.get('pipeline_pk') or request.data.get('pipeline_id')
        
        if view.action == 'list':
            if pipeline_id:
                return permission_manager.has_permission('action', 'records', 'read', pipeline_id)
            return permission_manager.has_permission('action', 'records', 'read')
        elif view.action == 'create':
            if pipeline_id:
                return permission_manager.has_permission('action', 'records', 'create', pipeline_id)
            return False
        elif view.action in ['retrieve', 'relationships', 'history']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['update', 'partial_update']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['destroy', 'soft_delete', 'restore']:
            return True  # Object-level check in has_object_permission
        elif view.action == 'deleted':
            # List deleted records - requires read permission for the pipeline
            if pipeline_id:
                return permission_manager.has_permission('action', 'records', 'read', pipeline_id)
            return permission_manager.has_permission('action', 'records', 'read')
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = PermissionManager(request.user)
        pipeline_id = str(obj.pipeline_id)
        
        if view.action in ['retrieve', 'relationships', 'history']:
            return permission_manager.has_permission('action', 'records', 'read', pipeline_id)
        elif view.action in ['update', 'partial_update']:
            return permission_manager.has_permission('action', 'records', 'update', pipeline_id)
        elif view.action in ['destroy', 'soft_delete']:
            return permission_manager.has_permission('action', 'records', 'delete', pipeline_id)
        elif view.action == 'restore':
            # Restore requires delete permission (ability to manage deleted records)
            return permission_manager.has_permission('action', 'records', 'delete', pipeline_id)
        
        return False