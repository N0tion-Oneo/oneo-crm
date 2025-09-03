"""
Permission classes for staff profile management
"""
from rest_framework import permissions
from authentication.permissions import SyncPermissionManager


class StaffProfilePermission(permissions.BasePermission):
    """
    Permission class for staff profile access with field-level control.
    """
    
    # Define sensitive fields that require special permissions
    SENSITIVE_FIELDS = {
        'date_of_birth', 'nationality', 'personal_email', 'home_address',
        'emergency_contact_name', 'emergency_contact_phone', 
        'emergency_contact_relationship'
    }
    
    # Define admin-only fields
    ADMIN_FIELDS = {'internal_notes'}
    
    # Public fields visible to all authenticated users
    PUBLIC_FIELDS = {
        'id', 'user_email', 'user_full_name', 'user_type',
        'job_title', 'department', 'work_location', 'office_location',
        'bio', 'linkedin_profile', 'reporting_manager_name'
    }
    
    def has_permission(self, request, view):
        """
        Check if user has permission to access staff profiles endpoint.
        """
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        # For list and create operations
        if view.action == 'list':
            # Users can at minimum see public info of staff
            return permission_manager.has_permission('action', 'staff_profiles', 'read')
        elif view.action == 'create':
            return permission_manager.has_permission('action', 'staff_profiles', 'create')
        
        # For other operations, check at object level
        return True
    
    def has_object_permission(self, request, view, obj):
        """
        Check if user has permission to access a specific staff profile.
        """
        if not request.user.is_authenticated:
            return False
        
        permission_manager = SyncPermissionManager(request.user)
        
        # Check if it's the user's own profile
        is_own_profile = obj.user == request.user
        
        # Check if user is the manager of this staff member
        is_manager = obj.reporting_manager == request.user
        
        # For read operations
        if view.action in ['retrieve', 'list']:
            # Users can read their own profile
            if is_own_profile:
                return True
            
            # Managers can read their direct reports
            if is_manager:
                return True
            
            # Check for read_all permission
            return permission_manager.has_permission('action', 'staff_profiles', 'read_all')
        
        # For update operations
        elif view.action in ['update', 'partial_update']:
            # Users can update their own profile (non-sensitive fields)
            if is_own_profile:
                return permission_manager.has_permission('action', 'staff_profiles', 'update')
            
            # Managers can update their direct reports (limited fields)
            if is_manager:
                return permission_manager.has_permission('action', 'staff_profiles', 'update_all')
            
            # Check for update_all permission (admin/HR)
            return permission_manager.has_permission('action', 'staff_profiles', 'update_all')
        
        # For delete operations
        elif view.action == 'destroy':
            return permission_manager.has_permission('action', 'staff_profiles', 'delete')
        
        return False
    
    @classmethod
    def get_allowed_fields(cls, user, target_profile):
        """
        Determine which fields a user can access for a given profile.
        Returns a set of field names.
        """
        permission_manager = SyncPermissionManager(user)
        allowed_fields = set()
        
        # Start with public fields - everyone can see these
        allowed_fields.update(cls.PUBLIC_FIELDS)
        
        # Check if it's the user's own profile
        is_own_profile = target_profile.user == user
        
        # Check if user is the manager
        is_manager = target_profile.reporting_manager == user
        
        if is_own_profile:
            # Users can see all their own fields except admin fields
            all_fields = set(target_profile._meta.get_fields())
            field_names = {f.name for f in all_fields}
            allowed_fields.update(field_names - cls.ADMIN_FIELDS)
        
        elif is_manager:
            # Managers can see more fields for their direct reports
            allowed_fields.update({
                'employee_id', 'employment_type', 'employment_status',
                'start_date', 'end_date', 'work_phone_extension',
                'certifications', 'languages_spoken', 'education',
                'professional_links'
            })
            
            # Managers can also see emergency contacts for their reports
            if permission_manager.has_permission('action', 'staff_profiles', 'read_sensitive'):
                allowed_fields.update({
                    'emergency_contact_name', 'emergency_contact_phone',
                    'emergency_contact_relationship'
                })
        
        # Check for read_sensitive permission (HR/Admin)
        if permission_manager.has_permission('action', 'staff_profiles', 'read_sensitive'):
            allowed_fields.update(cls.SENSITIVE_FIELDS)
        
        # Check for admin permission (internal notes)
        if permission_manager.has_permission('action', 'staff_profiles', 'update_sensitive'):
            allowed_fields.update(cls.ADMIN_FIELDS)
        
        # Add metadata fields for those with appropriate permissions
        if permission_manager.has_permission('action', 'staff_profiles', 'read_all'):
            allowed_fields.update({
                'created_at', 'updated_at', 'created_by',
                'is_manager', 'direct_reports_count'
            })
        
        return allowed_fields
    
    @classmethod
    def filter_serializer_fields(cls, serializer, user, instance):
        """
        Filter serializer fields based on user permissions.
        Modifies the serializer in place.
        """
        allowed_fields = cls.get_allowed_fields(user, instance)
        
        # Get all fields from the serializer
        all_fields = set(serializer.fields.keys())
        
        # Remove fields that are not allowed
        fields_to_remove = all_fields - allowed_fields
        for field_name in fields_to_remove:
            serializer.fields.pop(field_name, None)
        
        return serializer