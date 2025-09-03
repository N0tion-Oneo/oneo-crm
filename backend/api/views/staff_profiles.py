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
    
    def perform_update(self, serializer):
        """
        Filter out fields user doesn't have permission to update.
        """
        instance = self.get_object()
        allowed_fields = StaffProfilePermission.get_allowed_fields(
            self.request.user, instance
        )
        
        # Filter validated data to only include allowed fields
        filtered_data = {
            k: v for k, v in serializer.validated_data.items()
            if k in allowed_fields
        }
        
        # Update the instance with filtered data
        for attr, value in filtered_data.items():
            setattr(instance, attr, value)
        instance.save()
    
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