"""
DRF serializers for authentication API endpoints
Handles data validation and serialization for async views
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import UserType, UserSession, ExtendedPermission, UserTypePermission

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