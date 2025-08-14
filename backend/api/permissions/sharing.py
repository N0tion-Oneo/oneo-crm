"""
Sharing-specific permission classes
"""
from rest_framework import permissions
from authentication.permissions import SyncPermissionManager as PermissionManager


class SharedRecordPermission(permissions.BasePermission):
    """Permissions for shared record management and history"""
    
    def has_permission(self, request, view):
        """Check if user has general sharing access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = PermissionManager(request.user)
        
        # Check sharing permissions
        if view.action in ['list', 'retrieve', 'access_logs', 'analytics']:
            # Viewing shares requires create_shared_views permission
            return permission_manager.has_permission('action', 'sharing', 'create_shared_views')
        elif view.action == 'revoke':
            # Revoking shares uses the new revoke permission
            return permission_manager.has_permission('action', 'sharing', 'revoke_shared_views_forms')
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions for shared records"""
        permission_manager = PermissionManager(request.user)
        
        # Extract pipeline_id from the shared record object
        if hasattr(obj, 'record') and hasattr(obj.record, 'pipeline'):
            pipeline_id = str(obj.record.pipeline.id)
        elif hasattr(obj, 'pipeline_id'):
            pipeline_id = str(obj.pipeline_id)
        else:
            return False
        
        if view.action in ['retrieve', 'access_logs']:
            # Viewing shared record details requires sharing view permission + pipeline access
            has_sharing_perm = permission_manager.has_permission('action', 'sharing', 'create_shared_views')
            has_pipeline_access = permission_manager.has_permission('action', 'records', 'read', pipeline_id)
            return has_sharing_perm and has_pipeline_access
        elif view.action == 'revoke':
            # Revoking shares requires revoke permission + pipeline access
            has_revoke_perm = permission_manager.has_permission('action', 'sharing', 'revoke_shared_views_forms')
            has_pipeline_access = permission_manager.has_permission('action', 'records', 'read', pipeline_id)
            return has_revoke_perm and has_pipeline_access
        elif view.action == 'analytics':
            # Analytics requires sharing view permission + pipeline access
            has_sharing_perm = permission_manager.has_permission('action', 'sharing', 'create_shared_views')
            has_pipeline_access = permission_manager.has_permission('action', 'records', 'read', pipeline_id)
            return has_sharing_perm and has_pipeline_access
        
        return False


class RecordSharingPermission(permissions.BasePermission):
    """Permissions for record-specific sharing history"""
    
    def has_permission(self, request, view):
        """Check if user has access to view sharing history for a specific record"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = PermissionManager(request.user)
        pipeline_id = view.kwargs.get('pipeline_pk')
        
        if not pipeline_id:
            return False
        
        # For viewing record sharing history, user needs record read access
        if view.action in ['list', 'retrieve']:
            return permission_manager.has_permission('action', 'records', 'read', pipeline_id)
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions for record sharing history"""
        permission_manager = PermissionManager(request.user)
        
        # Extract pipeline_id from the shared record object
        if hasattr(obj, 'record') and hasattr(obj.record, 'pipeline'):
            pipeline_id = str(obj.record.pipeline.id)
        else:
            return False
        
        if view.action in ['retrieve']:
            # Viewing specific shared record details requires record read permission
            return permission_manager.has_permission('action', 'records', 'read', pipeline_id)
        
        return False