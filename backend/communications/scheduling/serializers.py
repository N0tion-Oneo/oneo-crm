"""
Serializers for scheduling models
Handles data validation and transformation for scheduling API endpoints
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta

from communications.models import Channel, Conversation, Participant
from pipelines.models import Pipeline, Record
from pipelines.serializers import PipelineSerializer
from communications.serializers import ParticipantSerializer, ConversationListSerializer
from .models import (
    SchedulingProfile, MeetingType, SchedulingLink,
    ScheduledMeeting, AvailabilityOverride
)

User = get_user_model()


class AvailabilityOverrideSerializer(serializers.ModelSerializer):
    """Serializer for availability overrides"""
    
    class Meta:
        model = AvailabilityOverride
        fields = [
            'id', 'date', 'override_type', 'time_slots',
            'reason', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_time_slots(self, value):
        """Validate time slot format"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Time slots must be a list")
        
        for slot in value:
            if not isinstance(slot, dict):
                raise serializers.ValidationError("Each time slot must be an object")
            if 'start' not in slot or 'end' not in slot:
                raise serializers.ValidationError("Each time slot must have 'start' and 'end' times")
            
            # Validate time format
            try:
                datetime.strptime(slot['start'], '%H:%M')
                datetime.strptime(slot['end'], '%H:%M')
            except ValueError:
                raise serializers.ValidationError("Time must be in HH:MM format")
        
        return value


