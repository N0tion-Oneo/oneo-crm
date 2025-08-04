"""
Monitoring and analytics permission classes
"""
from rest_framework import permissions
from authentication.permissions import SyncPermissionManager


class MonitoringPermission(permissions.BasePermission):
    """System monitoring permissions"""
    
    def has_permission(self, request, view):
        """Check if user has monitoring access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action == 'list':
            return permission_manager.has_permission('action', 'monitoring', 'read')
        elif view.action in ['retrieve', 'health_check', 'system_status']:
            return permission_manager.has_permission('action', 'monitoring', 'read')
        elif view.action in ['update', 'partial_update']:
            return permission_manager.has_permission('action', 'monitoring', 'update')
        elif view.action in ['restart_service', 'clear_cache']:
            # System-level operations require admin access
            return request.user.user_type.name == 'Admin'
        
        return False


class AnalyticsPermission(permissions.BasePermission):
    """Analytics and reporting permissions"""
    
    def has_permission(self, request, view):
        """Check if user has analytics access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action == 'list':
            return permission_manager.has_permission('action', 'reports', 'read')
        elif view.action == 'create':
            return permission_manager.has_permission('action', 'reports', 'create')
        elif view.action in ['retrieve', 'export', 'dashboard']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['update', 'partial_update']:
            return True  # Object-level check in has_object_permission
        elif view.action == 'destroy':
            return True  # Object-level check in has_object_permission
        elif view.action in ['schedule', 'generate']:
            return True  # Object-level check in has_object_permission
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action in ['retrieve', 'export', 'dashboard']:
            return permission_manager.has_permission('action', 'reports', 'read', str(obj.id))
        elif view.action in ['update', 'partial_update']:
            return permission_manager.has_permission('action', 'reports', 'update', str(obj.id))
        elif view.action == 'destroy':
            return permission_manager.has_permission('action', 'reports', 'delete', str(obj.id))
        elif view.action in ['schedule', 'generate']:
            return permission_manager.has_permission('action', 'reports', 'create', str(obj.id))
        
        return False


class AlertPermission(permissions.BasePermission):
    """Alert management permissions"""
    
    def has_permission(self, request, view):
        """Check if user has alert access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action == 'list':
            return permission_manager.has_permission('action', 'monitoring', 'read')
        elif view.action == 'create':
            return permission_manager.has_permission('action', 'monitoring', 'update')
        elif view.action in ['retrieve', 'history']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['update', 'partial_update']:
            return True  # Object-level check in has_object_permission
        elif view.action == 'destroy':
            return True  # Object-level check in has_object_permission
        elif view.action in ['acknowledge', 'resolve']:
            return True  # Object-level check in has_object_permission
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action in ['retrieve', 'history']:
            return permission_manager.has_permission('action', 'monitoring', 'read')
        elif view.action in ['update', 'partial_update']:
            return permission_manager.has_permission('action', 'monitoring', 'update')
        elif view.action == 'destroy':
            return permission_manager.has_permission('action', 'monitoring', 'update')
        elif view.action in ['acknowledge', 'resolve']:
            return permission_manager.has_permission('action', 'monitoring', 'update')
        
        return False


class SystemMetricsPermission(permissions.BasePermission):
    """System metrics and performance permissions"""
    
    def has_permission(self, request, view):
        """Check if user has metrics access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action == 'list':
            return permission_manager.has_permission('action', 'monitoring', 'read')
        elif view.action in ['retrieve', 'real_time', 'historical']:
            return permission_manager.has_permission('action', 'monitoring', 'read')
        elif view.action in ['export', 'dashboard']:
            return permission_manager.has_permission('action', 'reports', 'read')
        
        return False