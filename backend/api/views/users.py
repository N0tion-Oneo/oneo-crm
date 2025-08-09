"""
API views for user management and USER field autocomplete
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.db.models import Q
from api.serializers import UserSerializer
from authentication.permissions import SyncPermissionManager
from pipelines.models import Pipeline

User = get_user_model()


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for user data access - read-only for USER field autocomplete
    Filters users based on pipeline access permissions
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter users based on tenant and user permissions"""
        return User.objects.filter(
            is_active=True
        ).order_by('first_name', 'last_name', 'email')
    
    def get_pipeline_accessible_users(self, pipeline_id):
        """Get users who have access to a specific pipeline"""
        # Get all active users
        all_users = self.get_queryset()
        accessible_users = []
        
        for user in all_users:
            permission_manager = SyncPermissionManager(user)
            
            # Check if user has any access to the pipeline (read, create, update)
            has_read_access = permission_manager.has_permission('action', 'records', 'read', str(pipeline_id))
            has_create_access = permission_manager.has_permission('action', 'records', 'create', str(pipeline_id))
            has_update_access = permission_manager.has_permission('action', 'records', 'update', str(pipeline_id))
            
            # User is assignable if they can at least read records in the pipeline
            if has_read_access or has_create_access or has_update_access:
                accessible_users.append(user)
        
        return accessible_users
    
    @action(detail=False, methods=['get'])
    def autocomplete(self, request):
        """
        Autocomplete endpoint for USER fields
        Supports search by name, email with filtering options
        IMPORTANT: Filters users based on pipeline access permissions
        """
        # Get pipeline context - critical for permission filtering
        pipeline_id = request.query_params.get('pipeline_id')
        if not pipeline_id:
            return Response({
                'error': 'pipeline_id parameter is required for user autocomplete'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate pipeline exists and user has access to it
        try:
            pipeline = Pipeline.objects.get(id=pipeline_id)
            permission_manager = SyncPermissionManager(request.user)
            
            # Check if requesting user has access to the pipeline
            if not permission_manager.has_permission('action', 'pipelines', 'read', str(pipeline_id)):
                return Response({
                    'error': 'You do not have access to this pipeline'
                }, status=status.HTTP_403_FORBIDDEN)
        
        except Pipeline.DoesNotExist:
            return Response({
                'error': 'Pipeline not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get search query
        query = request.query_params.get('q', '').strip()
        
        # Get filtering options from USER field configuration
        restrict_to_user_types = request.query_params.getlist('restrict_to_user_types', [])
        user_types = request.query_params.getlist('user_types', [])
        exclude_user_types = request.query_params.getlist('exclude_user_types', [])
        departments = request.query_params.getlist('departments', [])
        
        # Limit results
        limit = min(int(request.query_params.get('limit', 20)), 100)
        
        # CRITICAL: Only show users who have access to the pipeline
        accessible_users = self.get_pipeline_accessible_users(pipeline_id)
        user_ids = [user.id for user in accessible_users]
        
        # Build queryset filtered by pipeline access
        queryset = self.get_queryset().filter(id__in=user_ids)
        
        # Apply search if provided
        if query and len(query) >= 2:  # Minimum search length
            search_filter = Q(
                first_name__icontains=query
            ) | Q(
                last_name__icontains=query
            ) | Q(
                email__icontains=query
            )
            
            # Include combined name search
            if ' ' in query:
                name_parts = query.split(' ', 1)
                search_filter |= Q(
                    first_name__icontains=name_parts[0],
                    last_name__icontains=name_parts[1]
                ) | Q(
                    first_name__icontains=name_parts[1],
                    last_name__icontains=name_parts[0]
                )
            
            queryset = queryset.filter(search_filter)
        
        # Apply user type filters - prioritize restrict_to_user_types from USER field config
        if restrict_to_user_types:
            queryset = queryset.filter(user_type__name__in=restrict_to_user_types)
        elif user_types:  # Fallback to legacy user_types parameter
            queryset = queryset.filter(user_type__name__in=user_types)
        
        if exclude_user_types:
            queryset = queryset.exclude(user_type__name__in=exclude_user_types)
        
        # Apply department filters (if user model has department field)
        if departments and hasattr(User, 'department'):
            queryset = queryset.filter(department__in=departments)
        
        # Limit results
        queryset = queryset[:limit]
        
        # Serialize results
        serializer = self.get_serializer(queryset, many=True)
        
        # Format for frontend autocomplete
        results = []
        for user_data in serializer.data:
            results.append({
                'user_id': user_data['id'],
                'name': user_data['name'] or f"{user_data['first_name']} {user_data['last_name']}".strip(),
                'email': user_data['email'],
                'first_name': user_data['first_name'],
                'last_name': user_data['last_name'],
                'user_type': user_data['user_type'],
                'is_active': user_data['is_active'],
                # Add computed display fields
                'display_name': user_data['name'] or f"{user_data['first_name']} {user_data['last_name']}".strip(),
                'display_email': user_data['email'],
                'avatar_url': None,  # Placeholder for future avatar support
            })
        
        return Response({
            'results': results,
            'count': len(results),
            'has_more': len(results) == limit,
            'query': query,
            'pipeline_id': pipeline_id,
            'total_accessible_users': len(accessible_users),
            'filters_applied': {
                'restrict_to_user_types': restrict_to_user_types,
                'user_types': user_types,
                'exclude_user_types': exclude_user_types,
                'departments': departments,
                'pipeline_access_filtered': True,
            }
        })
    
    @action(detail=False, methods=['get'])
    def available_for_assignment(self, request):
        """
        Get users available for assignment based on USER field configuration
        Supports all filtering options from UserFieldConfig
        IMPORTANT: Requires pipeline_id and filters based on pipeline access permissions
        """
        # Get pipeline context - critical for permission filtering
        pipeline_id = request.query_params.get('pipeline_id')
        if not pipeline_id:
            return Response({
                'error': 'pipeline_id parameter is required for user assignment'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate pipeline exists and user has access to it
        try:
            pipeline = Pipeline.objects.get(id=pipeline_id)
            permission_manager = SyncPermissionManager(request.user)
            
            # Check if requesting user has access to the pipeline
            if not permission_manager.has_permission('action', 'pipelines', 'read', str(pipeline_id)):
                return Response({
                    'error': 'You do not have access to this pipeline'
                }, status=status.HTTP_403_FORBIDDEN)
        
        except Pipeline.DoesNotExist:
            return Response({
                'error': 'Pipeline not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get filtering parameters
        restrict_to_user_types = request.query_params.getlist('restrict_to_user_types', [])
        exclude_user_types = request.query_params.getlist('exclude_user_types', [])
        restrict_to_departments = request.query_params.getlist('restrict_to_departments', [])
        allow_external_users = request.query_params.get('allow_external_users', 'true').lower() == 'true'
        
        # CRITICAL: Only show users who have access to the pipeline
        accessible_users = self.get_pipeline_accessible_users(pipeline_id)
        user_ids = [user.id for user in accessible_users]
        
        # Build queryset filtered by pipeline access
        queryset = self.get_queryset().filter(id__in=user_ids)
        
        # Apply user type restrictions
        if restrict_to_user_types:
            queryset = queryset.filter(user_type__name__in=restrict_to_user_types)
        
        if exclude_user_types:
            queryset = queryset.exclude(user_type__name__in=exclude_user_types)
        
        # Apply department restrictions (if applicable)
        if restrict_to_departments and hasattr(User, 'department'):
            queryset = queryset.filter(department__in=restrict_to_departments)
        
        # Apply external user restrictions (if applicable)
        if not allow_external_users and hasattr(User, 'is_external'):
            queryset = queryset.filter(is_external=False)
        
        # Serialize results
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'users': serializer.data,
            'count': len(serializer.data),
            'pipeline_id': pipeline_id,
            'total_accessible_users': len(accessible_users),
            'filters_applied': {
                'restrict_to_user_types': restrict_to_user_types,
                'exclude_user_types': exclude_user_types,
                'restrict_to_departments': restrict_to_departments,
                'allow_external_users': allow_external_users,
                'pipeline_access_filtered': True,
            }
        })
    
    @action(detail=False, methods=['get'])
    def user_types(self, request):
        """Get available user types for filtering"""
        from authentication.models import UserType
        
        user_types = UserType.objects.all().values('name', 'slug', 'description')
        
        return Response({
            'user_types': list(user_types)
        })
    
    @action(detail=False, methods=['get'])
    def departments(self, request):
        """Get available departments for filtering (if applicable)"""
        if not hasattr(User, 'department'):
            return Response({
                'departments': [],
                'message': 'Department field not available in user model'
            })
        
        departments = User.objects.values_list('department', flat=True).distinct()
        departments = [dept for dept in departments if dept]  # Filter out None/empty values
        
        return Response({
            'departments': sorted(departments)
        })
    
    def retrieve(self, request, pk=None):
        """
        Get detailed user information for USER fields
        IMPORTANT: Should validate pipeline access when used in USER field context
        """
        try:
            # Check if pipeline_id is provided for permission validation
            pipeline_id = request.query_params.get('pipeline_id')
            
            user = self.get_queryset().get(pk=pk)
            
            # If pipeline_id provided, validate the user has access to that pipeline
            if pipeline_id:
                try:
                    pipeline = Pipeline.objects.get(id=pipeline_id)
                    permission_manager = SyncPermissionManager(request.user)
                    
                    # Check if requesting user has access to the pipeline
                    if not permission_manager.has_permission('action', 'pipelines', 'read', str(pipeline_id)):
                        return Response({
                            'error': 'You do not have access to this pipeline'
                        }, status=status.HTTP_403_FORBIDDEN)
                    
                    # Check if the requested user has access to the pipeline
                    accessible_users = self.get_pipeline_accessible_users(pipeline_id)
                    if user not in accessible_users:
                        return Response({
                            'error': 'User does not have access to the specified pipeline'
                        }, status=status.HTTP_403_FORBIDDEN)
                
                except Pipeline.DoesNotExist:
                    return Response({
                        'error': 'Pipeline not found'
                    }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = self.get_serializer(user)
            
            # Add additional details for USER field display
            user_data = serializer.data.copy()
            user_data.update({
                'display_name': user_data['name'] or f"{user_data['first_name']} {user_data['last_name']}".strip(),
                'display_email': user_data['email'],
                'avatar_url': None,  # Placeholder for future avatar support
                'online_status': 'unknown',  # Placeholder for future online status
                'job_title': None,  # Placeholder for future job title field
                'pipeline_accessible': pipeline_id is not None,  # Indicates if pipeline access was verified
            })
            
            return Response(user_data)
        
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )