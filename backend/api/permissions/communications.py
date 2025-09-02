"""
Communication-specific permission classes
"""
from rest_framework import permissions
from authentication.permissions import SyncPermissionManager


class CommunicationPermission(permissions.BasePermission):
    """Communication management permissions"""
    
    def has_permission(self, request, view):
        """Check if user has general communication access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action == 'list':
            return permission_manager.has_permission('action', 'communications', 'read')
        elif view.action == 'create':
            return permission_manager.has_permission('action', 'communications', 'create')
        elif view.action in ['retrieve', 'analytics', 'export']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['update', 'partial_update']:
            return True  # Object-level check in has_object_permission
        elif view.action == 'destroy':
            return True  # Object-level check in has_object_permission
        elif view.action in ['send', 'resend']:
            return True  # Object-level check in has_object_permission
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action in ['retrieve', 'analytics', 'export']:
            return permission_manager.has_permission('action', 'communications', 'read', str(obj.id))
        elif view.action in ['update', 'partial_update']:
            return permission_manager.has_permission('action', 'communications', 'update', str(obj.id))
        elif view.action == 'destroy':
            return permission_manager.has_permission('action', 'communications', 'delete', str(obj.id))
        elif view.action in ['send', 'resend']:
            return permission_manager.has_permission('action', 'communications', 'send', str(obj.id))
        
        return False


class MessagePermission(permissions.BasePermission):
    """Message-specific permissions"""
    
    def has_permission(self, request, view):
        """Check if user has message access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action == 'list':
            return permission_manager.has_permission('action', 'communications', 'read')
        elif view.action == 'create':
            return permission_manager.has_permission('action', 'communications', 'send')
        elif view.action in ['retrieve', 'thread', 'attachments', 'mark_read']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['update', 'partial_update']:
            return True  # Object-level check in has_object_permission
        elif view.action == 'destroy':
            return True  # Object-level check in has_object_permission
        elif view.action in ['reply', 'forward']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['unmatched_contacts', 'domain_validation_warnings']:
            # Contact resolution actions - require communication read access
            return permission_manager.has_permission('action', 'communications', 'read')
        elif view.action in ['connect_contact', 'create_contact']:
            # Contact resolution actions - require communication update access
            return True  # Object-level check in has_object_permission
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action in ['retrieve', 'thread', 'attachments', 'mark_read']:
            return permission_manager.has_permission('action', 'communications', 'read')
        elif view.action in ['update', 'partial_update']:
            # Only allow editing own messages or with update permission
            if obj.sent_by == request.user:
                return True
            return permission_manager.has_permission('action', 'communications', 'update')
        elif view.action == 'destroy':
            # Only allow deleting own messages or with delete permission
            if obj.sent_by == request.user:
                return True
            return permission_manager.has_permission('action', 'communications', 'delete')
        elif view.action in ['reply', 'forward']:
            return permission_manager.has_permission('action', 'communications', 'send')
        elif view.action in ['connect_contact', 'create_contact']:
            # Contact resolution actions require communications update permission
            return permission_manager.has_permission('action', 'communications', 'update')
        
        return False


class ChannelPermission(permissions.BasePermission):
    """Communication channel permissions"""
    
    def has_permission(self, request, view):
        """Check if user has channel access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action == 'list':
            return permission_manager.has_permission('action', 'communications', 'read')
        elif view.action == 'create':
            return permission_manager.has_permission('action', 'communications', 'create')
        elif view.action in ['retrieve', 'messages', 'statistics']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['update', 'partial_update']:
            return True  # Object-level check in has_object_permission
        elif view.action == 'destroy':
            return True  # Object-level check in has_object_permission
        elif view.action in ['sync', 'test_connection']:
            return True  # Object-level check in has_object_permission
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action in ['retrieve', 'messages', 'statistics']:
            return permission_manager.has_permission('action', 'communications', 'read')
        elif view.action in ['update', 'partial_update']:
            return permission_manager.has_permission('action', 'communications', 'update')
        elif view.action == 'destroy':
            return permission_manager.has_permission('action', 'communications', 'delete')
        elif view.action in ['sync', 'test_connection']:
            return permission_manager.has_permission('action', 'communications', 'send')
        
        return False


class CommunicationTrackingPermission(permissions.BasePermission):
    """Communication tracking and analytics permissions"""
    
    def has_permission(self, request, view):
        """Check if user has tracking access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action == 'list':
            return permission_manager.has_permission('action', 'communications', 'read')
        elif view.action in ['retrieve', 'analytics', 'report']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['update', 'partial_update']:
            return True  # Object-level check in has_object_permission
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action in ['retrieve', 'analytics', 'report']:
            return permission_manager.has_permission('action', 'communications', 'read')
        elif view.action in ['update', 'partial_update']:
            return permission_manager.has_permission('action', 'communications', 'update')
        
        return False