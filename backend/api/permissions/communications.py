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
            return permission_manager.has_permission('action', 'communications', 'read', None)
        elif view.action == 'create':
            return permission_manager.has_permission('action', 'communications', 'create', None)
        elif view.action in ['retrieve', 'analytics', 'export']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['update', 'partial_update']:
            return True  # Object-level check in has_object_permission
        elif view.action == 'destroy':
            return True  # Object-level check in has_object_permission
        elif view.action in ['send', 'resend']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['mark_conversation_read', 'mark_conversation_unread', 'archive', 'stats']:
            return True  # Object-level check in has_object_permission or general action
        
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
        elif view.action in ['mark_conversation_read', 'mark_conversation_unread', 'archive']:
            # Allow users to mark conversations as read/unread if they can read them
            return permission_manager.has_permission('action', 'communications', 'update', str(obj.id))
        elif view.action == 'stats':
            # Stats is a list action, not object-specific
            return permission_manager.has_permission('action', 'communications', 'read', None)
        
        return False


class MessagePermission(permissions.BasePermission):
    """Message-specific permissions"""
    
    def has_permission(self, request, view):
        """Check if user has message access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action == 'list':
            return permission_manager.has_permission('action', 'communications', 'read', None)
        elif view.action == 'create':
            return permission_manager.has_permission('action', 'communications', 'send', None)
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
            return permission_manager.has_permission('action', 'communications', 'read', None)
        elif view.action in ['connect_contact', 'create_contact']:
            # Contact resolution actions - require communication update access
            return True  # Object-level check in has_object_permission
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action in ['retrieve', 'thread', 'attachments', 'mark_read']:
            return permission_manager.has_permission('action', 'communications', 'read', None)
        elif view.action in ['update', 'partial_update']:
            # Only allow editing own messages or with update permission
            if obj.sent_by == request.user:
                return True
            return permission_manager.has_permission('action', 'communications', 'update', None)
        elif view.action == 'destroy':
            # Only allow deleting own messages or with delete permission
            if obj.sent_by == request.user:
                return True
            return permission_manager.has_permission('action', 'communications', 'delete', None)
        elif view.action in ['reply', 'forward']:
            return permission_manager.has_permission('action', 'communications', 'send', None)
        elif view.action in ['connect_contact', 'create_contact']:
            # Contact resolution actions require communications update permission
            return permission_manager.has_permission('action', 'communications', 'update', None)
        
        return False


class ChannelPermission(permissions.BasePermission):
    """Communication channel permissions"""
    
    def has_permission(self, request, view):
        """Check if user has channel access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action == 'list':
            return permission_manager.has_permission('action', 'communications', 'read', None)
        elif view.action == 'create':
            return permission_manager.has_permission('action', 'communications', 'create', None)
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
            return permission_manager.has_permission('action', 'communications', 'read', None)
        elif view.action in ['update', 'partial_update']:
            return permission_manager.has_permission('action', 'communications', 'update', None)
        elif view.action == 'destroy':
            return permission_manager.has_permission('action', 'communications', 'delete', None)
        elif view.action in ['sync', 'test_connection']:
            return permission_manager.has_permission('action', 'communications', 'send', None)
        
        return False


class CommunicationTrackingPermission(permissions.BasePermission):
    """Communication tracking and analytics permissions"""
    
    def has_permission(self, request, view):
        """Check if user has tracking access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action == 'list':
            return permission_manager.has_permission('action', 'communications', 'read', None)
        elif view.action in ['retrieve', 'analytics', 'report']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['update', 'partial_update']:
            return True  # Object-level check in has_object_permission
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action in ['retrieve', 'analytics', 'report']:
            return permission_manager.has_permission('action', 'communications', 'read', None)
        elif view.action in ['update', 'partial_update']:
            return permission_manager.has_permission('action', 'communications', 'update', None)
        
        return False


class ParticipantPermission(permissions.BasePermission):
    """Participant management permissions"""
    
    def has_permission(self, request, view):
        """Check if user has general participant access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        # Check based on view action
        if view.action == 'list':
            return permission_manager.has_permission('action', 'participants', 'read', None)
        elif view.action == 'create':
            return permission_manager.has_permission('action', 'participants', 'create', None)
        elif view.action in ['retrieve', 'preview_field_mapping', 'get_field_mapping']:
            return permission_manager.has_permission('action', 'participants', 'read', None)
        elif view.action in ['update', 'partial_update']:
            return permission_manager.has_permission('action', 'participants', 'update', None)
        elif view.action == 'destroy':
            return permission_manager.has_permission('action', 'participants', 'delete', None)
        elif view.action in ['create_record', 'link_to_record']:
            # Require both participant link permission and pipeline permissions
            return permission_manager.has_permission('action', 'participants', 'link', None)
        elif view.action == 'bulk_action':
            # Require batch permission for bulk operations
            return permission_manager.has_permission('action', 'participants', 'batch', None)
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions for specific participants"""
        permission_manager = SyncPermissionManager(request.user)
        
        if view.action in ['retrieve', 'preview_field_mapping', 'get_field_mapping']:
            return permission_manager.has_permission('action', 'participants', 'read', None)
        elif view.action in ['update', 'partial_update']:
            return permission_manager.has_permission('action', 'participants', 'update', None)
        elif view.action == 'destroy':
            return permission_manager.has_permission('action', 'participants', 'delete', None)
        elif view.action in ['create_record', 'link_to_record']:
            # Also check pipeline permissions when linking
            if obj.contact_record and obj.contact_record.pipeline:
                has_pipeline_perm = permission_manager.has_permission(
                    'action', 'pipelines', 'update', str(obj.contact_record.pipeline.id)
                )
                if not has_pipeline_perm:
                    return False
            return permission_manager.has_permission('action', 'participants', 'link', None)
        
        return False


class ParticipantSettingsPermission(permissions.BasePermission):
    """Participant settings management permissions"""
    
    def has_permission(self, request, view):
        """Check if user can manage participant settings"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        # Settings page access uses communication_settings.participants permission
        if view.action in ['list', 'retrieve']:
            return permission_manager.has_permission('action', 'communication_settings', 'participants', None)
        elif view.action in ['create', 'update', 'partial_update']:
            return permission_manager.has_permission('action', 'communication_settings', 'participants', None)
        elif view.action == 'destroy':
            # Settings typically shouldn't be deleted, only updated
            return permission_manager.has_permission('action', 'communication_settings', 'participants', None)
        elif view.action in ['process_batch', 'dry_run']:
            # Batch processing requires both settings page access and batch permission
            has_settings = permission_manager.has_permission('action', 'communication_settings', 'participants', None)
            has_batch = permission_manager.has_permission('action', 'participants', 'batch', None)
            return has_settings and has_batch
        elif view.action in ['company_pipelines', 'get_creation_stats', 'compatible_pipelines']:
            return permission_manager.has_permission('action', 'communication_settings', 'participants', None)
        
        return False