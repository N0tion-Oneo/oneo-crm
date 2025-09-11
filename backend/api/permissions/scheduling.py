"""
Scheduling-specific permission classes
Simple two-level permission model: manage_all or manage_own
"""
from rest_framework import permissions
from authentication.permissions import SyncPermissionManager
from django.db.models import Q


class SchedulingPermission(permissions.BasePermission):
    """
    Simple scheduling permissions - manage all or manage own
    
    Permission levels:
    - communication_settings.scheduling_all: Admin can manage all scheduling (profiles, meeting types, meetings)
    - communication_settings.scheduling: User can manage only their own scheduling
    """
    
    def has_permission(self, request, view):
        """Check if user has any scheduling permission"""
        if not request.user.is_authenticated:
            return False
            
        permission_manager = SyncPermissionManager(request.user)
        
        # Check if user has any scheduling permission
        has_scheduling_all = permission_manager.has_permission('action', 'communication_settings', 'scheduling_all', None)
        has_scheduling = permission_manager.has_permission('action', 'communication_settings', 'scheduling', None)
        
        # Allow access if user has either permission
        return has_scheduling_all or has_scheduling
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = SyncPermissionManager(request.user)
        
        # Admin can manage all scheduling objects
        if permission_manager.has_permission('action', 'communication_settings', 'scheduling_all', None):
            return True
        
        # Users can only manage their own scheduling objects
        if permission_manager.has_permission('action', 'communication_settings', 'scheduling', None):
            # Check if object belongs to user
            if hasattr(obj, 'user'):
                return obj.user == request.user
            elif hasattr(obj, 'host'):
                # For scheduled meetings, check if user is the host
                return obj.host == request.user
            elif hasattr(obj, 'created_by'):
                # For objects with created_by field
                return obj.created_by == request.user
                
        return False


class SchedulingProfilePermission(SchedulingPermission):
    """Permission class specifically for scheduling profiles"""
    pass


class MeetingTypePermission(SchedulingPermission):
    """Permission class specifically for meeting types"""
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions for meeting types"""
        permission_manager = SyncPermissionManager(request.user)
        
        # Admin can manage all meeting types
        if permission_manager.has_permission('action', 'communication_settings', 'scheduling_all', None):
            return True
        
        # For templates, allow read access (including copy_from_template action) to all authenticated users
        if obj.is_template and request.method in ['GET', 'POST'] and view.action == 'copy_from_template':
            return True
        
        # Users can only manage their own meeting types
        if permission_manager.has_permission('action', 'communication_settings', 'scheduling', None):
            # Check if object belongs to user
            if hasattr(obj, 'user'):
                return obj.user == request.user
                
        return False


class ScheduledMeetingPermission(permissions.BasePermission):
    """
    Permission class for scheduled meetings
    Users can see meetings they host OR participate in
    """
    
    def has_permission(self, request, view):
        """Check if user has any scheduling permission"""
        if not request.user.is_authenticated:
            return False
            
        permission_manager = SyncPermissionManager(request.user)
        
        # Check if user has any scheduling permission
        has_scheduling_all = permission_manager.has_permission('action', 'communication_settings', 'scheduling_all', None)
        has_scheduling = permission_manager.has_permission('action', 'communication_settings', 'scheduling', None)
        
        return has_scheduling_all or has_scheduling
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions for scheduled meetings"""
        permission_manager = SyncPermissionManager(request.user)
        
        # Admin can manage all meetings
        if permission_manager.has_permission('action', 'communication_settings', 'scheduling_all', None):
            return True
        
        # Users can manage meetings they host or participate in
        if permission_manager.has_permission('action', 'communication_settings', 'scheduling', None):
            # Check if user is the host
            if obj.host == request.user:
                return True
            
            # Check if user is a participant (by email)
            if hasattr(obj, 'participant') and obj.participant:
                if obj.participant.email == request.user.email:
                    return True
            
            # Check if meeting is from user's meeting type
            if hasattr(obj, 'meeting_type') and obj.meeting_type:
                if obj.meeting_type.user == request.user:
                    return True
                
        return False


class SchedulingLinkPermission(SchedulingPermission):
    """Permission class specifically for scheduling links"""
    pass


class AvailabilityOverridePermission(SchedulingPermission):
    """
    Permission class for availability overrides
    These are tied to scheduling profiles
    """
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions for availability overrides"""
        permission_manager = SyncPermissionManager(request.user)
        
        # Admin can manage all
        if permission_manager.has_permission('action', 'communication_settings', 'scheduling_all', None):
            return True
        
        # Users can manage overrides for their own profiles
        if permission_manager.has_permission('action', 'communication_settings', 'scheduling', None):
            if hasattr(obj, 'profile') and obj.profile:
                return obj.profile.user == request.user
                
        return False