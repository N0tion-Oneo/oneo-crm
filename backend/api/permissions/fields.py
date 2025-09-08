"""
Field-specific permission classes
"""
from rest_framework import permissions
from authentication.permissions import SyncPermissionManager


class FieldPermission(permissions.BasePermission):
    """Field-specific permissions separate from pipeline permissions"""
    
    def has_permission(self, request, view):
        """Check if user has general field access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        pipeline_id = view.kwargs.get('pipeline_pk')
        
        # Debug logging
        print(f"🔍 Field permission check: action={view.action}, pipeline_id={pipeline_id}")
        
        if view.action == 'list':
            # List fields requires field read permission
            if pipeline_id:
                return permission_manager.has_permission('action', 'fields', 'read', pipeline_id)
            return permission_manager.has_permission('action', 'fields', 'read')
            
        elif view.action == 'create':
            # Create field requires field manage permission
            if pipeline_id:
                return permission_manager.has_permission('action', 'fields', 'manage', pipeline_id)
            return permission_manager.has_permission('action', 'fields', 'manage')
            
        elif view.action in ['retrieve', 'metadata', 'usage']:
            return True  # Object-level check in has_object_permission
            
        elif view.action in ['update', 'partial_update']:
            return True  # Object-level check in has_object_permission
            
        elif view.action == 'destroy':
            return True  # Object-level check in has_object_permission
            
        elif view.action in ['recover', 'restore']:
            # Field recovery requires delete permission
            if pipeline_id:
                return permission_manager.has_permission('action', 'fields', 'delete', pipeline_id)
            return permission_manager.has_permission('action', 'fields', 'delete')
            
        elif view.action in ['migrate', 'validate_migration', 'migrate_schema']:
            # Field migration requires delete permission
            if pipeline_id:
                return permission_manager.has_permission('action', 'fields', 'delete', pipeline_id)
            return permission_manager.has_permission('action', 'fields', 'delete')
            
        elif view.action == 'reorder':
            # Field reordering requires manage permission
            if pipeline_id:
                return permission_manager.has_permission('action', 'fields', 'manage', pipeline_id)
            return permission_manager.has_permission('action', 'fields', 'manage')
            
        elif view.action == 'bulk_update':
            # Bulk update requires manage permission
            if pipeline_id:
                return permission_manager.has_permission('action', 'fields', 'manage', pipeline_id)
            return permission_manager.has_permission('action', 'fields', 'manage')
            
        elif view.action == 'clone':
            # Cloning requires manage permission
            return permission_manager.has_permission('action', 'fields', 'manage')
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = SyncPermissionManager(request.user)
        
        # Get pipeline ID from field object
        pipeline_id = None
        if hasattr(obj, 'pipeline_id'):
            pipeline_id = str(obj.pipeline_id)
        elif hasattr(obj, 'pipeline'):
            pipeline_id = str(obj.pipeline.id)
        
        if view.action in ['retrieve', 'metadata', 'usage']:
            # Read permission on field
            if pipeline_id:
                return permission_manager.has_permission('action', 'fields', 'read', pipeline_id)
            return permission_manager.has_permission('action', 'fields', 'read')
            
        elif view.action in ['update', 'partial_update']:
            # Update permission on field
            if pipeline_id:
                return permission_manager.has_permission('action', 'fields', 'manage', pipeline_id)
            return permission_manager.has_permission('action', 'fields', 'manage')
            
        elif view.action == 'destroy':
            # Delete permission on field
            if pipeline_id:
                return permission_manager.has_permission('action', 'fields', 'delete', pipeline_id)
            return permission_manager.has_permission('action', 'fields', 'delete')
            
        elif view.action in ['recover', 'restore']:
            # Recover permission on field
            if pipeline_id:
                return permission_manager.has_permission('action', 'fields', 'delete', pipeline_id)
            return permission_manager.has_permission('action', 'fields', 'delete')
            
        elif view.action in ['migrate', 'validate_migration', 'migrate_schema']:
            # Migrate permission on field
            if pipeline_id:
                return permission_manager.has_permission('action', 'fields', 'delete', pipeline_id)
            return permission_manager.has_permission('action', 'fields', 'delete')
            
        elif view.action == 'clone':
            # Read permission on source field, manage permission for new fields
            read_perm = permission_manager.has_permission('action', 'fields', 'read', pipeline_id) if pipeline_id else permission_manager.has_permission('action', 'fields', 'read')
            manage_perm = permission_manager.has_permission('action', 'fields', 'manage')
            return read_perm and manage_perm
        
        return False


class FieldGroupPermission(permissions.BasePermission):
    """Field group management permissions"""
    
    def has_permission(self, request, view):
        """Check if user has field group management access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        pipeline_id = view.kwargs.get('pipeline_pk')
        
        if view.action == 'list':
            # List field groups requires field read permission
            if pipeline_id:
                return permission_manager.has_permission('action', 'fields', 'read', pipeline_id)
            return permission_manager.has_permission('action', 'fields', 'read')
            
        elif view.action == 'create':
            # Create field group requires field manage permission (organizing fields)
            if pipeline_id:
                return permission_manager.has_permission('action', 'fields', 'manage', pipeline_id)
            return permission_manager.has_permission('action', 'fields', 'manage')
            
        elif view.action in ['retrieve', 'fields']:
            return True  # Object-level check in has_object_permission
            
        elif view.action in ['update', 'partial_update', 'assign_fields', 'ungroup_fields', 'reorder_groups']:
            return True  # Object-level check in has_object_permission
            
        elif view.action == 'destroy':
            return True  # Object-level check in has_object_permission
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = SyncPermissionManager(request.user)
        
        # Get pipeline ID from field group object
        pipeline_id = None
        if hasattr(obj, 'pipeline_id'):
            pipeline_id = str(obj.pipeline_id)
        elif hasattr(obj, 'pipeline'):
            pipeline_id = str(obj.pipeline.id)
        
        if view.action in ['retrieve', 'fields']:
            # Read permission on fields
            if pipeline_id:
                return permission_manager.has_permission('action', 'fields', 'read', pipeline_id)
            return permission_manager.has_permission('action', 'fields', 'read')
            
        elif view.action in ['update', 'partial_update', 'assign_fields', 'ungroup_fields', 'reorder_groups']:
            # Manage permission on fields (organizing)
            if pipeline_id:
                return permission_manager.has_permission('action', 'fields', 'manage', pipeline_id)
            return permission_manager.has_permission('action', 'fields', 'manage')
            
        elif view.action == 'destroy':
            # Manage permission on fields (ungrouping)
            if pipeline_id:
                return permission_manager.has_permission('action', 'fields', 'manage', pipeline_id)
            return permission_manager.has_permission('action', 'fields', 'manage')
        
        return False