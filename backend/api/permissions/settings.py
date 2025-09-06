"""
Settings-specific permission classes with granular permissions for each category
"""
from rest_framework import permissions
from authentication.permissions import SyncPermissionManager


class OrganizationSettingsPermission(permissions.BasePermission):
    """Organization settings page permissions"""
    
    def has_permission(self, request, view):
        """Check if user has organization settings page access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        # Single permission per page - having access means can view and edit
        if view.action in ['list', 'retrieve', 'create', 'update', 'partial_update', 'upload_logo']:
            return permission_manager.has_permission('action', 'settings', 'organization', None)
        
        elif view.action == 'usage':
            # Usage statistics moved to its own page permission
            return permission_manager.has_permission('action', 'settings', 'usage', None)
        
        elif view.action in ['email_signature_preview', 'render_email_signature']:
            # Email signature is part of branding page
            return permission_manager.has_permission('action', 'settings', 'branding', None)
        
        elif view.action == 'destroy':
            return False  # Never allow deletion of settings
        
        return False


class LocalizationSettingsPermission(permissions.BasePermission):
    """Localization settings page permissions"""
    
    def has_permission(self, request, view):
        """Check if user can access localization settings page"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        # Single permission per page
        if view.action in ['list', 'retrieve', 'create', 'update', 'partial_update']:
            return permission_manager.has_permission('action', 'settings', 'localization', None)
        elif view.action == 'destroy':
            return False  # Never allow deletion
        
        return False


class BrandingSettingsPermission(permissions.BasePermission):
    """Branding settings page permissions"""
    
    def has_permission(self, request, view):
        """Check if user can access branding settings page"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        # Single permission per page
        if view.action in ['list', 'retrieve', 'create', 'update', 'partial_update']:
            return permission_manager.has_permission('action', 'settings', 'branding', None)
        elif view.action == 'destroy':
            return False  # Never allow deletion
        
        return False


class SecurityPoliciesPermission(permissions.BasePermission):
    """Security settings page permissions - more restrictive"""
    
    def has_permission(self, request, view):
        """Check if user can access security settings page"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        # Single permission per page (keep system full_access as override)
        if view.action in ['list', 'retrieve', 'create', 'update', 'partial_update']:
            return (permission_manager.has_permission('action', 'settings', 'security', None) or
                    permission_manager.has_permission('action', 'system', 'full_access', None))
        elif view.action == 'destroy':
            return False  # Never allow deletion
        
        return False


class DataPoliciesPermission(permissions.BasePermission):
    """Data policies page permissions - more restrictive"""
    
    def has_permission(self, request, view):
        """Check if user can access data policies page"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        # Single permission per page (keep system full_access as override)
        if view.action in ['list', 'retrieve', 'create', 'update', 'partial_update']:
            return (permission_manager.has_permission('action', 'settings', 'data_policies', None) or
                    permission_manager.has_permission('action', 'system', 'full_access', None))
        elif view.action == 'destroy':
            return False  # Never allow deletion
        
        return False


class UsageAndBillingPermission(permissions.BasePermission):
    """Usage page permissions"""
    
    def has_permission(self, request, view):
        """Check if user can access usage page"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        # Single permission per page
        if view.action in ['list', 'retrieve', 'usage', 'create', 'update', 'partial_update']:
            return (permission_manager.has_permission('action', 'settings', 'usage', None) or
                    permission_manager.has_permission('action', 'system', 'full_access', None))
        elif view.action == 'destroy':
            return False  # Never allow deletion
        
        return False


# Communication Settings Sub-Permissions (already partially exist)

class CommunicationGeneralSettingsPermission(permissions.BasePermission):
    """Communication general settings page permissions"""
    
    def has_permission(self, request, view):
        """Check if user can access communication general settings page"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action in ['list', 'retrieve', 'create', 'update', 'partial_update']:
            return permission_manager.has_permission('action', 'communication_settings', 'general', None)
        elif view.action == 'destroy':
            return False
        
        return False


class CommunicationAccountsSettingsPermission(permissions.BasePermission):
    """Communication accounts page permissions"""
    
    def has_permission(self, request, view):
        """Check if user can access communication accounts page"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action in ['list', 'retrieve', 'create', 'update', 'partial_update']:
            return permission_manager.has_permission('action', 'communication_settings', 'accounts', None)
        elif view.action == 'destroy':
            return False
        
        return False


class CommunicationProviderSettingsPermission(permissions.BasePermission):
    """Communication providers page permissions"""
    
    def has_permission(self, request, view):
        """Check if user can access communication providers page"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action in ['list', 'retrieve', 'create', 'update', 'partial_update']:
            return permission_manager.has_permission('action', 'communication_settings', 'providers', None)
        elif view.action == 'destroy':
            return False
        
        return False


class CommunicationParticipantsSettingsPermission(permissions.BasePermission):
    """Communication participants settings page permissions"""
    
    def has_permission(self, request, view):
        """Check if user can access communication participants settings page"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action in ['list', 'retrieve', 'create', 'update', 'partial_update']:
            return permission_manager.has_permission('action', 'communication_settings', 'participants', None)
        elif view.action == 'destroy':
            return False
        
        return False


class CommunicationAdvancedSettingsPermission(permissions.BasePermission):
    """Communication advanced settings page permissions"""
    
    def has_permission(self, request, view):
        """Check if user can access communication advanced settings page"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action in ['list', 'retrieve', 'create', 'update', 'partial_update']:
            return (permission_manager.has_permission('action', 'communication_settings', 'advanced', None) or
                    permission_manager.has_permission('action', 'system', 'full_access', None))
        elif view.action == 'destroy':
            return False
        
        return False


class UsersSettingsPermission(permissions.BasePermission):
    """Users settings page permissions"""
    
    def has_permission(self, request, view):
        """Check if user can access users settings page"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        # Single permission per page
        if view.action in ['list', 'retrieve', 'create', 'update', 'partial_update']:
            return permission_manager.has_permission('action', 'settings', 'users', None)
        elif view.action == 'destroy':
            # May want to allow user deletion with proper permission
            return permission_manager.has_permission('action', 'settings', 'users', None)
        
        return False


class PermissionsSettingsPermission(permissions.BasePermission):
    """Permissions settings page permissions"""
    
    def has_permission(self, request, view):
        """Check if user can access permissions settings page"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        # Single permission per page (keep system full_access as override)
        if view.action in ['list', 'retrieve', 'create', 'update', 'partial_update']:
            return (permission_manager.has_permission('action', 'settings', 'permissions', None) or
                    permission_manager.has_permission('action', 'system', 'full_access', None))
        elif view.action == 'destroy':
            return False
        
        return False


class AISettingsPermission(permissions.BasePermission):
    """AI settings page permissions"""
    
    def has_permission(self, request, view):
        """Check if user can access AI settings page"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        # Page access controlled by settings.ai permission
        if view.action in ['list', 'retrieve', 'create', 'update', 'partial_update']:
            return permission_manager.has_permission('action', 'settings', 'ai', None)
        elif view.action == 'destroy':
            return False
        
        return False