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