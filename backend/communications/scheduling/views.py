"""
Internal API views for scheduling management
Handles authenticated user operations for scheduling configuration
"""
import logging
from datetime import datetime, timedelta
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Q, Count
from drf_spectacular.utils import extend_schema, OpenApiParameter
from asgiref.sync import async_to_sync

from api.permissions.scheduling import (
    SchedulingPermission,
    SchedulingProfilePermission,
    MeetingTypePermission,
    ScheduledMeetingPermission,
    SchedulingLinkPermission,
    AvailabilityOverridePermission
)
from authentication.permissions import SyncPermissionManager
from communications.models import UserChannelConnection
from .models import (
    SchedulingProfile, MeetingType, SchedulingLink,
    ScheduledMeeting, AvailabilityOverride
)
from .serializers import (
    SchedulingProfileSerializer, MeetingTypeSerializer,
    SchedulingLinkSerializer, ScheduledMeetingSerializer,
    AvailabilityOverrideSerializer, AvailabilityRequestSerializer,
    MeetingCancellationSerializer, MeetingRescheduleSerializer
)
from .services import AvailabilityCalculator

logger = logging.getLogger(__name__)


class SchedulingProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user scheduling profiles
    Handles availability settings and calendar configuration
    """
    serializer_class = SchedulingProfileSerializer
    permission_classes = [permissions.IsAuthenticated, SchedulingProfilePermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['calendar_connection', 'is_active']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter profiles based on permissions"""
        permission_manager = SyncPermissionManager(self.request.user)
        
        if permission_manager.has_permission('action', 'communication_settings', 'scheduling_all', None):
            # Admin can see all profiles
            return SchedulingProfile.objects.all().select_related(
                'calendar_connection'
            ).prefetch_related('availability_overrides')
        elif permission_manager.has_permission('action', 'communication_settings', 'scheduling', None):
            # Users can only see their own profiles
            return SchedulingProfile.objects.filter(
                user=self.request.user
            ).select_related('calendar_connection').prefetch_related('availability_overrides')
        
        return SchedulingProfile.objects.none()
    
    def perform_create(self, serializer):
        """Set user to current user"""
        serializer.save(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Override create to add better error handling"""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Profile creation failed: {serializer.errors}")
            logger.error(f"Request data: {request.data}")
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(detail=False, methods=['get'])
    def calendar_connections(self, request):
        """Get available calendar connections for the current user"""
        connections = UserChannelConnection.objects.filter(
            user=request.user,
            channel_type__in=['calendar', 'gmail', 'outlook'],
            auth_status__in=['active', 'authenticated']  # Accept both statuses
        )
        
        data = [{
            'id': str(conn.id),
            'account_name': conn.account_name,
            'channel_type': conn.channel_type,
            'auth_status': conn.auth_status,
            'unipile_account_id': conn.unipile_account_id
        } for conn in connections]
        
        return Response({'connections': data})
    
    @action(detail=False, methods=['get'])
    def calendars_for_connection(self, request):
        """Get calendars for a specific connection"""
        connection_id = request.query_params.get('connection_id')
        if not connection_id:
            return Response(
                {'error': 'connection_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            connection = UserChannelConnection.objects.get(
                id=connection_id,
                user=request.user,
                channel_type__in=['calendar', 'gmail', 'outlook']
            )
        except UserChannelConnection.DoesNotExist:
            return Response(
                {'error': 'Calendar connection not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get calendars from UniPile
        from communications.unipile.core.client import UnipileClient
        from communications.unipile.clients.calendar import UnipileCalendarClient
        
        try:
            # For testing without UniPile API, return mock data
            if connection.unipile_account_id == 'test-unipile-account-123':
                # Mock calendar data for testing
                calendars = [
                    {
                        'id': 'primary',
                        'name': 'Primary Calendar',
                        'is_default': True,
                        'is_read_only': False,
                        'is_owned_by_user': True
                    },
                    {
                        'id': 'work-calendar',
                        'name': 'Work Calendar',
                        'is_default': False,
                        'is_read_only': False,
                        'is_owned_by_user': True
                    },
                    {
                        'id': 'personal-calendar',
                        'name': 'Personal Calendar',
                        'is_default': False,
                        'is_read_only': False,
                        'is_owned_by_user': True
                    }
                ]
            else:
                from django.conf import settings
                client = UnipileClient(
                    dsn=settings.UNIPILE_DSN,
                    access_token=settings.UNIPILE_API_KEY
                )
                calendar_client = UnipileCalendarClient(client)
                
                # Use sync_to_async for the async call
                from asgiref.sync import async_to_sync
                calendars_response = async_to_sync(calendar_client.get_calendars)(
                    connection.unipile_account_id
                )
                
                logger.info(f"UniPile calendars response: {calendars_response}")
                
                # Extract calendar list from response - check different possible structures
                if isinstance(calendars_response, dict):
                    # Try different possible response structures
                    calendars = calendars_response.get('items', 
                               calendars_response.get('calendars', 
                               calendars_response.get('data', [])))
                elif isinstance(calendars_response, list):
                    calendars = calendars_response
                else:
                    calendars = []
                
                logger.info(f"Found {len(calendars)} calendars from UniPile")
            
            # Format calendar data for frontend
            # Include all calendars for now to debug
            data = [{
                'id': cal.get('id'),
                'name': cal.get('name', 'Unnamed Calendar'),
                'is_default': cal.get('is_primary', cal.get('is_default', False)),  # UniPile uses is_primary
                'is_read_only': cal.get('is_read_only', False),
                'is_owned_by_user': cal.get('is_owned_by_user', True)
            } for cal in calendars]
            
            logger.info(f"Returning {len(data)} calendars to frontend")
            
            return Response({'calendars': data})
            
        except Exception as e:
            logger.error(f"Failed to fetch calendars: {e}")
            return Response(
                {'error': 'Failed to fetch calendars from provider'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Get available time slots",
        parameters=[
            OpenApiParameter(name='start_date', type=str, required=True),
            OpenApiParameter(name='end_date', type=str, required=True),
            OpenApiParameter(name='duration_minutes', type=int, required=True),
        ]
    )
    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        """Get available time slots for a profile"""
        profile = self.get_object()
        
        # Parse parameters
        try:
            start_date = datetime.fromisoformat(request.query_params.get('start_date'))
            end_date = datetime.fromisoformat(request.query_params.get('end_date'))
            duration_minutes = int(request.query_params.get('duration_minutes', 30))
        except (TypeError, ValueError) as e:
            return Response(
                {'error': f'Invalid parameters: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get availability
        calculator = AvailabilityCalculator(profile)
        try:
            slots = async_to_sync(calculator.get_available_slots)(
                start_date, end_date, duration_minutes
            )
            return Response({'slots': slots})
        except Exception as e:
            logger.error(f"Failed to get availability: {e}")
            return Response(
                {'error': 'Failed to calculate availability'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def block_dates(self, request, pk=None):
        """Block specific dates"""
        profile = self.get_object()
        dates = request.data.get('dates', [])
        
        if not dates:
            return Response(
                {'error': 'No dates provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add to blocked dates
        current_blocked = profile.blocked_dates or []
        for date_str in dates:
            if date_str not in current_blocked:
                current_blocked.append(date_str)
        
        profile.blocked_dates = current_blocked
        profile.save(update_fields=['blocked_dates'])
        
        return Response({'blocked_dates': current_blocked})
    
    @action(detail=True, methods=['post'])
    def unblock_dates(self, request, pk=None):
        """Unblock specific dates"""
        profile = self.get_object()
        dates = request.data.get('dates', [])
        
        if not dates:
            return Response(
                {'error': 'No dates provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Remove from blocked dates
        current_blocked = profile.blocked_dates or []
        for date_str in dates:
            if date_str in current_blocked:
                current_blocked.remove(date_str)
        
        profile.blocked_dates = current_blocked
        profile.save(update_fields=['blocked_dates'])
        
        return Response({'blocked_dates': current_blocked})


class MeetingTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing meeting types
    Handles meeting templates and configuration
    """
    serializer_class = MeetingTypeSerializer
    permission_classes = [permissions.IsAuthenticated, MeetingTypePermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['pipeline', 'location_type', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'duration_minutes', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Filter meeting types based on permissions"""
        permission_manager = SyncPermissionManager(self.request.user)
        
        if permission_manager.has_permission('action', 'communication_settings', 'scheduling_all', None):
            # Admin can see all meeting types including templates
            return MeetingType.objects.all().select_related(
                'pipeline', 'user', 'template_source'
            ).annotate(links_count=Count('scheduling_links'))
        elif permission_manager.has_permission('action', 'communication_settings', 'scheduling', None):
            # Users can see:
            # 1. Their own meeting types
            # 2. Organization-wide templates
            return MeetingType.objects.filter(
                Q(user=self.request.user) |  # Their own meeting types
                Q(is_template=True, created_for_org=True)  # Organization templates
            ).select_related('pipeline', 'user', 'template_source').annotate(
                links_count=Count('scheduling_links')
            )
        
        return MeetingType.objects.none()
    
    def perform_create(self, serializer):
        """Set user to current user"""
        # Check if user has permission to create templates
        permission_manager = SyncPermissionManager(self.request.user)
        is_template = serializer.validated_data.get('is_template', False)
        created_for_org = serializer.validated_data.get('created_for_org', False)
        
        # Only admins can create templates
        if is_template and not permission_manager.has_permission('action', 'communication_settings', 'scheduling_all', None):
            # Regular users cannot create templates
            is_template = False
            created_for_org = False
        
        # Save the meeting type - slug will be auto-generated by the model's save method
        serializer.save(
            user=self.request.user,
            is_template=is_template,
            created_for_org=created_for_org
        )
    
    @action(detail=False, methods=['get'])
    def calendars_for_connection(self, request):
        """Get calendars from user's profile connection"""
        # First try to get connection_id from query params (for backward compatibility)
        connection_id = request.query_params.get('connection_id')
        
        if not connection_id:
            # Get from user's active scheduling profile
            profile = request.user.scheduling_profiles.filter(is_active=True).first()
            
            if not profile:
                return Response(
                    {'error': 'No active scheduling profile found. Please configure your availability settings first.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not profile.calendar_connection:
                return Response(
                    {'error': 'No calendar connection found. Please connect a calendar in your availability settings.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            connection = profile.calendar_connection
        else:
            # Use the provided connection_id
            try:
                connection = UserChannelConnection.objects.get(
                    id=connection_id,
                    user=request.user,
                    channel_type__in=['calendar', 'gmail', 'outlook']
                )
            except UserChannelConnection.DoesNotExist:
                return Response(
                    {'error': 'Calendar connection not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Get calendars from UniPile
        from communications.unipile.core.client import UnipileClient
        from communications.unipile.clients.calendar import UnipileCalendarClient
        
        try:
            # For testing without UniPile API, return mock data
            if connection.unipile_account_id == 'test-unipile-account-123':
                # Mock calendar data for testing
                calendars = [
                    {
                        'id': 'primary',
                        'name': 'Primary Calendar',
                        'is_default': True,
                        'is_read_only': False,
                        'is_owned_by_user': True
                    },
                    {
                        'id': 'work-calendar',
                        'name': 'Work Calendar',
                        'is_default': False,
                        'is_read_only': False,
                        'is_owned_by_user': True
                    },
                    {
                        'id': 'personal-calendar',
                        'name': 'Personal Calendar',
                        'is_default': False,
                        'is_read_only': False,
                        'is_owned_by_user': True
                    }
                ]
            else:
                from django.conf import settings
                client = UnipileClient(
                    dsn=settings.UNIPILE_DSN,
                    access_token=settings.UNIPILE_API_KEY
                )
                calendar_client = UnipileCalendarClient(client)
                
                # Use sync_to_async for the async call
                from asgiref.sync import async_to_sync
                calendars_response = async_to_sync(calendar_client.get_calendars)(
                    connection.unipile_account_id
                )
                
                logger.info(f"UniPile calendars response: {calendars_response}")
                
                # Extract calendar list from response - check different possible structures
                if isinstance(calendars_response, dict):
                    # Try different possible response structures
                    calendars = calendars_response.get('items', 
                               calendars_response.get('calendars', 
                               calendars_response.get('data', [])))
                elif isinstance(calendars_response, list):
                    calendars = calendars_response
                else:
                    calendars = []
                
                logger.info(f"Found {len(calendars)} calendars from UniPile")
            
            # Format calendar data for frontend
            # Include all calendars for now to debug
            data = [{
                'id': cal.get('id'),
                'name': cal.get('name', 'Unnamed Calendar'),
                'is_default': cal.get('is_primary', cal.get('is_default', False)),  # UniPile uses is_primary
                'is_read_only': cal.get('is_read_only', False),
                'is_owned_by_user': cal.get('is_owned_by_user', True)
            } for cal in calendars]
            
            logger.info(f"Returning {len(data)} calendars to frontend")
            
            return Response({'calendars': data})
            
        except Exception as e:
            logger.error(f"Failed to fetch calendars: {e}")
            return Response(
                {'error': 'Failed to fetch calendars from provider'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicate a meeting type"""
        meeting_type = self.get_object()
        
        # Create duplicate
        new_name = request.data.get('name', f"{meeting_type.name} (Copy)")
        from django.utils.text import slugify
        slug = slugify(new_name)
        
        # Ensure unique slug
        base_slug = slug
        counter = 1
        while MeetingType.objects.filter(user=self.request.user, slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        duplicate = MeetingType.objects.create(
            user=self.request.user,
            name=new_name,
            slug=slug,
            description=meeting_type.description,
            duration_minutes=meeting_type.duration_minutes,
            location_type=meeting_type.location_type,
            location_details=meeting_type.location_details,
            pipeline=meeting_type.pipeline,
            pipeline_stage=meeting_type.pipeline_stage,
            booking_form_config=meeting_type.booking_form_config,
            custom_questions=meeting_type.custom_questions,
            required_fields=meeting_type.required_fields,
            confirmation_template=meeting_type.confirmation_template,
            reminder_template=meeting_type.reminder_template,
            cancellation_template=meeting_type.cancellation_template,
            allow_rescheduling=meeting_type.allow_rescheduling,
            allow_cancellation=meeting_type.allow_cancellation,
            cancellation_notice_hours=meeting_type.cancellation_notice_hours,
            send_reminders=meeting_type.send_reminders,
            reminder_hours=meeting_type.reminder_hours,
            is_active=True
        )
        
        serializer = self.get_serializer(duplicate)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get analytics for a meeting type"""
        meeting_type = self.get_object()
        
        # Calculate analytics
        total = meeting_type.total_bookings
        if total > 0:
            completion_rate = (meeting_type.total_completed / total) * 100
            cancellation_rate = (meeting_type.total_cancelled / total) * 100
            no_show_rate = (meeting_type.total_no_shows / total) * 100
        else:
            completion_rate = cancellation_rate = no_show_rate = 0
        
        # Get recent meetings
        recent_meetings = ScheduledMeeting.objects.filter(
            meeting_type=meeting_type
        ).order_by('-created_at')[:10]
        
        return Response({
            'total_bookings': total,
            'total_completed': meeting_type.total_completed,
            'total_cancelled': meeting_type.total_cancelled,
            'total_no_shows': meeting_type.total_no_shows,
            'completion_rate': round(completion_rate, 2),
            'cancellation_rate': round(cancellation_rate, 2),
            'no_show_rate': round(no_show_rate, 2),
            'recent_meetings': ScheduledMeetingSerializer(
                recent_meetings, many=True, context={'request': request}
            ).data
        })
    
    @action(detail=False, methods=['get'])
    def templates(self, request):
        """Get available templates that can be copied"""
        permission_manager = SyncPermissionManager(request.user)
        
        # Filter templates that are available
        if permission_manager.has_permission('action', 'communication_settings', 'scheduling_all', None):
            # Admin can see all templates
            templates = MeetingType.objects.filter(is_template=True)
        else:
            # Regular users only see organization-wide templates
            templates = MeetingType.objects.filter(
                is_template=True,
                created_for_org=True
            )
        
        templates = templates.select_related('user', 'pipeline').order_by('name')
        serializer = self.get_serializer(templates, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def copy_from_template(self, request, pk=None):
        """Copy a template to create a new meeting type"""
        template = self.get_object()
        
        # Check if this is actually a template
        if not template.is_template:
            return Response(
                {'error': 'This meeting type is not a template'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # All templates should be usable by users in the organization
        # Templates are created by admins for everyone to use
        # No additional permission check needed here since the user is already authenticated
        
        # Get new name from request or use template name
        new_name = request.data.get('name', template.name)
        
        # Generate unique slug
        from django.utils.text import slugify
        base_slug = slugify(new_name)
        slug = base_slug
        counter = 1
        while MeetingType.objects.filter(user=request.user, slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Check if this is a centralized template and set sync accordingly
        from django.utils import timezone
        is_synced = template.template_type == 'centralized'
        
        # Get calendar info from request (user must specify their calendar)
        calendar_id = request.data.get('calendar_id', '')
        calendar_name = request.data.get('calendar_name', '')
        
        # Create copy with all template settings except calendar
        new_meeting_type = MeetingType.objects.create(
            user=request.user,
            name=new_name,
            slug=slug,
            description=template.description,
            is_template=False,  # Copy is not a template
            template_source=template,  # Track the source template
            is_synced_to_template=is_synced,  # Sync if centralized
            last_synced_at=timezone.now() if is_synced else None,
            created_for_org=False,  # User's personal meeting type
            # User-specific fields
            calendar_id=calendar_id,
            calendar_name=calendar_name,
            # All template fields
            duration_minutes=template.duration_minutes,
            location_type=template.location_type,
            location_details=template.location_details,
            pipeline=template.pipeline,
            pipeline_stage=template.pipeline_stage,
            booking_form_config=template.booking_form_config,
            custom_questions=template.custom_questions,
            required_fields=template.required_fields,
            confirmation_template=template.confirmation_template,
            reminder_template=template.reminder_template,
            cancellation_template=template.cancellation_template,
            allow_rescheduling=template.allow_rescheduling,
            allow_cancellation=template.allow_cancellation,
            cancellation_notice_hours=template.cancellation_notice_hours,
            send_reminders=template.send_reminders,
            reminder_hours=template.reminder_hours,
            is_active=True
        )
        
        serializer = self.get_serializer(new_meeting_type)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def sync_with_template(self, request, pk=None):
        """Sync a meeting type with its centralized template"""
        meeting_type = self.get_object()
        
        # Check if this meeting type has a template source
        if not meeting_type.template_source:
            return Response(
                {'error': 'This meeting type is not based on a template'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if the template is centralized
        if meeting_type.template_source.template_type != 'centralized':
            return Response(
                {'error': 'This template is standalone and cannot be synced'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Sync fields from the template
        template = meeting_type.template_source
        from django.utils import timezone
        
        # Update fields from template (preserve user-specific settings like calendar)
        meeting_type.description = template.description
        meeting_type.duration_minutes = template.duration_minutes
        meeting_type.location_type = template.location_type
        meeting_type.location_details = template.location_details
        meeting_type.pipeline = template.pipeline
        meeting_type.pipeline_stage = template.pipeline_stage
        meeting_type.booking_form_config = template.booking_form_config
        meeting_type.custom_questions = template.custom_questions
        meeting_type.required_fields = template.required_fields
        meeting_type.confirmation_template = template.confirmation_template
        meeting_type.reminder_template = template.reminder_template
        meeting_type.cancellation_template = template.cancellation_template
        meeting_type.allow_rescheduling = template.allow_rescheduling
        meeting_type.allow_cancellation = template.allow_cancellation
        meeting_type.cancellation_notice_hours = template.cancellation_notice_hours
        meeting_type.send_reminders = template.send_reminders
        meeting_type.reminder_hours = template.reminder_hours
        
        # Update sync status
        meeting_type.is_synced_to_template = True
        meeting_type.last_synced_at = timezone.now()
        meeting_type.save()
        
        serializer = self.get_serializer(meeting_type)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def unsync_from_template(self, request, pk=None):
        """Stop syncing a meeting type with its template"""
        meeting_type = self.get_object()
        
        # Check if this meeting type is synced
        if not meeting_type.is_synced_to_template:
            return Response(
                {'error': 'This meeting type is not synced to a template'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Unsync from template
        meeting_type.is_synced_to_template = False
        meeting_type.save(update_fields=['is_synced_to_template', 'updated_at'])
        
        serializer = self.get_serializer(meeting_type)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def make_template(self, request, pk=None):
        """Convert a meeting type to a template (admin only)"""
        meeting_type = self.get_object()
        permission_manager = SyncPermissionManager(request.user)
        
        # Only admins can create templates
        if not permission_manager.has_permission('action', 'communication_settings', 'scheduling_all', None):
            return Response(
                {'error': 'Only administrators can create templates'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update the meeting type to be a template
        meeting_type.is_template = True
        meeting_type.template_type = request.data.get('template_type', 'standalone')
        meeting_type.created_for_org = request.data.get('created_for_org', True)
        
        # Clear user-specific fields from templates
        meeting_type.calendar_id = ''
        meeting_type.calendar_name = ''
        
        meeting_type.save(update_fields=[
            'is_template', 'template_type', 'created_for_org', 
            'calendar_id', 'calendar_name', 'updated_at'
        ])
        
        serializer = self.get_serializer(meeting_type)
        return Response(serializer.data)


class SchedulingLinkViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing scheduling links
    Handles public booking link creation and management
    """
    serializer_class = SchedulingLinkSerializer
    permission_classes = [permissions.IsAuthenticated, SchedulingLinkPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['meeting_type', 'pipeline', 'is_active']
    search_fields = ['name', 'public_name', 'public_description']
    ordering_fields = ['name', 'created_at', 'booking_count', 'conversion_rate']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter scheduling links based on permissions"""
        permission_manager = SyncPermissionManager(self.request.user)
        
        if permission_manager.has_permission('action', 'communication_settings', 'scheduling_all', None):
            # Admin can see all scheduling links
            return SchedulingLink.objects.all().select_related(
                'meeting_type', 'pipeline', 'conversation'
            )
        elif permission_manager.has_permission('action', 'communication_settings', 'scheduling', None):
            # Users can only see links for their meeting types
            return SchedulingLink.objects.filter(
                meeting_type__user=self.request.user
            ).select_related('meeting_type', 'pipeline', 'conversation')
        
        return SchedulingLink.objects.none()
    
    def perform_create(self, serializer):
        """Set created_by to current user"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a scheduling link"""
        link = self.get_object()
        link.is_active = False
        link.save(update_fields=['is_active'])
        return Response({'status': 'deactivated'})
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a scheduling link"""
        link = self.get_object()
        link.is_active = True
        link.save(update_fields=['is_active'])
        return Response({'status': 'activated'})
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get analytics for a scheduling link"""
        link = self.get_object()
        
        # Get bookings over time
        bookings = ScheduledMeeting.objects.filter(
            scheduling_link=link
        ).values('created_at__date').annotate(
            count=Count('id')
        ).order_by('created_at__date')
        
        return Response({
            'view_count': link.view_count,
            'booking_count': link.booking_count,
            'conversion_rate': float(link.conversion_rate),
            'bookings_over_time': list(bookings),
            'is_expired': link.is_expired(),
            'has_reached_limit': link.has_reached_limit()
        })


class ScheduledMeetingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing scheduled meetings
    Handles meeting lifecycle and operations
    """
    serializer_class = ScheduledMeetingSerializer
    permission_classes = [permissions.IsAuthenticated, ScheduledMeetingPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['meeting_type', 'status', 'host', 'participant']
    search_fields = ['participant__name', 'participant__email']
    ordering_fields = ['start_time', 'created_at', 'status']
    ordering = ['start_time']
    
    def get_queryset(self):
        """Filter scheduled meetings based on permissions"""
        permission_manager = SyncPermissionManager(self.request.user)
        
        if permission_manager.has_permission('action', 'communication_settings', 'scheduling_all', None):
            # Admin can see all scheduled meetings
            queryset = ScheduledMeeting.objects.all().select_related(
                'meeting_type', 'scheduling_link', 'participant',
                'host', 'record', 'conversation'
            )
        elif permission_manager.has_permission('action', 'communication_settings', 'scheduling', None):
            # Users can see meetings they host or participate in
            queryset = ScheduledMeeting.objects.filter(
                Q(host=self.request.user) |
                Q(meeting_type__user=self.request.user) |
                Q(participant__email=self.request.user.email)
            ).select_related(
                'meeting_type', 'scheduling_link', 'participant',
                'host', 'record', 'conversation'
            )
        else:
            return ScheduledMeeting.objects.none()
        
        # Filter by time period if requested
        period = self.request.query_params.get('period')
        if period == 'upcoming':
            queryset = queryset.filter(
                start_time__gte=timezone.now(),
                status__in=['scheduled', 'confirmed', 'reminder_sent']
            )
        elif period == 'past':
            queryset = queryset.filter(
                Q(end_time__lt=timezone.now()) |
                Q(status__in=['completed', 'no_show', 'cancelled'])
            )
        elif period == 'today':
            today = timezone.now().date()
            queryset = queryset.filter(
                start_time__date=today
            )
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a meeting"""
        meeting = self.get_object()
        
        # Check if can cancel
        if not meeting.can_cancel():
            return Response(
                {'error': 'Meeting cannot be cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get cancellation reason
        serializer = MeetingCancellationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Cancel the meeting
        meeting.cancel(
            cancelled_by=request.user,
            reason=serializer.validated_data.get('reason', '')
        )
        
        # TODO: Send cancellation notifications
        
        return Response({'status': 'cancelled'})
    
    @action(detail=True, methods=['post'])
    def reschedule(self, request, pk=None):
        """Reschedule a meeting"""
        meeting = self.get_object()
        
        # Check if can reschedule
        if not meeting.can_reschedule():
            return Response(
                {'error': 'Meeting cannot be rescheduled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get new time slot
        serializer = MeetingRescheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        new_slot = serializer.validated_data['new_slot']
        
        # Create new meeting
        new_meeting = ScheduledMeeting.objects.create(
            meeting_type=meeting.meeting_type,
            scheduling_link=meeting.scheduling_link,
            conversation=meeting.conversation,
            participant=meeting.participant,
            host=meeting.host,
            record=meeting.record,
            start_time=datetime.fromisoformat(new_slot['start']),
            end_time=datetime.fromisoformat(new_slot['end']),
            timezone=meeting.timezone,
            booking_data=meeting.booking_data,
            status='scheduled'
        )
        
        # Mark old meeting as rescheduled
        meeting.status = 'rescheduled'
        meeting.rescheduled_to = new_meeting
        meeting.save(update_fields=['status', 'rescheduled_to'])
        
        # TODO: Send rescheduling notifications
        
        return Response(
            ScheduledMeetingSerializer(new_meeting, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark meeting as completed"""
        meeting = self.get_object()
        
        if meeting.status != 'in_progress':
            return Response(
                {'error': 'Only in-progress meetings can be marked as completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add post-meeting notes if provided
        notes = request.data.get('post_meeting_notes', '')
        if notes:
            meeting.post_meeting_notes = notes
        
        meeting.mark_completed()
        
        return Response({'status': 'completed'})
    
    @action(detail=True, methods=['post'])
    def no_show(self, request, pk=None):
        """Mark meeting as no-show"""
        meeting = self.get_object()
        
        if meeting.status not in ['scheduled', 'confirmed', 'reminder_sent', 'in_progress']:
            return Response(
                {'error': 'Invalid status for marking as no-show'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        meeting.mark_no_show()
        
        return Response({'status': 'no_show'})
    
    @action(detail=False, methods=['get'])
    def calendar(self, request):
        """Get meetings in calendar format"""
        # Get date range
        start = request.query_params.get('start')
        end = request.query_params.get('end')
        
        if not start or not end:
            return Response(
                {'error': 'Start and end dates required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            start_date = datetime.fromisoformat(start)
            end_date = datetime.fromisoformat(end)
        except ValueError:
            return Response(
                {'error': 'Invalid date format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get meetings in range
        meetings = self.get_queryset().filter(
            start_time__gte=start_date,
            start_time__lt=end_date
        )
        
        # Format for calendar
        events = []
        for meeting in meetings:
            events.append({
                'id': str(meeting.id),
                'title': f"{meeting.meeting_type.name} - {meeting.participant.name or meeting.participant.email}",
                'start': meeting.start_time.isoformat(),
                'end': meeting.end_time.isoformat(),
                'status': meeting.status,
                'meeting_url': meeting.meeting_url,
                'location': meeting.meeting_location,
                'participant': {
                    'name': meeting.participant.name,
                    'email': meeting.participant.email
                }
            })
        
        return Response({'events': events})


class AvailabilityOverrideViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing availability overrides
    Handles date-specific availability changes
    """
    serializer_class = AvailabilityOverrideSerializer
    permission_classes = [permissions.IsAuthenticated, AvailabilityOverridePermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['profile', 'date', 'override_type']
    ordering_fields = ['date', 'created_at']
    ordering = ['date']
    
    def get_queryset(self):
        """Filter overrides based on permissions"""
        permission_manager = SyncPermissionManager(self.request.user)
        
        if permission_manager.has_permission('action', 'communication_settings', 'scheduling_all', None):
            # Admin can see all availability overrides
            return AvailabilityOverride.objects.all().select_related('profile')
        elif permission_manager.has_permission('action', 'communication_settings', 'scheduling', None):
            # Users can only see overrides for their profiles
            return AvailabilityOverride.objects.filter(
                profile__user=self.request.user
            ).select_related('profile')
        
        return AvailabilityOverride.objects.none()
    
    def perform_create(self, serializer):
        """Validate profile ownership"""
        profile = serializer.validated_data['profile']
        if profile.user != self.request.user:
            raise permissions.PermissionDenied("Cannot create override for another user's profile")
        serializer.save()