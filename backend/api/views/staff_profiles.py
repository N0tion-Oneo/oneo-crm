"""
ViewSet for staff profile management with permission-based field filtering
"""
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count
from django_filters.rest_framework import DjangoFilterBackend
from authentication.models import StaffProfile
from authentication.serializers import (
    StaffProfileSerializer,
    StaffProfilePublicSerializer,
    StaffProfileCreateSerializer,
    StaffProfileSummarySerializer
)
from authentication.permissions import SyncPermissionManager
from api.permissions.staff import StaffProfilePermission


class StaffProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing staff profiles with permission-based access control.
    
    Field visibility is dynamically controlled based on user permissions:
    - Own profile: Full access (except admin fields)
    - Direct reports: Extended access for managers
    - Others: Public fields only
    - HR/Admin: Full access including sensitive fields
    """
    
    permission_classes = [permissions.IsAuthenticated, StaffProfilePermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['department', 'employment_status', 'employment_type', 'work_location']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 
                     'employee_id', 'job_title', 'department']
    ordering_fields = ['employee_id', 'user__first_name', 'user__last_name', 
                      'department', 'start_date']
    ordering = ['employee_id']
    
    def get_queryset(self):
        """
        Filter queryset based on user permissions.
        """
        user = self.request.user
        permission_manager = SyncPermissionManager(user)
        
        # Start with all profiles, properly prefetch related data
        queryset = StaffProfile.objects.select_related(
            'user', 'user__user_type', 'reporting_manager', 'created_by'
        ).prefetch_related('user__direct_reports')
        
        # Admins and those with read_all permission see everything
        if permission_manager.has_permission('action', 'staff_profiles', 'read_all'):
            return queryset
        
        # Managers see their own profile and their direct reports
        if hasattr(user, 'staff_profile') and user.staff_profile.is_manager:
            return queryset.filter(
                Q(user=user) | Q(reporting_manager=user)
            )
        
        # Regular users only see their own profile
        return queryset.filter(user=user)
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action and permissions.
        """
        if self.action == 'create':
            return StaffProfileCreateSerializer
        elif self.action == 'list':
            # Use summary serializer for list views
            return StaffProfileSummarySerializer
        else:
            # For detail views, we'll use the full serializer but filter fields
            return StaffProfileSerializer
    
    def get_serializer(self, *args, **kwargs):
        """
        Get serializer with field filtering based on permissions.
        """
        serializer_class = self.get_serializer_class()
        kwargs.setdefault('context', self.get_serializer_context())
        serializer = serializer_class(*args, **kwargs)
        
        # For retrieve/update actions, filter fields based on permissions
        if self.action in ['retrieve', 'update', 'partial_update'] and hasattr(self, 'get_object'):
            try:
                instance = self.get_object() if not args else args[0]
                if instance and isinstance(instance, StaffProfile):
                    # Use the permission class to filter fields
                    StaffProfilePermission.filter_serializer_fields(
                        serializer, self.request.user, instance
                    )
            except:
                # If we can't get the object, return the serializer as-is
                pass
        
        return serializer
    
    def perform_create(self, serializer):
        """
        Set created_by when creating a new profile.
        """
        serializer.save(created_by=self.request.user)
    
    def update(self, request, *args, **kwargs):
        """
        Override update to provide better error reporting
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Clean the data - convert empty strings to appropriate values
        cleaned_data = {}
        
        for key, value in request.data.items():
            if value == '' or value is None:
                # These fields should be None when empty (nullable fields)
                if key in ['linkedin_profile', 'personal_email', 'emergency_contact_name', 
                          'emergency_contact_phone', 'emergency_contact_relationship', 
                          'nationality', 'internal_notes', 'employee_id']:
                    cleaned_data[key] = None
                # These fields can be empty strings
                elif key in ['job_title', 'department', 'office_location', 
                            'work_phone_extension', 'bio']:
                    cleaned_data[key] = ''
                # Date fields should be None when empty
                elif key in ['start_date', 'end_date', 'date_of_birth', 'reporting_manager']:
                    cleaned_data[key] = None
                # JSON fields
                elif key in ['professional_links', 'education', 'home_address']:
                    cleaned_data[key] = {}
                else:
                    cleaned_data[key] = value
            elif key == 'education':
                # Handle education field - can be array or dict
                if isinstance(value, list):
                    # Convert array to dict format if needed
                    if value:
                        # Store as dict with indexed keys for compatibility
                        cleaned_data[key] = {str(i): edu for i, edu in enumerate(value)}
                    else:
                        cleaned_data[key] = {}
                else:
                    cleaned_data[key] = value
            elif key == 'home_address':
                # Ensure home_address is a proper dict
                if isinstance(value, dict):
                    # Check if all values are empty strings
                    if all(v == '' for v in value.values()):
                        cleaned_data[key] = {}
                    else:
                        cleaned_data[key] = value
                else:
                    cleaned_data[key] = {}
            elif key == 'date_of_birth' and value == '':
                cleaned_data[key] = None
            elif key == 'end_date' and value == '':
                cleaned_data[key] = None
            else:
                cleaned_data[key] = value
        
        serializer = self.get_serializer(instance, data=cleaned_data, partial=partial)
        
        # Validate and provide detailed error messages
        if not serializer.is_valid():
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Staff profile validation errors: {serializer.errors}")
            logger.error(f"Request data: {cleaned_data}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        self.perform_update(serializer)
        
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}
        
        return Response(serializer.data)
    
    def perform_update(self, serializer):
        """
        Update the staff profile with appropriate permission checks.
        """
        instance = self.get_object()
        user = self.request.user
        permission_manager = SyncPermissionManager(user)
        
        # Determine which fields the user can update based on their relationship
        is_own_profile = instance.user == user
        is_manager = instance.reporting_manager == user
        
        # Get the validated data from the serializer
        validated_data = serializer.validated_data
        
        # Define which fields can be updated based on permissions
        updatable_fields = set()
        
        if is_own_profile:
            # Users can update most of their own fields except admin fields
            updatable_fields = {
                'job_title', 'department', 'work_location', 'office_location',
                'work_phone_extension', 'education', 'bio',
                'linkedin_profile', 'professional_links', 'emergency_contact_name',
                'emergency_contact_phone', 'emergency_contact_relationship',
                'personal_email', 'home_address', 'date_of_birth', 'nationality'
            }
        
        # Check for broader update permissions
        if permission_manager.has_permission('action', 'staff_profiles', 'update_all'):
            # Admin/HR can update all fields
            updatable_fields = set(validated_data.keys())
            # Remove read-only fields that shouldn't be updated
            updatable_fields.discard('user')  # Can't change the user association
            updatable_fields.discard('created_by')
            updatable_fields.discard('created_at')
            updatable_fields.discard('updated_at')
        elif is_manager and permission_manager.has_permission('action', 'staff_profiles', 'update'):
            # Managers can update limited fields for their direct reports
            updatable_fields.update({
                'job_title', 'department', 'employment_type', 'employment_status',
                'work_location', 'office_location', 'work_phone_extension'
            })
        
        # Filter validated data to only include updatable fields
        filtered_data = {
            field: value for field, value in validated_data.items() 
            if field in updatable_fields
        }
        
        # Log the update for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"User {user.email} updating StaffProfile {instance.id}")
        logger.info(f"Allowed fields: {list(updatable_fields)}")
        logger.info(f"Requested fields: {list(validated_data.keys())}")
        logger.info(f"Updating fields: {list(filtered_data.keys())}")
        
        # Update instance fields with filtered data
        for field, value in filtered_data.items():
            setattr(instance, field, value)
        
        # Save the instance
        instance.save(update_fields=list(filtered_data.keys()) if filtered_data else None)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Get current user's staff profile.
        """
        try:
            profile = StaffProfile.objects.get(user=request.user)
            serializer = StaffProfileSerializer(profile)
            # User can see all fields of their own profile (except admin fields)
            StaffProfilePermission.filter_serializer_fields(
                serializer, request.user, profile
            )
            return Response(serializer.data)
        except StaffProfile.DoesNotExist:
            return Response(
                {'error': 'You do not have a staff profile'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def my_team(self, request):
        """
        Get direct reports for the current user (managers only).
        """
        try:
            # Check if user is a manager
            if not hasattr(request.user, 'staff_profile'):
                return Response(
                    {'error': 'You do not have a staff profile'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            profile = request.user.staff_profile
            if not profile.is_manager:
                return Response(
                    {'error': 'You are not a manager'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get direct reports
            direct_reports = StaffProfile.objects.filter(
                reporting_manager=request.user
            ).select_related('user', 'user__user_type')
            
            # Use public serializer for team members
            serializer = StaffProfilePublicSerializer(direct_reports, many=True)
            return Response(serializer.data)
            
        except StaffProfile.DoesNotExist:
            return Response(
                {'error': 'You do not have a staff profile'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def reporting_chain(self, request, pk=None):
        """
        Get the reporting chain for a staff member.
        """
        profile = self.get_object()
        
        # Check permissions - users can see their own chain, managers can see their reports' chains
        permission_manager = SyncPermissionManager(request.user)
        is_own = profile.user == request.user
        is_manager = profile.reporting_manager == request.user
        has_read_all = permission_manager.has_permission('action', 'staff_profiles', 'read_all')
        
        if not (is_own or is_manager or has_read_all):
            return Response(
                {'error': 'You do not have permission to view this reporting chain'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get the reporting chain
        chain = profile.get_reporting_chain()
        serializer = StaffProfilePublicSerializer(chain, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def departments(self, request):
        """
        Get list of all departments (for filtering).
        """
        departments = StaffProfile.objects.values_list(
            'department', flat=True
        ).distinct().exclude(department='')
        return Response(list(departments))
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        """
        Export staff profiles to CSV (admin only).
        """
        permission_manager = SyncPermissionManager(request.user)
        if not permission_manager.has_permission('action', 'staff_profiles', 'update_sensitive'):
            return Response(
                {'error': 'You do not have permission to export staff profiles'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get all profiles
        profiles = self.get_queryset()
        
        # Create CSV response
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="staff_profiles.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Employee ID', 'Full Name', 'Email', 'Job Title', 'Department',
            'Employment Type', 'Employment Status', 'Start Date', 'Manager'
        ])
        
        for profile in profiles:
            writer.writerow([
                profile.employee_id,
                profile.user.get_full_name(),
                profile.user.email,
                profile.job_title,
                profile.department,
                profile.get_employment_type_display(),
                profile.get_employment_status_display(),
                profile.start_date,
                profile.reporting_manager.get_full_name() if profile.reporting_manager else ''
            ])
        
        return response