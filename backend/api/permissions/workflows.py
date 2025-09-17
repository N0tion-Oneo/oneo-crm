"""
Workflow-specific permission classes
"""
from rest_framework import permissions
from authentication.permissions import SyncPermissionManager


class WorkflowPermission(permissions.BasePermission):
    """Workflow-specific permissions using authentication registry"""
    
    def has_permission(self, request, view):
        """Check if user has general workflow access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action == 'list':
            return permission_manager.has_permission('action', 'workflows', 'read')
        elif view.action == 'create':
            return permission_manager.has_permission('action', 'workflows', 'create')
        elif view.action in ['retrieve', 'analytics', 'export', 'clone', 'triggers']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['update', 'partial_update', 'update_trigger', 'delete_trigger', 'test_node']:
            return True  # Object-level check in has_object_permission
        elif view.action == 'destroy':
            return True  # Object-level check in has_object_permission
        elif view.action in ['execute', 'test_run']:
            return True  # Object-level check in has_object_permission
        elif view.action == 'node_schemas':
            # Allow authenticated users to view node schemas
            return True

        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = SyncPermissionManager(request.user)

        if view.action in ['retrieve', 'analytics', 'export', 'clone', 'triggers']:
            return permission_manager.has_permission('action', 'workflows', 'read', str(obj.id))
        elif view.action in ['update', 'partial_update', 'update_trigger', 'delete_trigger', 'test_node']:
            return permission_manager.has_permission('action', 'workflows', 'update', str(obj.id))
        elif view.action == 'destroy':
            return permission_manager.has_permission('action', 'workflows', 'delete', str(obj.id))
        elif view.action in ['execute', 'test_run']:
            return permission_manager.has_permission('action', 'workflows', 'execute', str(obj.id))

        return False


class WorkflowExecutionPermission(permissions.BasePermission):
    """Workflow execution permissions"""
    
    def has_permission(self, request, view):
        """Check if user has workflow execution access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        workflow_id = view.kwargs.get('workflow_pk')
        
        if view.action == 'list':
            if workflow_id:
                return permission_manager.has_permission('action', 'workflows', 'read', workflow_id)
            return permission_manager.has_permission('action', 'workflows', 'read')
        elif view.action == 'create':
            if workflow_id:
                return permission_manager.has_permission('action', 'workflows', 'execute', workflow_id)
            return False
        elif view.action in ['retrieve', 'logs', 'status']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['cancel', 'pause', 'resume']:
            return True  # Object-level check in has_object_permission
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = SyncPermissionManager(request.user)
        workflow_id = str(obj.workflow.id)
        
        if view.action in ['retrieve', 'logs', 'status']:
            return permission_manager.has_permission('action', 'workflows', 'read', workflow_id)
        elif view.action in ['cancel', 'pause', 'resume']:
            return permission_manager.has_permission('action', 'workflows', 'execute', workflow_id)
        
        return False


class WorkflowApprovalPermission(permissions.BasePermission):
    """Workflow approval permissions"""
    
    def has_permission(self, request, view):
        """Check if user has workflow approval access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action == 'list':
            return permission_manager.has_permission('action', 'workflows', 'read')
        elif view.action in ['retrieve', 'approve', 'reject']:
            return True  # Object-level check in has_object_permission
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = SyncPermissionManager(request.user)
        
        # Check if user is assigned to this approval or has workflow admin rights
        if obj.assigned_to == request.user:
            return True
        
        workflow_id = str(obj.execution.workflow.id)
        
        if view.action == 'retrieve':
            return permission_manager.has_permission('action', 'workflows', 'read', workflow_id)
        elif view.action in ['approve', 'reject']:
            # Either assigned user or workflow admin can approve/reject
            return permission_manager.has_permission('action', 'workflows', 'update', workflow_id)
        
        return False


class WorkflowTemplatePermission(permissions.BasePermission):
    """Workflow template permissions"""
    
    def has_permission(self, request, view):
        """Check if user has workflow template access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action == 'list':
            return permission_manager.has_permission('action', 'workflows', 'read')
        elif view.action == 'create':
            return permission_manager.has_permission('action', 'workflows', 'create')
        elif view.action in ['retrieve', 'instantiate']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['update', 'partial_update']:
            return True  # Object-level check in has_object_permission
        elif view.action == 'destroy':
            return True  # Object-level check in has_object_permission
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action in ['retrieve', 'instantiate']:
            return permission_manager.has_permission('action', 'workflows', 'read')
        elif view.action in ['update', 'partial_update']:
            # Only creator or admin can edit templates
            if obj.created_by == request.user:
                return True
            return permission_manager.has_permission('action', 'workflows', 'update')
        elif view.action == 'destroy':
            # Only creator or admin can delete templates
            if obj.created_by == request.user:
                return True
            return permission_manager.has_permission('action', 'workflows', 'delete')
        
        return False