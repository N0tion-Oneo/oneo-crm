"""
Tenant management views and registration API
"""

import logging
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django_tenants.utils import schema_context
from asgiref.sync import sync_to_async

from .models import Tenant, Domain
from .serializers import TenantRegistrationSerializer, TenantSerializer
from authentication.session_utils import AsyncSessionManager
from authentication.serializers import UserSerializer

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
