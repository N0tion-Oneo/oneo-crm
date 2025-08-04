"""
Form-specific permission classes
"""
from rest_framework import permissions
from authentication.permissions import SyncPermissionManager


class FormPermission(permissions.BasePermission):
    """Form-specific permissions"""
    
    def has_permission(self, request, view):
        """Check if user has general form access"""
        if not request.user.is_authenticated:
            return False
        
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