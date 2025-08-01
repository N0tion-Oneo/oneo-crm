"""
Authentication API views
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema

from api.serializers import UserSerializer, UserTypeSerializer
from authentication.models import UserType
from authentication.permissions import AsyncPermissionManager as PermissionManager

User = get_user_model()


class AuthViewSet(viewsets.ViewSet):
    """
    Authentication and user profile management
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Get current user profile",
        description="Retrieve the current authenticated user's profile"
    )
    @action(detail=False, methods=['get'])
    def profile(self, request):
        """Get current user profile"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Update user profile",
        description="Update the current user's profile information"
    )
    @action(detail=False, methods=['patch'])
    def update_profile(self, request):
        """Update user profile"""
        serializer = UserSerializer(
            request.user, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Get user permissions",
        description="Retrieve the current user's permissions"
    )
    @action(detail=False, methods=['get'])
    def permissions(self, request):
        """Get user permissions"""
        permission_manager = PermissionManager(request.user)
        permissions_data = permission_manager.get_user_permissions()
        
        return Response({
            'user_id': request.user.id,
            'user_type': request.user.user_type.name,
            'permissions': permissions_data
        })
    
    @extend_schema(
        summary="Check specific permission",
        description="Check if user has a specific permission",
        parameters=[
            {'name': 'resource_type', 'type': 'string', 'required': True},
            {'name': 'resource', 'type': 'string', 'required': True},
            {'name': 'action', 'type': 'string', 'required': True},
            {'name': 'resource_id', 'type': 'string', 'required': False}
        ]
    )
    @action(detail=False, methods=['get'])
    def check_permission(self, request):
        """Check specific permission"""
        resource_type = request.query_params.get('resource_type')
        resource = request.query_params.get('resource')
        action = request.query_params.get('action')
        resource_id = request.query_params.get('resource_id')
        
        if not all([resource_type, resource, action]):
            return Response(
                {'error': 'resource_type, resource, and action are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        permission_manager = PermissionManager(request.user)
        has_permission = permission_manager.has_permission(
            resource_type, resource, action, resource_id
        )
        
        return Response({
            'has_permission': has_permission,
            'resource_type': resource_type,
            'resource': resource,
            'action': action,
            'resource_id': resource_id
        })
    
    @extend_schema(
        summary="Get user types",
        description="Retrieve all available user types"
    )
    @action(detail=False, methods=['get'])
    def user_types(self, request):
        """Get available user types"""
        user_types = UserType.objects.all()
        serializer = UserTypeSerializer(user_types, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Get tenant information",
        description="Retrieve current tenant information"
    )
    @action(detail=False, methods=['get'])
    def tenant_info(self, request):
        """Get current tenant info"""
        from django_tenants.utils import tenant_context
        from tenants.models import Tenant
        
        try:
            current_tenant = request.tenant
            return Response({
                'tenant_id': current_tenant.id,
                'schema_name': current_tenant.schema_name,
                'name': current_tenant.name,
                'domain': current_tenant.domains.first().domain if current_tenant.domains.exists() else None,
                'created_on': current_tenant.created_on,
                'is_active': True
            })
        except Exception as e:
            return Response(
                {'error': 'Could not retrieve tenant information'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )