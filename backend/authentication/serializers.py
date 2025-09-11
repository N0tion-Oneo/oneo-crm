"""
DRF serializers for authentication API endpoints
Handles data validation and serialization for async views
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import (
    UserType, UserSession, ExtendedPermission, UserTypePermission,
    UserTypePipelinePermission, UserTypeFieldPermission, UserPipelinePermissionOverride,
    StaffProfile
)

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    """Serializer for login requests"""
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    remember_me = serializers.BooleanField(default=False)

    def validate_username(self, value):
        """Validate username field"""
        if not value.strip():
            raise serializers.ValidationError("Username cannot be empty")
        return value.strip()

    def validate_password(self, value):
        """Validate password field"""
        if not value:
            raise serializers.ValidationError("Password cannot be empty")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change requests"""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    destroy_other_sessions = serializers.BooleanField(default=False)

    def validate_old_password(self, value):
        """Validate old password field"""
        if not value:
            raise serializers.ValidationError("Current password is required")
        return value

    def validate_new_password(self, value):
        """Validate new password with Django validators"""
        if not value:
            raise serializers.ValidationError("New password is required")
        
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        
        return value

    def validate(self, attrs):
        """Validate password confirmation"""
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')
        
        if new_password != confirm_password:
            raise serializers.ValidationError(
                "New password and confirmation do not match"
            )
        
        return attrs


