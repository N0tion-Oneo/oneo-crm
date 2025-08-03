"""
API-specific permission classes
"""
from rest_framework import permissions
from authentication.permissions import AsyncPermissionManager as PermissionManager


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


class AdminOnlyPermission(permissions.BasePermission):
    """Admin-only access permission"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type.name == 'Admin'


class TenantMemberPermission(permissions.BasePermission):
    """Tenant member permission - basic authenticated access"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated


class ReadOnlyPermission(permissions.BasePermission):
    """Read-only access permission"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        return view.action in ['list', 'retrieve']


class FormPermission(permissions.BasePermission):
    """Form-specific permissions"""
    
    def has_permission(self, request, view):
        """Check if user has general form access"""
        if not request.user.is_authenticated:
            return False
        
        from authentication.permissions import SyncPermissionManager
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action == 'list':
            return permission_manager.has_permission('action', 'forms', 'read')
        elif view.action == 'create':
            return permission_manager.has_permission('action', 'forms', 'create')
        elif view.action in ['retrieve', 'validate_form', 'check_duplicates', 'analytics']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['update', 'partial_update']:
            return True  # Object-level check in has_object_permission
        elif view.action == 'destroy':
            return True  # Object-level check in has_object_permission
        elif view.action in ['submit_form', 'build_form']:
            return permission_manager.has_permission('action', 'forms', 'submit')
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        from authentication.permissions import SyncPermissionManager
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action in ['retrieve', 'validate_form', 'check_duplicates', 'analytics']:
            return permission_manager.has_permission('action', 'forms', 'read', str(obj.id))
        elif view.action in ['update', 'partial_update', 'build_form']:
            return permission_manager.has_permission('action', 'forms', 'update', str(obj.id))
        elif view.action == 'destroy':
            return permission_manager.has_permission('action', 'forms', 'delete', str(obj.id))
        elif view.action == 'submit_form':
            return permission_manager.has_permission('action', 'forms', 'submit', str(obj.id))
        
        return False


class ValidationRulePermission(permissions.BasePermission):
    """Validation rule-specific permissions"""
    
    def has_permission(self, request, view):
        """Check if user has validation rule access"""
        if not request.user.is_authenticated:
            return False
        
        from authentication.permissions import SyncPermissionManager
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action == 'list':
            return permission_manager.has_permission('action', 'validation_rules', 'read')
        elif view.action == 'create':
            return permission_manager.has_permission('action', 'validation_rules', 'create')
        elif view.action in ['retrieve', 'rule_types', 'pattern_library', 'test_rule', 'test_rule_static']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['update', 'partial_update']:
            return True  # Object-level check in has_object_permission
        elif view.action == 'destroy':
            return True  # Object-level check in has_object_permission
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        from authentication.permissions import SyncPermissionManager
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action in ['retrieve', 'rule_types', 'pattern_library', 'test_rule', 'test_rule_static']:
            # For metadata endpoints, just check general read permission
            if view.action in ['rule_types', 'pattern_library', 'test_rule_static']:
                return permission_manager.has_permission('action', 'validation_rules', 'read')
            return permission_manager.has_permission('action', 'validation_rules', 'read', str(obj.id))
        elif view.action in ['update', 'partial_update']:
            return permission_manager.has_permission('action', 'validation_rules', 'update', str(obj.id))
        elif view.action == 'destroy':
            return permission_manager.has_permission('action', 'validation_rules', 'delete', str(obj.id))
        
        return False


class DuplicatePermission(permissions.BasePermission):
    """Duplicate-specific permissions"""
    
    def has_permission(self, request, view):
        """Check if user has general duplicate access"""
        if not request.user.is_authenticated:
            return False
        
        from authentication.permissions import SyncPermissionManager
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action == 'list':
            return permission_manager.has_permission('action', 'duplicates', 'read')
        elif view.action == 'create':
            return permission_manager.has_permission('action', 'duplicates', 'create')
        elif view.action in ['retrieve', 'detect_duplicates', 'compare_records', 'statistics']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['update', 'partial_update']:
            return True  # Object-level check in has_object_permission
        elif view.action == 'destroy':
            return True  # Object-level check in has_object_permission
        elif view.action in ['resolve_matches', 'bulk_resolution']:
            return permission_manager.has_permission('action', 'duplicates', 'resolve')
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        from authentication.permissions import SyncPermissionManager
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action in ['retrieve', 'detect_duplicates', 'compare_records', 'statistics']:
            return permission_manager.has_permission('action', 'duplicates', 'read', str(obj.id))
        elif view.action in ['update', 'partial_update']:
            return permission_manager.has_permission('action', 'duplicates', 'update', str(obj.id))
        elif view.action == 'destroy':
            return permission_manager.has_permission('action', 'duplicates', 'delete', str(obj.id))
        elif view.action in ['resolve_matches', 'bulk_resolution']:
            return permission_manager.has_permission('action', 'duplicates', 'resolve', str(obj.id))
        
        return False