"""
Tenant management views and registration API
"""

import logging
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status, viewsets, mixins
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from django_tenants.utils import schema_context
from asgiref.sync import sync_to_async
from datetime import datetime, timedelta
from decimal import Decimal

from .models import Tenant, Domain
from .serializers import (
    TenantRegistrationSerializer, 
    TenantSerializer,
    TenantSettingsSerializer, 
    TenantLogoUploadSerializer,
    TenantUsageSerializer,
    LocalizationSettingsSerializer,
    BrandingSettingsSerializer,
    SecurityPoliciesSerializer,
    DataPoliciesSerializer
)
from authentication.session_utils import AsyncSessionManager
from authentication.serializers import UserSerializer
from authentication.permissions import SyncPermissionManager

logger = logging.getLogger(__name__)
User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
def register_tenant(request):
    """
    Tenant registration endpoint for new organization signup
    Creates tenant, domain, and first customer admin user
    Leverages existing signals for automatic Oneo team setup
    """
    try:
        serializer = TenantRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid input', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create tenant, domain, and admin user
        # This leverages the existing signal infrastructure
        result = serializer.save()
        
        tenant = result['tenant']
        admin_user = result['admin_user']
        domain = result['domain']
        
        # Switch to tenant context for session creation and user data
        with schema_context(tenant.schema_name):
            # Update user's last activity
            admin_user.last_activity = timezone.now()
            admin_user.save(update_fields=['last_activity'])
            
            # Create session for auto-login after registration
            session_manager = AsyncSessionManager()
            
            # Create session data synchronously for now
            from django.contrib.sessions.models import Session
            from django.contrib.sessions.backends.db import SessionStore
            import uuid
            
            # Create session
            session = SessionStore()
            session['_auth_user_id'] = str(admin_user.id)
            session['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
            session.save()
            
            # Get user data within tenant context
            user_serializer = UserSerializer(admin_user)
            user_data = user_serializer.data
        
        # Prepare response data with tenant info
        tenant_serializer = TenantSerializer(tenant)
        tenant_data = tenant_serializer.data
        
        response_data = {
            'message': 'Organization created successfully',
            'tenant': tenant_data,
            'user': user_data,
            'session': {
                'session_key': session.session_key,
                'expires_at': session.get_expiry_date().isoformat() if session.get_expiry_date() else None
            },
            'redirect_url': f"http://{domain.domain}:3000/dashboard"
        }

        logger.info(f"Tenant registered successfully: {tenant.name} ({tenant.schema_name})")
        logger.info(f"Customer admin user created: {admin_user.email}")

        return Response(response_data, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Tenant registration error: {e}")
        return Response(
            {'error': 'Registration failed', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def check_subdomain_availability(request):
    """
    Check if a subdomain is available for registration
    """
    subdomain = request.GET.get('subdomain', '').lower().strip()
    
    if not subdomain:
        return Response(
            {'error': 'Subdomain parameter is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Use the serializer's validation logic
        serializer = TenantRegistrationSerializer()
        
        try:
            validated_subdomain = serializer.validate_subdomain(subdomain)
            return Response({
                'available': True,
                'subdomain': validated_subdomain,
                'domain': f"{validated_subdomain}.localhost"
            })
        except Exception as e:
            return Response({
                'available': False,
                'subdomain': subdomain,
                'error': str(e)
            })
    
    except Exception as e:
        logger.error(f"Subdomain check error: {e}")
        return Response(
            {'error': 'Failed to check subdomain availability'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class TenantSettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tenant settings
    Only tenant admins can access these endpoints
    This is a singleton resource - only one settings object per tenant
    We use 'current' as the pk for all operations
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TenantSettingsSerializer
    queryset = Tenant.objects.none()  # We override get_object anyway
    http_method_names = ['get', 'patch', 'post', 'head', 'options']  # No DELETE or PUT
    
    def list(self, request, *args, **kwargs):
        """List redirects to retrieve for singleton"""
        return Response(
            {"error": "Use /api/v1/tenant-settings/current/ to access settings"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    def create(self, request, *args, **kwargs):
        """Cannot create settings - they exist per tenant"""
        return Response(
            {"error": "Settings are automatically created per tenant"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def destroy(self, request, *args, **kwargs):
        """Cannot delete settings"""
        return Response(
            {"error": "Settings cannot be deleted"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def get_object(self):
        """Always return the current tenant as the object, ignoring the pk"""
        if hasattr(self.request, 'tenant'):
            return self.request.tenant
        return None
    
    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to check permissions"""
        instance = self.get_object()
        if not instance:
            return Response(
                {"error": "Tenant not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permissions - anyone can read basic settings
        permission_manager = SyncPermissionManager(request.user)
        if not permission_manager.has_permission('actions', 'settings', 'read'):
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """Override update to check admin permissions"""
        # Check admin permissions
        permission_manager = SyncPermissionManager(request.user)
        if not (permission_manager.has_permission('actions', 'system', 'full_access') or
                permission_manager.has_permission('actions', 'settings', 'update')):
            return Response(
                {"error": "Admin permission required"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        if not instance:
            return Response(
                {"error": "Tenant not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_logo(self, request, pk=None):
        """
        POST /api/v1/tenant/settings/upload_logo/
        Upload tenant logo
        """
        tenant = self.get_current_tenant()
        if not tenant:
            return Response(
                {"error": "Tenant not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check admin permissions
        if not self.check_admin_permission(request):
            return Response(
                {"error": "Admin permission required"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = TenantLogoUploadSerializer(
            tenant,
            data=request.data
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Logo uploaded successfully",
                "logo_url": tenant.organization_logo.url if tenant.organization_logo else None
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def usage(self, request, pk=None):
        """
        GET /api/v1/tenant/settings/usage/
        Get tenant usage statistics
        """
        tenant = self.get_current_tenant()
        if not tenant:
            return Response(
                {"error": "Tenant not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Calculate usage statistics
        with schema_context(tenant.schema_name):
            current_users = User.objects.filter(is_active=True).count()
        
        # Calculate percentages
        user_percentage = (current_users / tenant.max_users * 100) if tenant.max_users > 0 else 0
        
        # Storage (placeholder values for now)
        storage_used_mb = 250  # TODO: Implement actual calculation
        storage_limit_mb = 5000  # 5GB default
        storage_percentage = (storage_used_mb / storage_limit_mb * 100)
        
        # AI usage
        ai_usage_percentage = float(
            (tenant.ai_current_usage / tenant.ai_usage_limit * 100)
            if tenant.ai_usage_limit > 0 else 0
        )
        
        # API usage (placeholder values)
        api_calls_today = 150
        api_calls_this_month = 3500
        api_calls_limit_monthly = 10000
        
        # Plan information (from billing_settings or defaults)
        billing_settings = tenant.billing_settings or {}
        plan_name = billing_settings.get('plan_name', 'Starter')
        plan_tier = billing_settings.get('plan_tier', 'basic')
        billing_cycle = billing_settings.get('billing_cycle', 'monthly')
        
        # Calculate next billing date (first of next month for now)
        today = timezone.now().date()
        if today.month == 12:
            next_billing = datetime(today.year + 1, 1, 1).date()
        else:
            next_billing = datetime(today.year, today.month + 1, 1).date()
        
        usage_data = {
            'current_users': current_users,
            'max_users': tenant.max_users,
            'user_percentage': round(user_percentage, 1),
            'storage_used_mb': storage_used_mb,
            'storage_limit_mb': storage_limit_mb,
            'storage_percentage': round(storage_percentage, 1),
            'ai_usage_current': tenant.ai_current_usage,
            'ai_usage_limit': tenant.ai_usage_limit,
            'ai_usage_percentage': round(ai_usage_percentage, 1),
            'api_calls_today': api_calls_today,
            'api_calls_this_month': api_calls_this_month,
            'api_calls_limit_monthly': api_calls_limit_monthly,
            'plan_name': plan_name,
            'plan_tier': plan_tier,
            'billing_cycle': billing_cycle,
            'next_billing_date': next_billing
        }
        
        serializer = TenantUsageSerializer(data=usage_data)
        serializer.is_valid(raise_exception=True)
        
        return Response(serializer.data)
