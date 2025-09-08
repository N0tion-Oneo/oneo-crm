"""
Business rules permission classes
"""
from rest_framework import permissions
from authentication.permissions import SyncPermissionManager


class BusinessRulePermission(permissions.BasePermission):
    """Business rule-specific permissions"""
    
    def has_permission(self, request, view):
        """Check if user has general business rule access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action == 'list':
            return permission_manager.has_permission('action', 'business_rules', 'read')
        elif view.action == 'create':
            return permission_manager.has_permission('action', 'business_rules', 'create')
        elif view.action in ['retrieve', 'test_rule', 'preview', 'audit_log']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['update', 'partial_update']:
            return True  # Object-level check in has_object_permission
        elif view.action == 'destroy':
            return True  # Object-level check in has_object_permission
        elif view.action in ['execute', 'dry_run']:
            return True  # Object-level check in has_object_permission
        elif view.action == 'clone':
            return permission_manager.has_permission('action', 'business_rules', 'create')
        elif view.action in ['activate', 'deactivate']:
            return True  # Object-level check in has_object_permission
        elif view.action == 'bulk_execute':
            # Bulk execution requires both read and execute permissions
            return (permission_manager.has_permission('action', 'business_rules', 'read') and
                   permission_manager.has_permission('action', 'business_rules', 'execute'))
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = SyncPermissionManager(request.user)
        
        # For pipeline-specific business rules, check pipeline permissions too
        pipeline_id = None
        if hasattr(obj, 'pipeline_id'):
            pipeline_id = str(obj.pipeline_id)
        elif hasattr(obj, 'pipeline'):
            pipeline_id = str(obj.pipeline.id)
        
        if view.action in ['retrieve', 'test_rule', 'preview', 'audit_log']:
            # Read permission on business rule
            has_rule_perm = permission_manager.has_permission('action', 'business_rules', 'read', str(obj.id))
            # If rule is pipeline-specific, also check pipeline read permission
            if pipeline_id:
                has_pipeline_perm = permission_manager.has_permission('action', 'pipelines', 'read', pipeline_id)
                return has_rule_perm and has_pipeline_perm
            return has_rule_perm
            
        elif view.action in ['update', 'partial_update']:
            has_rule_perm = permission_manager.has_permission('action', 'business_rules', 'update', str(obj.id))
            if pipeline_id:
                has_pipeline_perm = permission_manager.has_permission('action', 'pipelines', 'update', pipeline_id)
                return has_rule_perm and has_pipeline_perm
            return has_rule_perm
            
        elif view.action == 'destroy':
            has_rule_perm = permission_manager.has_permission('action', 'business_rules', 'delete', str(obj.id))
            if pipeline_id:
                has_pipeline_perm = permission_manager.has_permission('action', 'pipelines', 'delete', pipeline_id)
                return has_rule_perm and has_pipeline_perm
            return has_rule_perm
            
        elif view.action in ['execute', 'dry_run']:
            # Execute permission on business rule
            has_rule_perm = permission_manager.has_permission('action', 'business_rules', 'execute', str(obj.id))
            if pipeline_id:
                # Also need update permission on pipeline to execute rules that modify data
                has_pipeline_perm = permission_manager.has_permission('action', 'pipelines', 'update', pipeline_id)
                return has_rule_perm and has_pipeline_perm
            return has_rule_perm
            
        elif view.action in ['activate', 'deactivate']:
            # Update permission needed to change rule status
            has_rule_perm = permission_manager.has_permission('action', 'business_rules', 'update', str(obj.id))
            if pipeline_id:
                has_pipeline_perm = permission_manager.has_permission('action', 'pipelines', 'update', pipeline_id)
                return has_rule_perm and has_pipeline_perm
            return has_rule_perm
            
        elif view.action == 'clone':
            # Read permission on source rule, create permission for new rules
            return (permission_manager.has_permission('action', 'business_rules', 'read', str(obj.id)) and
                   permission_manager.has_permission('action', 'business_rules', 'create'))
        
        return False


class BusinessRuleExecutionPermission(permissions.BasePermission):
    """Business rule execution permissions"""
    
    def has_permission(self, request, view):
        """Check if user has business rule execution access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        rule_id = view.kwargs.get('rule_pk')
        
        if view.action == 'list':
            if rule_id:
                return permission_manager.has_permission('action', 'business_rules', 'read', rule_id)
            return permission_manager.has_permission('action', 'business_rules', 'read')
        elif view.action == 'create':
            if rule_id:
                return permission_manager.has_permission('action', 'business_rules', 'execute', rule_id)
            return False
        elif view.action in ['retrieve', 'logs', 'status', 'results']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['cancel', 'retry']:
            return True  # Object-level check in has_object_permission
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = SyncPermissionManager(request.user)
        rule_id = str(obj.rule.id) if hasattr(obj, 'rule') else str(obj.business_rule.id)
        
        if view.action in ['retrieve', 'logs', 'status', 'results']:
            return permission_manager.has_permission('action', 'business_rules', 'read', rule_id)
        elif view.action in ['cancel', 'retry']:
            return permission_manager.has_permission('action', 'business_rules', 'execute', rule_id)
        
        return False