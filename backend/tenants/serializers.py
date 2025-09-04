"""
Serializers for tenant management and registration
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django_tenants.utils import schema_context
from .models import Tenant, Domain
import re
import time

User = get_user_model()


class TenantRegistrationSerializer(serializers.Serializer):
    """
    Serializer for tenant registration (self-service organization signup)
    Creates new tenant, domain, and first customer admin user
    """
    # Organization details
    organization_name = serializers.CharField(max_length=100, help_text="Name of the organization")
    subdomain = serializers.CharField(max_length=63, help_text="Subdomain for tenant access")
    
    # Customer admin user details
    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=30)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    
    def validate_organization_name(self, value):
        """Validate organization name"""
        if not value.strip():
            raise serializers.ValidationError("Organization name cannot be empty")
        
        # Check if organization name already exists
        if Tenant.objects.filter(name__iexact=value.strip()).exists():
            raise serializers.ValidationError("An organization with this name already exists")
        
        return value.strip()
    
    def validate_subdomain(self, value):
        """Validate subdomain format and uniqueness"""
        value = value.lower().strip()
        
        # Check format
        if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$', value) and len(value) > 1:
            if not re.match(r'^[a-z0-9]$', value):
                raise serializers.ValidationError(
                    "Subdomain must contain only lowercase letters, numbers, and hyphens. "
                    "It cannot start or end with a hyphen."
                )
        
        # Check length
        if len(value) < 2 or len(value) > 63:
            raise serializers.ValidationError("Subdomain must be between 2 and 63 characters")
        
        # Check reserved names
        reserved_names = {
            'www', 'api', 'admin', 'app', 'mail', 'email', 'ftp', 'localhost',
            'staging', 'test', 'dev', 'demo', 'public', 'private', 'secure',
            'support', 'help', 'docs', 'blog', 'news', 'static', 'assets'
        }
        if value in reserved_names:
            raise serializers.ValidationError(f"'{value}' is a reserved subdomain")
        
        # Check uniqueness (domain will be subdomain.localhost for development)
        domain_name = f"{value}.localhost"
        if Domain.objects.filter(domain=domain_name).exists():
            raise serializers.ValidationError("This subdomain is already taken")
        
        return value
    
    def validate_email(self, value):
        """Validate email uniqueness across all tenants"""
        # Check across all tenant schemas for email uniqueness
        tenant_schemas = Tenant.objects.values_list('schema_name', flat=True)
        
        for schema_name in tenant_schemas:
            try:
                with schema_context(schema_name):
                    if User.objects.filter(email=value).exists():
                        raise serializers.ValidationError(
                            "An account with this email already exists"
                        )
            except Exception:
                # Schema might not exist yet or have issues, continue checking others
                continue
        
        return value
    
    def validate_password(self, value):
        """Validate password with Django validators"""
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value
    
    def create(self, validated_data):
        """
        Create tenant, domain, and customer admin user atomically
        Leverages existing signals for automatic Oneo team setup
        """
        organization_name = validated_data['organization_name']
        subdomain = validated_data['subdomain']
        
        # Customer admin user data
        user_data = {
            'first_name': validated_data['first_name'],
            'last_name': validated_data['last_name'],
            'email': validated_data['email'],
            'password': validated_data['password']
        }
        
        with transaction.atomic():
            # 1. Create tenant (this triggers automatic signals for Oneo team setup)
            schema_name = subdomain.replace('-', '_')  # Schema names can't have hyphens
            tenant = Tenant.objects.create(
                name=organization_name,
                schema_name=schema_name,
                max_users=100,  # Default limit
                features_enabled={
                    'pipelines': True,
                    'workflows': True,
                    'ai_integration': False,  # Disabled by default
                    'communications': True,
                    'analytics': True
                }
            )
            
            # 2. Create domain
            domain_name = f"{subdomain}.localhost"  # For development
            domain = Domain.objects.create(
                domain=domain_name,
                tenant=tenant,
                is_primary=True
            )
            
            # 3. Wait a moment for signals to complete their work
            # The signals create Oneo team accounts and default UserTypes
            time.sleep(3)  # Allow signal processing to complete
            
            # 4. Create customer admin user in tenant schema
            with schema_context(schema_name):
                from authentication.models import UserType
                
                # Get the admin user type (should exist from signal setup)
                admin_user_type = UserType.objects.filter(slug='admin').first()
                if not admin_user_type:
                    # Fallback: create admin user type if signal failed
                    admin_user_type = UserType.objects.create(
                        name='Admin',
                        slug='admin',
                        description='Full access to all tenant features',
                        is_system_default=True,
                        is_custom=False,
                        base_permissions={
                            'system': ['full_access'],
                            'pipelines': ['create', 'read', 'update', 'delete'],
                            'users': ['create', 'read', 'update', 'delete'],
                            'settings': ['read', 'update']
                        }
                    )
                
                # Create customer admin user (NOT Django superuser)
                admin_user = User.objects.create_user(
                    username=user_data['email'],  # Use email as username
                    email=user_data['email'],
                    password=user_data['password'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    user_type=admin_user_type,
                    is_superuser=False,  # NOT Django superuser
                    is_staff=False,      # NOT Django admin access
                    is_active=True
                )
        
        return {
            'tenant': tenant,
            'domain': domain,
            'admin_user': admin_user
        }


class TenantSerializer(serializers.ModelSerializer):
    """Serializer for Tenant model"""
    domain = serializers.SerializerMethodField()
    
    class Meta:
        model = Tenant
        fields = [
            'id', 'name', 'schema_name', 'created_on',
            'max_users', 'features_enabled', 'billing_settings',
            'ai_enabled', 'ai_usage_limit', 'ai_current_usage',
            'organization_logo', 'organization_description', 'organization_website',
            'support_email', 'support_phone', 'business_hours',
            'domain'
        ]
        read_only_fields = ['id', 'schema_name', 'created_on']
    
    def get_domain(self, obj):
        """Get primary domain for tenant"""
        primary_domain = obj.domains.filter(is_primary=True).first()
        return primary_domain.domain if primary_domain else None


class DomainSerializer(serializers.ModelSerializer):
    """Serializer for Domain model"""
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    
    class Meta:
        model = Domain
        fields = ['id', 'domain', 'tenant', 'tenant_name', 'is_primary']
        read_only_fields = ['id']


class LocalizationSettingsSerializer(serializers.Serializer):
    """Serializer for localization settings"""
    timezone = serializers.CharField(max_length=50, default='UTC')
    date_format = serializers.ChoiceField(
        choices=['MM/DD/YYYY', 'DD/MM/YYYY', 'YYYY-MM-DD'],
        default='MM/DD/YYYY'
    )
    time_format = serializers.ChoiceField(
        choices=['12h', '24h'],
        default='12h'
    )
    currency = serializers.CharField(max_length=3, default='USD')
    language = serializers.CharField(max_length=2, default='en')
    week_start_day = serializers.ChoiceField(
        choices=['sunday', 'monday'],
        default='sunday'
    )


class BrandingSettingsSerializer(serializers.Serializer):
    """Serializer for branding settings"""
    primary_color = serializers.RegexField(
        regex=r'^#[0-9A-Fa-f]{6}$',
        max_length=7,
        default='#3B82F6',
        error_messages={'invalid': 'Enter a valid hex color code'}
    )
    secondary_color = serializers.RegexField(
        regex=r'^#[0-9A-Fa-f]{6}$',
        max_length=7,
        default='#10B981',
        error_messages={'invalid': 'Enter a valid hex color code'}
    )
    email_header_html = serializers.CharField(
        max_length=5000,
        allow_blank=True,
        required=False
    )
    login_message = serializers.CharField(
        max_length=500,
        allow_blank=True,
        required=False
    )
    email_signature_template = serializers.CharField(
        max_length=10000,
        allow_blank=True,
        required=False,
        help_text="HTML template for email signatures with variables like {user_full_name}, {user_email}, etc."
    )
    email_signature_enabled = serializers.BooleanField(
        default=False,
        help_text="Enable standardized email signatures for all users"
    )
    email_signature_variables = serializers.SerializerMethodField(
        read_only=True,
        help_text="Available variables for use in email signature template"
    )
    
    def get_email_signature_variables(self, obj):
        """Get categorized email signature variables"""
        from tenants.models import Tenant
        return Tenant.get_email_signature_variables()


class PasswordComplexitySerializer(serializers.Serializer):
    """Serializer for password complexity rules"""
    require_uppercase = serializers.BooleanField(default=True)
    require_lowercase = serializers.BooleanField(default=True)
    require_numbers = serializers.BooleanField(default=True)
    require_special = serializers.BooleanField(default=False)


class SecurityPoliciesSerializer(serializers.Serializer):
    """Serializer for security policies"""
    password_min_length = serializers.IntegerField(
        min_value=8,
        max_value=32,
        default=8
    )
    password_complexity = PasswordComplexitySerializer(required=False)
    session_timeout_minutes = serializers.IntegerField(
        min_value=15,
        max_value=480,  # 8 hours
        default=60
    )
    require_2fa = serializers.BooleanField(default=False)
    ip_whitelist = serializers.ListField(
        child=serializers.IPAddressField(),
        required=False,
        default=list
    )


class DataPoliciesSerializer(serializers.Serializer):
    """Serializer for data policies"""
    retention_days = serializers.IntegerField(
        min_value=30,
        max_value=3650,  # 10 years
        default=365
    )
    backup_frequency = serializers.ChoiceField(
        choices=['hourly', 'daily', 'weekly', 'monthly'],
        default='daily'
    )
    auto_archive_days = serializers.IntegerField(
        min_value=30,
        max_value=365,
        default=90
    )
    export_formats = serializers.ListField(
        child=serializers.ChoiceField(
            choices=['csv', 'json', 'excel', 'pdf']
        ),
        default=lambda: ['csv', 'json', 'excel']
    )


class TenantSettingsSerializer(serializers.ModelSerializer):
    """Main serializer for tenant settings"""
    
    # Nested serializers for JSON fields
    localization_settings = LocalizationSettingsSerializer(required=False)
    branding_settings = BrandingSettingsSerializer(required=False)
    security_policies = SecurityPoliciesSerializer(required=False)
    data_policies = DataPoliciesSerializer(required=False)
    
    # Read-only fields
    name = serializers.CharField(read_only=True)
    created_on = serializers.DateTimeField(read_only=True)
    
    # Usage statistics (computed fields)
    current_users = serializers.SerializerMethodField()
    storage_usage_mb = serializers.SerializerMethodField()
    api_calls_this_month = serializers.SerializerMethodField()
    
    class Meta:
        model = Tenant
        fields = [
            # Basic info
            'id', 'name', 'created_on',
            
            # Organization profile
            'organization_logo', 'organization_description', 'organization_website',
            'support_email', 'support_phone', 'business_hours',
            
            # Settings
            'localization_settings', 'branding_settings',
            'security_policies', 'data_policies',
            
            # Limits and usage
            'max_users', 'current_users',
            'features_enabled', 'billing_settings',
            'ai_enabled', 'ai_usage_limit', 'ai_current_usage',
            'storage_usage_mb', 'api_calls_this_month'
        ]
    
    def get_current_users(self, obj):
        """Get current user count for this tenant"""
        # Count users in the tenant schema
        with schema_context(obj.schema_name):
            return User.objects.filter(is_active=True).count()
    
    def get_storage_usage_mb(self, obj):
        """Calculate storage usage for this tenant"""
        # TODO: Implement actual storage calculation
        # For now, return a placeholder
        return 0
    
    def get_api_calls_this_month(self, obj):
        """Get API call count for current month"""
        # TODO: Implement API call tracking
        # For now, return a placeholder
        return 0
    
    def validate_password_min_length(self, value):
        """Ensure password min length is reasonable"""
        if value < 8:
            raise serializers.ValidationError("Password minimum length must be at least 8")
        if value > 32:
            raise serializers.ValidationError("Password minimum length cannot exceed 32")
        return value
    
    def validate_session_timeout_minutes(self, value):
        """Ensure session timeout is reasonable"""
        if value < 15:
            raise serializers.ValidationError("Session timeout must be at least 15 minutes")
        if value > 480:
            raise serializers.ValidationError("Session timeout cannot exceed 8 hours")
        return value


class TenantLogoUploadSerializer(serializers.ModelSerializer):
    """Serializer for logo upload"""
    
    organization_logo = serializers.ImageField(required=True)
    
    class Meta:
        model = Tenant
        fields = ['organization_logo']
    
    def validate_organization_logo(self, value):
        """Validate uploaded logo"""
        # Check file size (max 5MB)
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Logo file size cannot exceed 5MB")
        
        # Check file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/svg+xml']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
            )
        
        return value


class TenantUsageSerializer(serializers.Serializer):
    """Serializer for tenant usage statistics"""
    
    # User statistics
    current_users = serializers.IntegerField()
    max_users = serializers.IntegerField()
    user_percentage = serializers.FloatField()
    
    # Storage statistics  
    storage_used_mb = serializers.IntegerField()
    storage_limit_mb = serializers.IntegerField()
    storage_percentage = serializers.FloatField()
    
    # AI usage
    ai_usage_current = serializers.DecimalField(max_digits=10, decimal_places=2)
    ai_usage_limit = serializers.DecimalField(max_digits=10, decimal_places=2)
    ai_usage_percentage = serializers.FloatField()
    
    # API usage
    api_calls_today = serializers.IntegerField()
    api_calls_this_month = serializers.IntegerField()
    api_calls_limit_monthly = serializers.IntegerField()
    
    # Plan information
    plan_name = serializers.CharField()
    plan_tier = serializers.CharField()
    billing_cycle = serializers.CharField()
    next_billing_date = serializers.DateField()