class SchedulingProfileSerializer(serializers.ModelSerializer):
    """Serializer for scheduling profiles"""
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    calendar_connection_display = serializers.SerializerMethodField()
    availability_overrides = AvailabilityOverrideSerializer(many=True, read_only=True)
    
    class Meta:
        model = SchedulingProfile
        fields = [
            'id', 'user', 'calendar_connection', 'calendar_connection_display', 'timezone',
            'buffer_minutes', 'min_notice_hours', 'max_advance_days', 'slot_interval_minutes',
            'working_hours', 'calendar_sync_enabled', 'show_busy_slots',
            'blocked_dates', 'override_dates', 'is_active',
            'availability_overrides', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def get_calendar_connection_display(self, obj):
        """Return display information for the calendar connection"""
        if obj.calendar_connection:
            return {
                'id': str(obj.calendar_connection.id),
                'account_name': obj.calendar_connection.account_name,
                'channel_type': obj.calendar_connection.channel_type,
                'auth_status': obj.calendar_connection.auth_status
            }
        return None
    
    def validate_working_hours(self, value):
        """Validate working hours format"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Working hours must be an object")
        
        valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        for day, hours in value.items():
            if day not in valid_days:
                raise serializers.ValidationError(f"Invalid day: {day}")
            
            if not isinstance(hours, list):
                raise serializers.ValidationError(f"Hours for {day} must be a list")
            
            for time_range in hours:
                if not isinstance(time_range, dict):
                    raise serializers.ValidationError(f"Time range for {day} must be an object")
                if 'start' not in time_range or 'end' not in time_range:
                    raise serializers.ValidationError(f"Time range for {day} must have 'start' and 'end'")
                
                # Validate time format
                try:
                    datetime.strptime(time_range['start'], '%H:%M')
                    datetime.strptime(time_range['end'], '%H:%M')
                except ValueError:
                    raise serializers.ValidationError(f"Invalid time format for {day}")
        
        return value
    
    def validate_calendar_connection(self, value):
        """Ensure calendar connection is valid and belongs to the user"""
        if value:
            # Check if the connection belongs to the requesting user
            request = self.context.get('request')
            if request and value.user != request.user:
                raise serializers.ValidationError("Calendar connection does not belong to the current user")
            # Check if it's a valid calendar type
            if value.channel_type not in ['calendar', 'gmail', 'outlook']:
                raise serializers.ValidationError("Connection must be a calendar type (Google Calendar or Outlook)")
        return value


class MeetingTypeSerializer(serializers.ModelSerializer):
    """Serializer for meeting types"""
    user = serializers.SerializerMethodField()
    pipeline_name = serializers.CharField(source='pipeline.name', read_only=True)
    scheduling_links_count = serializers.IntegerField(source='scheduling_links.count', read_only=True)
    calendar_connection_display = serializers.SerializerMethodField()
    booking_url = serializers.SerializerMethodField()
    has_scheduling_profile = serializers.SerializerMethodField()
    template_source_name = serializers.CharField(source='template_source.name', read_only=True, allow_null=True)
    
    class Meta:
        model = MeetingType
        fields = [
            'id', 'user', 'name', 'slug', 'description',
            'is_template', 'template_type', 'template_source', 'template_source_name', 'is_synced_to_template',
            'created_for_org', 'last_synced_at',
            'calendar_connection_display', 'calendar_id', 'calendar_name',
            'duration_minutes', 'location_type', 'location_details',
            'pipeline', 'pipeline_name', 'pipeline_stage',
            'booking_form_config', 'custom_questions', 'required_fields',
            'confirmation_template', 'reminder_template', 'cancellation_template',
            'allow_rescheduling', 'allow_cancellation', 'cancellation_notice_hours',
            'send_reminders', 'reminder_hours',
            'total_bookings', 'total_completed', 'total_cancelled', 'total_no_shows',
            'is_active', 'scheduling_links_count', 'booking_url', 'has_scheduling_profile',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'template_source', 'total_bookings', 'total_completed',
            'total_cancelled', 'total_no_shows', 'created_at', 'updated_at'
        ]
    
    def get_user(self, obj):
        """Return user information"""
        if obj.user:
            return {
                'id': str(obj.user.id),
                'email': obj.user.email,
                'first_name': obj.user.first_name,
                'last_name': obj.user.last_name,
                'full_name': obj.user.get_full_name() or obj.user.username
            }
        return None
    
    def get_calendar_connection_display(self, obj):
        """Return display information for the calendar connection from user's profile"""
        connection = obj.calendar_connection  # This uses the property we added
        if connection:
            return {
                'id': str(connection.id),
                'account_name': connection.account_name,
                'channel_type': connection.channel_type,
                'auth_status': connection.auth_status
            }
        return None
    
    def get_has_scheduling_profile(self, obj):
        """Check if user has an active scheduling profile"""
        return obj.user.scheduling_profiles.filter(is_active=True).exists()
    
    def get_booking_url(self, obj):
        """Return the full booking URL for this meeting type"""
        request = self.context.get('request')
        if request:
            # Get the full URL with the current host
            return obj.get_full_booking_url(request)
        else:
            # Return the relative URL
            return obj.get_booking_url()
    
    def validate(self, attrs):
        """Validate that user has a scheduling profile with calendar connection"""
        request = self.context.get('request')
        if request and request.method in ['POST', 'PUT', 'PATCH']:
            user = request.user
            profile = user.scheduling_profiles.filter(is_active=True).first()
            if not profile:
                raise serializers.ValidationError(
                    "You must create a scheduling profile in Availability Settings before creating meeting types"
                )
            if not profile.calendar_connection:
                raise serializers.ValidationError(
                    "You must connect a calendar account in Availability Settings before creating meeting types"
                )
        return attrs
    
    def validate_duration_minutes(self, value):
        """Validate duration is reasonable"""
        if value < 5 or value > 480:
            raise serializers.ValidationError("Duration must be between 5 and 480 minutes")
        return value
    
    def validate_custom_questions(self, value):
        """Validate custom questions format"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Custom questions must be a list")
        
        for question in value:
            if not isinstance(question, dict):
                raise serializers.ValidationError("Each question must be an object")
            if 'label' not in question or 'type' not in question:
                raise serializers.ValidationError("Each question must have 'label' and 'type'")
            if question['type'] not in ['text', 'textarea', 'select', 'checkbox', 'radio']:
                raise serializers.ValidationError(f"Invalid question type: {question['type']}")
        
        return value


class SchedulingLinkSerializer(serializers.ModelSerializer):
    """Serializer for scheduling links"""
    meeting_type_name = serializers.CharField(source='meeting_type.name', read_only=True)
    pipeline_name = serializers.CharField(source='pipeline.name', read_only=True)
    booking_url = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = SchedulingLink
        fields = [
            'id', 'meeting_type', 'meeting_type_name', 'slug',
            'name', 'public_name', 'public_description',
            'conversation', 'pipeline', 'pipeline_name',
            'auto_create_record', 'field_mapping', 'override_availability',
            'expires_at', 'max_bookings', 'password', 'allowed_emails',
            'view_count', 'booking_count', 'conversion_rate',
            'is_active', 'booking_url', 'status',
            'created_at', 'updated_at', 'created_by'
        ]
        read_only_fields = [
            'id', 'slug', 'conversation', 'view_count', 'booking_count',
            'conversion_rate', 'created_at', 'updated_at', 'created_by'
        ]
    
    def get_booking_url(self, obj):
        """Generate the public booking URL"""
        request = self.context.get('request')
        if request:
            return f"{request.scheme}://{request.get_host()}/book/{obj.slug}"
        return f"/book/{obj.slug}"
    
    def get_status(self, obj):
        """Get link status"""
        if not obj.is_active:
            return 'inactive'
        if obj.is_expired():
            return 'expired'
        if obj.has_reached_limit():
            return 'limit_reached'
        return 'active'
    
    def validate_expires_at(self, value):
        """Ensure expiry is in the future"""
        if value and value <= timezone.now():
            raise serializers.ValidationError("Expiry date must be in the future")
        return value
    
    def validate_field_mapping(self, value):
        """Validate field mapping format"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Field mapping must be an object")
        return value


class ScheduledMeetingSerializer(serializers.ModelSerializer):
    """Serializer for scheduled meetings"""
    meeting_type_name = serializers.CharField(source='meeting_type.name', read_only=True)
    participant_detail = ParticipantSerializer(source='participant', read_only=True)
    host_name = serializers.CharField(source='host.get_full_name', read_only=True)
    record_display = serializers.CharField(source='record.display_name', read_only=True)
    can_cancel = serializers.BooleanField(read_only=True)
    can_reschedule = serializers.BooleanField(read_only=True)
    is_past = serializers.BooleanField(read_only=True)
    is_upcoming = serializers.BooleanField(read_only=True)
    is_in_progress = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = ScheduledMeeting
        fields = [
            'id', 'meeting_type', 'meeting_type_name', 'scheduling_link',
            'conversation', 'participant', 'participant_detail',
            'host', 'host_name', 'record', 'record_display',
            'start_time', 'end_time', 'timezone',
            'calendar_event_id', 'calendar_sync_status',
            'meeting_url', 'meeting_location', 'meeting_password',
            'booking_data', 'status',
            'cancelled_at', 'cancelled_by', 'cancellation_reason',
            'rescheduled_to', 'reminder_sent_at',
            'pre_meeting_notes', 'post_meeting_notes',
            'can_cancel', 'can_reschedule', 'is_past', 'is_upcoming', 'is_in_progress',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'conversation', 'participant', 'host', 'record',
            'calendar_event_id', 'calendar_sync_status',
            'cancelled_at', 'cancelled_by', 'rescheduled_to',
            'reminder_sent_at', 'created_at', 'updated_at'
        ]
    
    def validate_status(self, value):
        """Validate status transitions"""
        if self.instance:
            current_status = self.instance.status
            # Define valid transitions
            valid_transitions = {
                'scheduled': ['confirmed', 'cancelled', 'reminder_sent'],
                'confirmed': ['reminder_sent', 'in_progress', 'cancelled'],
                'reminder_sent': ['in_progress', 'cancelled'],
                'in_progress': ['completed', 'no_show'],
                'completed': [],  # Terminal state
                'cancelled': [],  # Terminal state
                'no_show': [],  # Terminal state
                'rescheduled': []  # Terminal state
            }
            
            if value not in valid_transitions.get(current_status, []):
                raise serializers.ValidationError(
                    f"Cannot transition from {current_status} to {value}"
                )
        
        return value


class ScheduledMeetingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating scheduled meetings (used internally)"""
    
    class Meta:
        model = ScheduledMeeting
        fields = [
            'meeting_type', 'scheduling_link', 'participant',
            'host', 'start_time', 'end_time', 'timezone',
            'meeting_url', 'meeting_location', 'booking_data'
        ]
    
    def validate(self, data):
        """Validate meeting times"""
        if data['end_time'] <= data['start_time']:
            raise serializers.ValidationError("End time must be after start time")
        
        # Check if time is in the future
        if data['start_time'] <= timezone.now():
            raise serializers.ValidationError("Meeting must be scheduled in the future")
        
        return data


class PublicMeetingTypeSerializer(serializers.ModelSerializer):
    """Public serializer for meeting types accessed via clean URLs"""
    host = serializers.SerializerMethodField()
    booking_url = serializers.SerializerMethodField()
    organization = serializers.SerializerMethodField()
    
    class Meta:
        model = MeetingType
        fields = [
            'name', 'description', 'duration_minutes', 'location_type',
            'booking_form_config', 'custom_questions', 'required_fields',
            'allow_rescheduling', 'allow_cancellation', 'cancellation_notice_hours',
            'host', 'booking_url', 'organization'
        ]
    
    def get_host(self, obj):
        """Return host info with profile details"""
        user = obj.user
        from django.db import connection
        
        # Try to get staff profile data
        staff_profile = None
        if hasattr(user, 'staff_profile'):
            staff_profile = user.staff_profile
        
        # Get tenant name for organization context
        tenant_name = ''
        if hasattr(connection, 'tenant'):
            tenant_name = connection.tenant.name if hasattr(connection.tenant, 'name') else ''
        
        return {
            'name': user.get_full_name() or user.username,
            'title': staff_profile.job_title if staff_profile else '',
            'email': user.email if hasattr(user, 'email') else '',
            'avatar': user.avatar_url if hasattr(user, 'avatar_url') else '',
            'bio': staff_profile.bio if staff_profile else '',
            'department': staff_profile.department if staff_profile else '',
            'company': tenant_name,
            'expertise': staff_profile.skills if staff_profile and hasattr(staff_profile, 'skills') else [],
            'timezone': user.timezone if hasattr(user, 'timezone') else 'UTC',
            'professional_links': staff_profile.professional_links if staff_profile and hasattr(staff_profile, 'professional_links') else {}
        }
    
    def get_booking_url(self, obj):
        """Return the clean booking URL"""
        return obj.get_booking_url()
    
    def get_organization(self, obj):
        """Return organization info from tenant settings"""
        from django.apps import apps
        from django.db import connection
        
        # Try to get tenant-specific organization info
        organization_info = {}
        
        # Get the current tenant
        if hasattr(connection, 'tenant'):
            tenant = connection.tenant
            
            # Build logo URL properly
            logo_url = ''
            if hasattr(tenant, 'organization_logo') and tenant.organization_logo:
                try:
                    # Get the request to build absolute URL
                    request = self.context.get('request')
                    if request and tenant.organization_logo:
                        logo_url = request.build_absolute_uri(tenant.organization_logo.url)
                    elif tenant.organization_logo:
                        logo_url = tenant.organization_logo.url
                except (ValueError, AttributeError):
                    # If organization_logo doesn't have a file, it might raise an error
                    logo_url = ''
            
            # Get organization details from tenant model fields
            organization_info = {
                'name': tenant.name if hasattr(tenant, 'name') else '',
                'logo': logo_url,
                'website': tenant.organization_website if hasattr(tenant, 'organization_website') else ''
            }
        
        # If no tenant info, try staff profile department/company
        if not organization_info.get('name'):
            staff_profile = None
            if hasattr(obj.user, 'staff_profile'):
                staff_profile = obj.user.staff_profile
            
            organization_info = {
                'name': staff_profile.department if staff_profile else '',
                'logo': '',
                'website': ''
            }
        
        return organization_info


class PublicSchedulingLinkSerializer(serializers.ModelSerializer):
    """Public serializer for scheduling links (limited fields)"""
    meeting_type = serializers.SerializerMethodField()
    host = serializers.SerializerMethodField()
    organization = serializers.SerializerMethodField()
    
    class Meta:
        model = SchedulingLink
        fields = [
            'public_name', 'public_description', 'meeting_type', 'host', 'organization'
        ]
    
    def get_meeting_type(self, obj):
        """Return limited meeting type info"""
        return {
            'name': obj.meeting_type.name,
            'description': obj.meeting_type.description,
            'duration_minutes': obj.meeting_type.duration_minutes,
            'location_type': obj.meeting_type.location_type
        }
    
    def get_host(self, obj):
        """Return host info with profile details"""
        user = obj.meeting_type.user
        
        # Try to get staff profile data
        staff_profile = None
        if hasattr(user, 'staff_profile'):
            staff_profile = user.staff_profile
        
        return {
            'name': user.get_full_name() or user.username,
            'title': staff_profile.job_title if staff_profile else '',
            'email': user.email if hasattr(user, 'email') else '',
            'avatar': user.avatar_url if hasattr(user, 'avatar_url') else '',
            'bio': staff_profile.bio if staff_profile else '',
            'company': staff_profile.department if staff_profile else '',
            'expertise': staff_profile.skills if staff_profile and hasattr(staff_profile, 'skills') else [],
            'timezone': user.timezone if hasattr(user, 'timezone') else 'UTC'
        }
    
    def get_organization(self, obj):
        """Return organization info from tenant settings"""
        from django.apps import apps
        from django.db import connection
        
        # Try to get tenant-specific organization info
        organization_info = {}
        
        # Get the current tenant
        if hasattr(connection, 'tenant'):
            tenant = connection.tenant
            
            # Build logo URL properly
            logo_url = ''
            if hasattr(tenant, 'organization_logo') and tenant.organization_logo:
                try:
                    # Get the request to build absolute URL
                    request = self.context.get('request')
                    if request and tenant.organization_logo:
                        logo_url = request.build_absolute_uri(tenant.organization_logo.url)
                    elif tenant.organization_logo:
                        logo_url = tenant.organization_logo.url
                except (ValueError, AttributeError):
                    # If organization_logo doesn't have a file, it might raise an error
                    logo_url = ''
            
            # Get organization details from tenant model fields
            organization_info = {
                'name': tenant.name if hasattr(tenant, 'name') else '',
                'logo': logo_url,
                'website': tenant.organization_website if hasattr(tenant, 'organization_website') else ''
            }
        
        # If no tenant info, try staff profile department/company
        if not organization_info.get('name'):
            staff_profile = None
            if hasattr(obj.meeting_type.user, 'staff_profile'):
                staff_profile = obj.meeting_type.user.staff_profile
            
            organization_info = {
                'name': staff_profile.department if staff_profile else '',
                'logo': '',
                'website': ''
            }
        
        return organization_info


class BookingRequestSerializer(serializers.Serializer):
    """
    Serializer for booking requests from external users.
    Only validates system fields - actual form data is validated dynamically
    based on the pipeline field configuration.
    
    This serializer is now just for OpenAPI documentation purposes.
    The actual validation happens in the view using DataFieldValidator.
    """
    # System fields only
    timezone = serializers.CharField(required=False, default='UTC')
    selected_slot = serializers.DictField(required=True)
    
    # We accept any additional fields dynamically
    # The view will validate these based on the pipeline configuration
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Allow extra fields to pass through
        self.allow_extra_fields = True
    
    class Meta:
        # This allows the serializer to accept additional fields
        strict = False
    
    def validate_selected_slot(self, value):
        """Validate selected slot format"""
        if 'start' not in value or 'end' not in value:
            raise serializers.ValidationError("Selected slot must have 'start' and 'end'")
        
        try:
            start = datetime.fromisoformat(value['start'])
            end = datetime.fromisoformat(value['end'])
        except (ValueError, TypeError):
            raise serializers.ValidationError("Invalid datetime format")
        
        if end <= start:
            raise serializers.ValidationError("End time must be after start time")
        
        if start <= datetime.now(tz=start.tzinfo):
            raise serializers.ValidationError("Cannot book slots in the past")
        
        return value


class AvailabilityRequestSerializer(serializers.Serializer):
    """Serializer for availability check requests"""
    start_date = serializers.DateTimeField(required=True)
    end_date = serializers.DateTimeField(required=True)
    timezone = serializers.CharField(required=False, default='UTC')
    
    def validate(self, data):
        """Validate date range"""
        if data['end_date'] <= data['start_date']:
            raise serializers.ValidationError("End date must be after start date")
        
        # Limit range to prevent abuse
        max_range = timedelta(days=90)
        if data['end_date'] - data['start_date'] > max_range:
            raise serializers.ValidationError("Date range cannot exceed 90 days")
        
        return data


class MeetingCancellationSerializer(serializers.Serializer):
    """Serializer for meeting cancellation"""
    reason = serializers.CharField(required=False, max_length=500, allow_blank=True)
    
    def validate(self, data):
        """Add any additional validation if needed"""
        return data


class MeetingRescheduleSerializer(serializers.Serializer):
    """Serializer for meeting rescheduling"""
    new_slot = serializers.DictField(required=True)
    reason = serializers.CharField(required=False, max_length=500, allow_blank=True)
    
    def validate_new_slot(self, value):
        """Validate new slot format"""
        if 'start' not in value or 'end' not in value:
            raise serializers.ValidationError("New slot must have 'start' and 'end'")
        
        try:
            start = datetime.fromisoformat(value['start'])
            end = datetime.fromisoformat(value['end'])
        except (ValueError, TypeError):
            raise serializers.ValidationError("Invalid datetime format")
        
        if end <= start:
            raise serializers.ValidationError("End time must be after start time")
        
        if start <= datetime.now(tz=start.tzinfo):
            raise serializers.ValidationError("Cannot reschedule to the past")
        
        return value