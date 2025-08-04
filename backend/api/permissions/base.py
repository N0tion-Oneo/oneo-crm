"""
Base permission classes for API endpoints
"""
from rest_framework import permissions


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