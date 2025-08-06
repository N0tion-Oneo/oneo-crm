"""
AI-specific permission classes
"""
from rest_framework import permissions
from authentication.permissions import SyncPermissionManager


class AIPermission(permissions.BasePermission):
    """AI feature permissions"""
    
    def has_permission(self, request, view):
        """Check if user has AI feature access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action == 'list':
            return permission_manager.has_permission('action', 'ai_features', 'read')
        elif view.action == 'create':
            return permission_manager.has_permission('action', 'ai_features', 'create')
        elif view.action in ['retrieve', 'capabilities', 'usage_stats']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['update', 'partial_update']:
            return True  # Object-level check in has_object_permission
        elif view.action == 'destroy':
            return True  # Object-level check in has_object_permission
        elif view.action in ['configure', 'test', 'analyze']:
            return permission_manager.has_permission('action', 'ai_features', 'create')
        elif view.action == 'tenant_config':
            return permission_manager.has_permission('action', 'ai_features', 'read')
        elif view.action == 'update_tenant_config':
            return permission_manager.has_permission('action', 'ai_features', 'configure')
        elif view.action == 'delete_api_key':
            return permission_manager.has_permission('action', 'ai_features', 'configure')
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action in ['retrieve', 'capabilities', 'usage_stats']:
            return permission_manager.has_permission('action', 'ai_features', 'read', str(obj.id))
        elif view.action in ['update', 'partial_update']:
            return permission_manager.has_permission('action', 'ai_features', 'update', str(obj.id))
        elif view.action == 'destroy':
            return permission_manager.has_permission('action', 'ai_features', 'delete', str(obj.id))
        elif view.action in ['configure', 'test']:
            return permission_manager.has_permission('action', 'ai_features', 'configure', str(obj.id))
        
        return False


class ProcessorPermission(permissions.BasePermission):
    """AI processor permissions"""
    
    def has_permission(self, request, view):
        """Check if user has processor access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action == 'list':
            return permission_manager.has_permission('action', 'ai_features', 'read')
        elif view.action == 'create':
            return permission_manager.has_permission('action', 'ai_features', 'create')
        elif view.action in ['retrieve', 'process', 'batch_process']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['update', 'partial_update']:
            return True  # Object-level check in has_object_permission
        elif view.action == 'destroy':
            return True  # Object-level check in has_object_permission
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action in ['retrieve', 'process', 'batch_process']:
            return permission_manager.has_permission('action', 'ai_features', 'read', str(obj.id))
        elif view.action in ['update', 'partial_update']:
            return permission_manager.has_permission('action', 'ai_features', 'update', str(obj.id))
        elif view.action == 'destroy':
            return permission_manager.has_permission('action', 'ai_features', 'delete', str(obj.id))
        
        return False


class AIModelPermission(permissions.BasePermission):
    """AI model configuration permissions"""
    
    def has_permission(self, request, view):
        """Check if user has model configuration access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action == 'list':
            return permission_manager.has_permission('action', 'ai_features', 'read')
        elif view.action == 'create':
            return permission_manager.has_permission('action', 'ai_features', 'configure')
        elif view.action in ['retrieve', 'models', 'pricing']:
            return permission_manager.has_permission('action', 'ai_features', 'read')
        elif view.action in ['update', 'partial_update']:
            return permission_manager.has_permission('action', 'ai_features', 'configure')
        elif view.action == 'destroy':
            return permission_manager.has_permission('action', 'ai_features', 'configure')
        elif view.action in ['test_model', 'validate_config']:
            return permission_manager.has_permission('action', 'ai_features', 'configure')
        
        return False


class AIPromptTemplatePermission(permissions.BasePermission):
    """AI prompt template permissions"""
    
    def has_permission(self, request, view):
        """Check if user has prompt template access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action == 'list':
            return permission_manager.has_permission('action', 'ai_features', 'read')
        elif view.action == 'create':
            return permission_manager.has_permission('action', 'ai_features', 'create')
        elif view.action in ['retrieve', 'preview', 'variables']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['update', 'partial_update']:
            return True  # Object-level check in has_object_permission
        elif view.action == 'destroy':
            return True  # Object-level check in has_object_permission
        elif view.action in ['test_prompt', 'clone']:
            return True  # Object-level check in has_object_permission
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action in ['retrieve', 'preview', 'variables']:
            return permission_manager.has_permission('action', 'ai_features', 'read', str(obj.id))
        elif view.action in ['update', 'partial_update']:
            # Allow editing own templates or with update permission
            if obj.created_by == request.user:
                return True
            return permission_manager.has_permission('action', 'ai_features', 'update', str(obj.id))
        elif view.action == 'destroy':
            # Allow deleting own templates or with delete permission
            if obj.created_by == request.user:
                return True
            return permission_manager.has_permission('action', 'ai_features', 'delete', str(obj.id))
        elif view.action in ['test_prompt', 'clone']:
            return permission_manager.has_permission('action', 'ai_features', 'read', str(obj.id))
        
        return False