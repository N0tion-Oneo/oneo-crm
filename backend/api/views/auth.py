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
from authentication.permissions_registry import (
    get_complete_permission_schema, 
    get_permission_matrix_configuration,
    get_dynamic_tenant_permissions,
    get_permission_registry_info
)
from authentication.permission_matrix import PermissionMatrixManager
from django.utils import timezone

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
    
    @extend_schema(
        summary="Get dynamic permission schema",
        description="Retrieve complete permission schema including tenant-specific dynamic resources"
    )
    @action(detail=False, methods=['get'])
    def permission_schema(self, request):
        """Get complete dynamic permission schema for the tenant"""
        try:
            tenant = getattr(request, 'tenant', None)
            if not tenant:
                return Response(
                    {'error': 'Could not determine tenant context'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generate fresh schema
            schema = get_complete_permission_schema(tenant)
            
            return Response({
                'schema': schema,
                'tenant': tenant.schema_name
            })
        
        except Exception as e:
            return Response(
                {'error': f'Failed to generate permission schema: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Get permission matrix configuration",
        description="Retrieve permission matrix with UI configuration and grouping"
    )
    @action(detail=False, methods=['get'])
    def permission_matrix(self, request):
        """Get complete permission matrix configuration for frontend UI"""
        try:
            tenant = getattr(request, 'tenant', None)
            if not tenant:
                return Response(
                    {'error': 'Could not determine tenant context'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generate fresh matrix configuration
            matrix_config = get_permission_matrix_configuration(tenant)
            
            return Response({
                'matrix': matrix_config,
                'tenant': tenant.schema_name
            })
        
        except Exception as e:
            return Response(
                {'error': f'Failed to generate permission matrix: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    
    @extend_schema(
        summary="Get permission registry info",
        description="Retrieve permission registry metadata and statistics"
    )
    @action(detail=False, methods=['get'])
    def permission_info(self, request):
        """Get permission registry information and statistics"""
        try:
            # Get registry info
            registry_info = get_permission_registry_info()
            
            # Add tenant-specific info
            tenant = getattr(request, 'tenant', None)
            if tenant:
                try:
                    dynamic_perms = get_dynamic_tenant_permissions(tenant)
                    registry_info['tenant_dynamic_resources'] = {
                        'total_dynamic_permissions': len(dynamic_perms),
                        'pipelines': len([k for k in dynamic_perms.keys() if k.startswith('pipeline_')]),
                        'workflows': len([k for k in dynamic_perms.keys() if k.startswith('workflow_')]),
                        'forms': len([k for k in dynamic_perms.keys() if k.startswith('form_')])
                    }
                    registry_info['tenant_info'] = {
                        'schema_name': tenant.schema_name,
                        'name': tenant.name
                    }
                except Exception:
                    pass
            
            return Response(registry_info)
        
        except Exception as e:
            return Response(
                {'error': f'Failed to get registry info: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Get frontend matrix configuration",
        description="Retrieve enhanced permission matrix configuration with UI helpers and bulk operation templates"
    )
    @action(detail=False, methods=['get'])
    def frontend_matrix(self, request):
        """Get enhanced permission matrix configuration for frontend"""
        try:
            tenant = getattr(request, 'tenant', None)
            if not tenant:
                return Response(
                    {'error': 'Could not determine tenant context'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            matrix_manager = PermissionMatrixManager(tenant, request.user)
            config = matrix_manager.get_frontend_matrix_config()
            
            return Response(config)
        
        except Exception as e:
            return Response(
                {'error': f'Failed to get frontend matrix config: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Validate permission set",
        description="Validate a permission configuration for consistency and dependencies"
    )
    @action(detail=False, methods=['post'])
    def validate_permissions(self, request):
        """Validate a permission set for frontend use"""
        try:
            tenant = getattr(request, 'tenant', None)
            if not tenant:
                return Response(
                    {'error': 'Could not determine tenant context'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            permissions = request.data.get('permissions', {})
            if not permissions:
                return Response(
                    {'error': 'permissions field is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            matrix_manager = PermissionMatrixManager(tenant, request.user)
            validation_result = matrix_manager.validate_permission_set(permissions)
            
            return Response(validation_result)
        
        except Exception as e:
            return Response(
                {'error': f'Failed to validate permissions: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Apply bulk permission operation",
        description="Apply a bulk permission operation to a user type"
    )
    @action(detail=False, methods=['post'])
    def bulk_permission_operation(self, request):
        """Apply bulk permission operation to user type"""
        try:
            tenant = getattr(request, 'tenant', None)
            if not tenant:
                return Response(
                    {'error': 'Could not determine tenant context'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user_type_id = request.data.get('user_type_id')
            operation_name = request.data.get('operation_name')
            custom_permissions = request.data.get('custom_permissions')
            
            if not user_type_id:
                return Response(
                    {'error': 'user_type_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not operation_name and not custom_permissions:
                return Response(
                    {'error': 'operation_name or custom_permissions is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            matrix_manager = PermissionMatrixManager(tenant, request.user)
            result = matrix_manager.apply_bulk_operation(
                user_type_id, operation_name, custom_permissions
            )
            
            if result['success']:
                return Response(result)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        except PermissionError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to apply bulk operation: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Compare user type permissions",
        description="Compare permissions across multiple user types"
    )
    @action(detail=False, methods=['post'])
    def compare_user_types(self, request):
        """Compare permissions across multiple user types"""
        try:
            tenant = getattr(request, 'tenant', None)
            if not tenant:
                return Response(
                    {'error': 'Could not determine tenant context'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user_type_ids = request.data.get('user_type_ids', [])
            if not user_type_ids or len(user_type_ids) < 2:
                return Response(
                    {'error': 'At least 2 user_type_ids are required for comparison'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            matrix_manager = PermissionMatrixManager(tenant, request.user)
            comparison = matrix_manager.get_user_type_comparison(user_type_ids)
            
            return Response(comparison)
        
        except Exception as e:
            return Response(
                {'error': f'Failed to compare user types: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Get permission usage analytics",
        description="Retrieve analytics about permission usage in the tenant"
    )
    @action(detail=False, methods=['get'])
    def permission_analytics(self, request):
        """Get permission usage analytics for the tenant"""
        try:
            tenant = getattr(request, 'tenant', None)
            if not tenant:
                return Response(
                    {'error': 'Could not determine tenant context'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            matrix_manager = PermissionMatrixManager(tenant, request.user)
            analytics = matrix_manager.get_permission_usage_analytics()
            
            return Response(analytics)
        
        except Exception as e:
            return Response(
                {'error': f'Failed to get permission analytics: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    
    