class UserTypeSerializer(serializers.ModelSerializer):
    """Serializer for UserType model"""
    user_count = serializers.SerializerMethodField()
    
    class Meta:
        model = UserType
        fields = [
            'id', 'name', 'slug', 'description', 
            'is_system_default', 'is_custom',
            'base_permissions', 'dashboard_config', 'menu_permissions',
            'user_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'user_count']

    def get_user_count(self, obj):
        """Get count of users with this type"""
        return obj.customuser_set.count()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    user_type_name = serializers.CharField(source='user_type.name', read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'timezone', 'language', 'avatar_url',
            'user_type', 'user_type_name', 'is_active', 'is_staff',
            'last_login', 'last_activity', 'date_joined'
        ]
        read_only_fields = [
            'id', 'last_login', 'last_activity', 'date_joined', 
            'user_type_name', 'full_name'
        ]

    def get_full_name(self, obj):
        """Get user's full name"""
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class UserSessionSerializer(serializers.ModelSerializer):
    """Serializer for UserSession model"""
    user_username = serializers.CharField(source='user.username', read_only=True)
    is_current = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    browser_info = serializers.SerializerMethodField()
    
    class Meta:
        model = UserSession
        fields = [
            'id', 'session_key', 'user', 'user_username',
            'created_at', 'last_activity', 'expires_at',
            'ip_address', 'user_agent', 'device_info',
            'is_current', 'is_expired', 'browser_info'
        ]
        read_only_fields = [
            'id', 'session_key', 'created_at', 'last_activity',
            'user_username', 'is_current', 'is_expired', 'browser_info'
        ]

    def get_is_current(self, obj):
        """Check if this is the current session"""
        request = self.context.get('request')
        if request and hasattr(request, 'user_session'):
            return request.user_session.id == obj.id
        return False

    def get_is_expired(self, obj):
        """Check if session is expired"""
        from django.utils import timezone
        return obj.expires_at < timezone.now()

    def get_browser_info(self, obj):
        """Get formatted browser information"""
        device_info = obj.device_info or {}
        browser = device_info.get('browser', 'Unknown')
        os = device_info.get('os', 'Unknown')
        device_type = device_info.get('device_type', 'Unknown')
        
        return f"{browser} on {os} ({device_type})"


class ExtendedPermissionSerializer(serializers.ModelSerializer):
    """Serializer for ExtendedPermission model"""
    content_type_name = serializers.CharField(source='content_type.name', read_only=True)
    
    class Meta:
        model = ExtendedPermission
        fields = [
            'id', 'name', 'codename', 'description',
            'permission_type', 'resource_type', 'resource_id',
            'content_type', 'content_type_name', 'is_system'
        ]
        read_only_fields = ['id', 'content_type_name']


class UserTypePermissionSerializer(serializers.ModelSerializer):
    """Serializer for UserTypePermission model"""
    user_type_name = serializers.CharField(source='user_type.name', read_only=True)
    permission_name = serializers.CharField(source='permission.name', read_only=True)
    permission_codename = serializers.CharField(source='permission.codename', read_only=True)
    
    class Meta:
        model = UserTypePermission
        fields = [
            'id', 'user_type', 'user_type_name',
            'permission', 'permission_name', 'permission_codename',
            'is_granted', 'conditions', 'traversal_depth',
            'field_restrictions', 'created_at'
        ]
        read_only_fields = [
            'id', 'user_type_name', 'permission_name', 
            'permission_codename', 'created_at'
        ]


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration (if needed in future)"""
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'confirm_password',
            'first_name', 'last_name', 'phone', 'timezone', 'language'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
        }

    def validate_email(self, value):
        """Validate email is unique"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def validate_username(self, value):
        """Validate username is unique"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists")
        return value

    def validate_password(self, value):
        """Validate password with Django validators"""
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def validate(self, attrs):
        """Validate password confirmation"""
        password = attrs.get('password')
        confirm_password = attrs.pop('confirm_password', None)
        
        if password != confirm_password:
            raise serializers.ValidationError(
                "Password and confirmation do not match"
            )
        
        return attrs

    def create(self, validated_data):
        """Create user with hashed password"""
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new users"""
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'confirm_password',
            'first_name', 'last_name', 'phone', 'timezone', 'language',
            'user_type', 'is_active', 'is_staff'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
        }

    def validate_email(self, value):
        """Validate email is unique"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def validate_username(self, value):
        """Validate username is unique"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists")
        return value

    def validate_password(self, value):
        """Validate password with Django validators"""
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def validate(self, attrs):
        """Validate password confirmation"""
        password = attrs.get('password')
        confirm_password = attrs.pop('confirm_password', None)
        
        if password != confirm_password:
            raise serializers.ValidationError({
                'confirm_password': "Password and confirmation do not match"
            })
        
        return attrs

    def create(self, validated_data):
        """Create user with hashed password"""
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating existing users"""
    
    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email', 'phone', 
            'timezone', 'language', 'avatar_url',
            'user_type', 'is_active', 'is_staff'
        ]
    
    def validate_username(self, value):
        """Validate username is unique within the tenant"""
        if not value or not value.strip():
            raise serializers.ValidationError("Username cannot be empty")
        
        # Check for valid characters
        import re
        if not re.match(r'^[a-zA-Z0-9._-]+$', value):
            raise serializers.ValidationError(
                "Username can only contain letters, numbers, dots, underscores, and hyphens"
            )
        
        # Check uniqueness (exclude current user)
        user = self.instance
        if User.objects.exclude(id=user.id).filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken")
        
        return value

    def validate_email(self, value):
        """Validate email is unique (excluding current user)"""
        if self.instance and self.instance.email != value:
            if User.objects.filter(email=value).exists():
                raise serializers.ValidationError("Email already exists")
        return value


class PermissionSummarySerializer(serializers.Serializer):
    """Serializer for permission summary responses"""
    permissions = serializers.DictField()
    user_type = serializers.CharField(allow_null=True)
    resource_permissions = serializers.DictField(required=False)


class SessionExtensionSerializer(serializers.Serializer):
    """Serializer for session extension requests"""
    extend_by_hours = serializers.IntegerField(min_value=1, max_value=72, default=24)

    def validate_extend_by_hours(self, value):
        """Validate extension time"""
        if value < 1 or value > 72:
            raise serializers.ValidationError(
                "Extension time must be between 1 and 72 hours"
            )
        return value


class UserTypePipelinePermissionSerializer(serializers.ModelSerializer):
    """Serializer for pipeline-specific permissions"""
    
    user_type_name = serializers.CharField(source='user_type.name', read_only=True)
    user_type_slug = serializers.CharField(source='user_type.slug', read_only=True)
    
    class Meta:
        model = UserTypePipelinePermission
        fields = [
            'id', 'user_type', 'user_type_name', 'user_type_slug', 'pipeline_id',
            'permissions', 'access_level', 'can_view_all_records', 'can_edit_all_records',
            'can_delete_records', 'can_export_data', 'can_import_data',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_permissions(self, value):
        """Validate permissions list"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Permissions must be a list")
        
        valid_permissions = ['read', 'create', 'update', 'delete', 'export', 'import', 'clone']
        for perm in value:
            if perm not in valid_permissions:
                raise serializers.ValidationError(f"Invalid permission: {perm}")
        
        return value
    
    def validate_access_level(self, value):
        """Validate access level"""
        valid_levels = ['none', 'read', 'write', 'admin']
        if value not in valid_levels:
            raise serializers.ValidationError(f"Invalid access level: {value}")
        return value


class UserTypeFieldPermissionSerializer(serializers.ModelSerializer):
    """Serializer for field-level permissions"""
    
    user_type_name = serializers.CharField(source='user_type.name', read_only=True)
    user_type_slug = serializers.CharField(source='user_type.slug', read_only=True)
    
    class Meta:
        model = UserTypeFieldPermission
        fields = [
            'id', 'user_type', 'user_type_name', 'user_type_slug', 'pipeline_id', 'field_id',
            'can_view', 'can_edit', 'can_require', 'visibility', 'visibility_conditions',
            'default_value', 'value_constraints', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_visibility(self, value):
        """Validate visibility level"""
        valid_levels = ['visible', 'hidden', 'conditional', 'readonly']
        if value not in valid_levels:
            raise serializers.ValidationError(f"Invalid visibility level: {value}")
        return value
    
    def validate_visibility_conditions(self, value):
        """Validate visibility conditions"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Visibility conditions must be a dictionary")
        return value
    
    def validate_value_constraints(self, value):
        """Validate value constraints"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Value constraints must be a dictionary")
        return value


class UserPipelinePermissionOverrideSerializer(serializers.ModelSerializer):
    """Serializer for user pipeline permission overrides"""
    
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    granted_by_email = serializers.CharField(source='granted_by.email', read_only=True)
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = UserPipelinePermissionOverride
        fields = [
            'id', 'user', 'user_email', 'user_name', 'pipeline_id', 'permissions',
            'access_level', 'can_view_all_records', 'can_edit_all_records',
            'can_delete_records', 'can_export_data', 'can_import_data',
            'granted_by', 'granted_by_email', 'granted_at', 'expires_at',
            'reason', 'is_expired'
        ]
        read_only_fields = ['id', 'granted_at', 'is_expired']
    
    def get_is_expired(self, obj):
        """Check if the override is expired"""
        return obj.is_expired()
    
    def validate_permissions(self, value):
        """Validate permissions list"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Permissions must be a list")
        
        valid_permissions = ['read', 'create', 'update', 'delete', 'export', 'import', 'clone']
        for perm in value:
            if perm not in valid_permissions:
                raise serializers.ValidationError(f"Invalid permission: {perm}")
        
        return value
    
    def validate_access_level(self, value):
        """Validate access level"""
        valid_levels = ['none', 'read', 'write', 'admin']
        if value not in valid_levels:
            raise serializers.ValidationError(f"Invalid access level: {value}")
        return value
    
    def validate(self, data):
        """Validate the entire override"""
        # Ensure expires_at is in the future if provided
        if data.get('expires_at') and data['expires_at'] <= timezone.now():
            raise serializers.ValidationError("Expiry date must be in the future")
        
        return data


class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    """
    A ModelSerializer that can dynamically include/exclude fields
    based on permissions.
    """
    
    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' arg up to the superclass
        fields = kwargs.pop('fields', None)
        exclude_fields = kwargs.pop('exclude_fields', None)

        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

        if fields is not None:
            # Drop any fields that are not specified in the `fields` argument.
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)

        if exclude_fields is not None:
            # Remove fields specified in the `exclude_fields` argument.
            for field_name in exclude_fields:
                self.fields.pop(field_name, None)


class StaffProfileSerializer(DynamicFieldsModelSerializer):
    """
    Full StaffProfile serializer with all fields.
    Field visibility is controlled by the ViewSet based on permissions.
    """
    
    # Read-only fields from the related user
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    user_type = serializers.CharField(source='user.user_type.name', read_only=True)
    
    # Manager information
    reporting_manager_email = serializers.EmailField(
        source='reporting_manager.email', 
        read_only=True,
        allow_null=True
    )
    reporting_manager_name = serializers.CharField(
        source='reporting_manager.get_full_name',
        read_only=True,
        allow_null=True
    )
    
    # Computed fields
    is_manager = serializers.BooleanField(read_only=True)
    direct_reports_count = serializers.SerializerMethodField()
    
    class Meta:
        model = StaffProfile
        fields = [
            'id', 'user', 'user_email', 'user_full_name', 'user_phone', 'user_type',
            
            # Professional Information
            'employee_id', 'job_title', 'department', 'employment_type',
            'employment_status', 'start_date', 'end_date',
            
            # Work Details
            'work_location', 'office_location', 'work_phone_extension',
            'reporting_manager', 'reporting_manager_email', 'reporting_manager_name',
            
            # Professional Details
            'education',
            'bio', 'linkedin_profile', 'professional_links',
            
            # Emergency & Personal (Sensitive)
            'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relationship', 'date_of_birth',
            'nationality', 'personal_email', 'home_address',
            
            # Administrative (Restricted)
            'internal_notes',
            
            # Metadata
            'is_manager', 'direct_reports_count',
            'created_at', 'updated_at', 'created_by'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_manager']
    
    def get_direct_reports_count(self, obj):
        """Get count of direct reports"""
        return obj.user.direct_reports.count()
    
    def validate_employee_id(self, value):
        """Ensure employee_id is unique if provided"""
        # Allow empty employee_id
        if not value:
            return value
            
        qs = StaffProfile.objects.filter(employee_id=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Employee ID must be unique")
        return value
    
    def validate_reporting_manager(self, value):
        """Validate reporting manager to prevent circular references"""
        if self.instance and value:
            # Check if this would create a circular reference
            current = value
            while current:
                if current == self.instance.user:
                    raise serializers.ValidationError(
                        "This would create a circular reporting structure"
                    )
                try:
                    current = current.staff_profile.reporting_manager
                except StaffProfile.DoesNotExist:
                    break
        return value


class StaffProfilePublicSerializer(serializers.ModelSerializer):
    """
    Limited StaffProfile serializer for public/peer viewing.
    Only includes non-sensitive professional information.
    """
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_type = serializers.CharField(source='user.user_type.name', read_only=True)
    reporting_manager_name = serializers.CharField(
        source='reporting_manager.get_full_name',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = StaffProfile
        fields = [
            'id', 'user_email', 'user_full_name', 'user_type',
            'job_title', 'department', 'work_location', 'office_location',
            'bio', 'linkedin_profile', 'reporting_manager_name'
        ]
        read_only_fields = fields


class StaffProfileCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new staff profiles.
    """
    
    class Meta:
        model = StaffProfile
        fields = [
            'user', 'employee_id', 'job_title', 'department',
            'employment_type', 'employment_status', 'start_date',
            'work_location', 'office_location', 'work_phone_extension',
            'reporting_manager'
        ]
    
    def validate_user(self, value):
        """Ensure user doesn't already have a profile"""
        if StaffProfile.objects.filter(user=value).exists():
            raise serializers.ValidationError(
                "This user already has a staff profile"
            )
        return value
    
    def validate_employee_id(self, value):
        """Ensure employee_id is unique"""
        if StaffProfile.objects.filter(employee_id=value).exists():
            raise serializers.ValidationError("Employee ID must be unique")
        return value


class StaffProfileSummarySerializer(serializers.ModelSerializer):
    """
    Minimal serializer for listing staff profiles.
    """
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = StaffProfile
        fields = [
            'id', 'employee_id', 'user_email', 'user_full_name',
            'job_title', 'department', 'employment_status'
        ]
        read_only_fields = fields