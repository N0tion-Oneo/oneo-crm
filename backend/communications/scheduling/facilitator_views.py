"""
API views for facilitator meeting bookings
Handles the two-step booking process for coordinating meetings between two participants
"""
import logging
from datetime import datetime
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema

from .models import MeetingType, FacilitatorBooking
from .services import FacilitatorBookingProcessor
from .public_views import get_user_by_slug
from pipelines.models import Pipeline, Record
from django.db import transaction

logger = logging.getLogger(__name__)


class FacilitatorInitiateView(APIView):
    """
    Initiate a facilitator meeting by selecting participants from pipeline records
    This is used by the facilitator from within the dashboard
    """
    permission_classes = []  # Will use authenticated user permissions
    
    @extend_schema(
        summary="Initiate facilitator meeting with pipeline records",
        request={
            'meeting_type_id': str,
            'participant_1_record_id': str,
            'participant_2_record_id': str
        },
        responses={201: dict}
    )
    def post(self, request):
        """Initiate a facilitator meeting"""
        meeting_type_id = request.data.get('meeting_type_id')
        p1_record_id = request.data.get('participant_1_record_id')
        p2_record_id = request.data.get('participant_2_record_id')
        
        # Validate inputs
        if not all([meeting_type_id, p1_record_id, p2_record_id]):
            return Response(
                {'error': 'meeting_type_id, participant_1_record_id, and participant_2_record_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if p1_record_id == p2_record_id:
            return Response(
                {'error': 'Participants must be different'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get meeting type
            meeting_type = get_object_or_404(
                MeetingType,
                id=meeting_type_id,
                user=request.user,
                meeting_mode='facilitator',
                is_active=True
            )
            
            # Get pipeline records
            pipeline = Pipeline.objects.get(id=meeting_type.pipeline_id)
            p1_record = Record.objects.get(id=p1_record_id, pipeline=pipeline)
            p2_record = Record.objects.get(id=p2_record_id, pipeline=pipeline)
            
            # Get pipeline fields to properly identify email and name fields
            from pipelines.models import Field
            from pipelines.form_generation import DynamicFormGenerator
            
            # Get the actual form fields based on meeting type configuration
            generator = DynamicFormGenerator(pipeline)
            
            # Use the same logic as the booking form - get fields from stage or public
            if meeting_type.pipeline_stage:
                form_schema = generator.generate_form(mode='stage_public', stage=meeting_type.pipeline_stage)
            else:
                form_schema = generator.generate_form(mode='public_filtered')
            
            # If meeting type has specific field selections, use those
            if meeting_type.booking_form_config and meeting_type.booking_form_config.get('selected_fields'):
                selected_field_ids = meeting_type.booking_form_config.get('selected_fields', [])
                form_fields = [
                    field for field in form_schema.fields 
                    if str(field.field_id) in selected_field_ids or field.field_slug in selected_field_ids
                ]
            else:
                form_fields = form_schema.fields
            
            # Build field info map for quick lookup
            field_info = {field.field_slug: field for field in form_fields}
            
            # Get all pipeline fields for type checking
            pipeline_fields = Field.objects.filter(pipeline=pipeline)
            field_type_map = {field.slug: field.field_type for field in pipeline_fields}
            
            import logging
            logger = logging.getLogger(__name__)
            
            # Extract participant 1 info
            p1_data = p1_record.data
            p1_email = None
            p1_name = None
            
            logger.info(f"P1 Record data: {p1_data}")
            logger.info(f"Form fields: {[f.field_slug for f in form_fields]}")
            
            # Extract name intelligently based on available fields
            name_parts = []
            
            # Check for specific name fields in order of preference
            # 1. Look for first_name and last_name
            first_name_raw = p1_data.get('first_name')
            last_name_raw = p1_data.get('last_name')
            
            logger.info(f"P1 first_name raw value: {repr(first_name_raw)}")
            logger.info(f"P1 last_name raw value: {repr(last_name_raw)}")
            
            first_name = str(first_name_raw).strip() if first_name_raw else ''
            last_name = str(last_name_raw).strip() if last_name_raw else ''
            
            logger.info(f"P1 first_name after processing: '{first_name}'")
            logger.info(f"P1 last_name after processing: '{last_name}'")
            
            if first_name:
                name_parts.append(first_name)
            if last_name:
                name_parts.append(last_name)
            
            # 2. If we have name parts, combine them
            if name_parts:
                p1_name = ' '.join(name_parts)
                logger.info(f"P1 combined name from parts: '{p1_name}'")
            else:
                # 3. Look for a full_name or name field
                for field_slug in ['full_name', 'name']:
                    if field_slug in p1_data and p1_data[field_slug]:
                        p1_name = p1_data[field_slug]
                        break
                
                # 4. If still no name, look for any field with 'name' in the slug
                if not p1_name:
                    for field_slug, value in p1_data.items():
                        if value and 'name' in field_slug.lower() and field_type_map.get(field_slug) in ['text', 'textarea', None]:
                            p1_name = str(value)
                            break
            
            # Extract email - look for field type 'email' or field slug containing 'email'
            for field_slug, value in p1_data.items():
                if value:
                    field_type = field_type_map.get(field_slug, '')
                    if field_type == 'email' or 'email' in field_slug.lower():
                        p1_email = value
                        break
            
            logger.info(f"P1 extracted name: '{p1_name}', email: '{p1_email}'")
            
            # Extract participant 2 info using same logic
            p2_data = p2_record.data
            p2_email = None
            p2_name = None
            
            logger.info(f"P2 Record data: {p2_data}")
            
            # Extract name intelligently based on available fields
            name_parts = []
            
            # Check for specific name fields in order of preference
            # 1. Look for first_name and last_name
            first_name_raw = p2_data.get('first_name')
            last_name_raw = p2_data.get('last_name')
            
            logger.info(f"P2 first_name raw value: {repr(first_name_raw)}")
            logger.info(f"P2 last_name raw value: {repr(last_name_raw)}")
            
            first_name = str(first_name_raw).strip() if first_name_raw else ''
            last_name = str(last_name_raw).strip() if last_name_raw else ''
            
            logger.info(f"P2 first_name after processing: '{first_name}'")
            logger.info(f"P2 last_name after processing: '{last_name}'")
            
            if first_name:
                name_parts.append(first_name)
            if last_name:
                name_parts.append(last_name)
            
            # 2. If we have name parts, combine them
            if name_parts:
                p2_name = ' '.join(name_parts)
                logger.info(f"P2 combined name from parts: '{p2_name}'")
            else:
                # 3. Look for a full_name or name field
                for field_slug in ['full_name', 'name']:
                    if field_slug in p2_data and p2_data[field_slug]:
                        p2_name = p2_data[field_slug]
                        break
                
                # 4. If still no name, look for any field with 'name' in the slug
                if not p2_name:
                    for field_slug, value in p2_data.items():
                        if value and 'name' in field_slug.lower() and field_type_map.get(field_slug) in ['text', 'textarea', None]:
                            p2_name = str(value)
                            break
            
            # Extract email - look for field type 'email' or field slug containing 'email'
            for field_slug, value in p2_data.items():
                if value:
                    field_type = field_type_map.get(field_slug, '')
                    if field_type == 'email' or 'email' in field_slug.lower():
                        p2_email = value
                        break
            
            logger.info(f"P2 extracted name: '{p2_name}', email: '{p2_email}'")
            
            if not p1_email or not p2_email:
                return Response(
                    {'error': 'Both participants must have email addresses in their records'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get expiry time from settings
            facilitator_settings = meeting_type.facilitator_settings or {}
            expiry_hours = facilitator_settings.get('link_expiry_hours', 72)
            
            # Create FacilitatorBooking
            with transaction.atomic():
                # Log what we're about to save
                logger.info(f"Creating booking with P1 name: '{p1_name}', P2 name: '{p2_name}'")
                
                booking = FacilitatorBooking.objects.create(
                    meeting_type=meeting_type,
                    facilitator=request.user,
                    
                    # Participant 1
                    participant_1_record_id=str(p1_record.id),
                    participant_1_email=p1_email,
                    participant_1_name=p1_name or '',
                    participant_1_data=p1_record.data,
                    
                    # Participant 2
                    participant_2_record_id=str(p2_record.id),
                    participant_2_email=p2_email,
                    participant_2_name=p2_name or '',
                    participant_2_data=p2_record.data,
                    
                    # Status and expiry
                    status='pending_p1',
                    expires_at=timezone.now() + timezone.timedelta(hours=expiry_hours)
                )
                
                # Send email to Participant 1
                from .tasks import send_facilitator_p1_invitation
                send_facilitator_p1_invitation.delay(
                    str(booking.id),
                    request.user.tenant.schema_name if hasattr(request.user, 'tenant') else None
                )
                
                booking.invitation_sent_at = timezone.now()
                booking.save(update_fields=['invitation_sent_at'])
            
            # Build response
            return Response({
                'success': True,
                'booking_id': str(booking.id),
                'participant_1': {
                    'email': p1_email,
                    'name': p1_name,
                    'token_url': request.build_absolute_uri(
                        f'/book/facilitator/{booking.participant_1_token}/participant1/'
                    )
                },
                'participant_2': {
                    'email': p2_email,
                    'name': p2_name
                },
                'expires_at': booking.expires_at.isoformat(),
                'message': f'Invitation sent to {p1_name or p1_email}'
            }, status=status.HTTP_201_CREATED)
            
        except Pipeline.DoesNotExist:
            return Response(
                {'error': 'Pipeline not found for meeting type'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Record.DoesNotExist:
            return Response(
                {'error': 'One or more participant records not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Failed to initiate facilitator meeting: {e}")
            return Response(
                {'error': 'Failed to initiate meeting'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FacilitatorBookingConfigView(APIView):
    """
    Get configuration for facilitator meeting type
    Returns allowed durations, locations, and other settings
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Get facilitator meeting configuration",
        responses={200: dict}
    )
    def get(self, request, username, slug):
        """Get facilitator meeting type configuration"""
        user = get_user_by_slug(username)
        meeting_type = get_object_or_404(
            MeetingType,
            user=user,
            slug=slug,
            meeting_mode='facilitator',
            is_active=True
        )
        
        facilitator_settings = meeting_type.facilitator_settings or {}
        
        # Determine available conference providers based on calendar connection
        available_providers = ['phone', 'in_person', 'custom']
        if meeting_type.calendar_connection:
            if meeting_type.calendar_connection.channel_type == 'gmail':
                available_providers.append('google_meet')
            elif meeting_type.calendar_connection.channel_type == 'outlook':
                available_providers.append('teams')
        
        # Filter location options based on what's configured and available
        configured_locations = facilitator_settings.get('location_options', available_providers)
        location_options = [loc for loc in configured_locations if loc in available_providers]
        
        return Response({
            'meeting_type': {
                'name': meeting_type.name,
                'description': meeting_type.description,
                'host': meeting_type.user.get_full_name() or meeting_type.user.username
            },
            'facilitator_settings': {
                'max_time_options': facilitator_settings.get('max_time_options', 3),
                'participant_1_label': facilitator_settings.get('participant_1_label', 'First Participant'),
                'participant_2_label': facilitator_settings.get('participant_2_label', 'Second Participant'),
                'include_facilitator': facilitator_settings.get('include_facilitator', True),
                'allow_duration_selection': facilitator_settings.get('allow_duration_selection', True),
                'duration_options': facilitator_settings.get('duration_options', [30, 60, 90]),
                'default_duration': meeting_type.duration_minutes,
                'allow_location_selection': facilitator_settings.get('allow_location_selection', True),
                'location_options': location_options,
                'link_expiry_hours': facilitator_settings.get('link_expiry_hours', 72)
            }
        })


class FacilitatorBookingAvailabilityView(APIView):
    """
    Check availability for a specific duration
    Used by Participant 1 when duration changes
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Get available slots for selected duration",
        request={'date': str, 'duration_minutes': int},
        responses={200: dict}
    )
    def post(self, request, username, slug):
        """Get available slots for a specific duration"""
        user = get_user_by_slug(username)
        meeting_type = get_object_or_404(
            MeetingType,
            user=user,
            slug=slug,
            meeting_mode='facilitator',
            is_active=True
        )
        
        # Get parameters
        date = request.data.get('date')
        duration_minutes = request.data.get('duration_minutes')
        
        if not date or not duration_minutes:
            return Response(
                {'error': 'Date and duration_minutes are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Parse date and create date range for the day
            from datetime import datetime, time, timedelta
            import pytz
            
            # Parse the date string - handle both ISO format and simple date format
            if 'T' in date:
                request_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            else:
                request_date = datetime.strptime(date, '%Y-%m-%d')
            
            # For facilitator meetings, generate time slots for the entire day
            # Participant 1 can choose any time, not restricted by facilitator's availability
            
            # Use a default timezone (can be overridden by participant's timezone if provided)
            timezone_str = request.data.get('timezone', 'UTC')
            tz = pytz.timezone(timezone_str)
            
            # Generate slots from 8 AM to 8 PM in 30-minute intervals
            # This gives Participant 1 flexibility to choose any reasonable time
            slot_interval = 30  # minutes
            start_hour = 8  # 8 AM
            end_hour = 20  # 8 PM
            
            # Create datetime objects for start and end of available window
            start_of_window = tz.localize(
                datetime.combine(request_date.date(), time(start_hour, 0))
            )
            end_of_window = tz.localize(
                datetime.combine(request_date.date(), time(end_hour, 0))
            )
            
            # Generate all possible slots
            available_slots = []
            current_time = start_of_window
            
            while current_time + timedelta(minutes=duration_minutes) <= end_of_window:
                slot = {
                    'start': current_time.isoformat(),
                    'end': (current_time + timedelta(minutes=duration_minutes)).isoformat()
                }
                available_slots.append(slot)
                current_time += timedelta(minutes=slot_interval)
            
            # Note: We're NOT filtering by facilitator availability or existing bookings
            # because in facilitator mode, Participant 1 proposes times and Participant 2 chooses
            # The actual meeting is only scheduled after Participant 2 confirms
            
            return Response({
                'slots': available_slots,
                'duration_minutes': duration_minutes,
                'timezone': timezone_str
            })
            
        except Exception as e:
            logger.error(f"Failed to get availability: {e}")
            return Response(
                {'error': 'Failed to calculate availability'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FacilitatorBookingStep1View(APIView):
    """
    Handle Participant 1's submission
    Creates FacilitatorBooking and sends invitation to Participant 2
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Submit Participant 1 selections",
        request=dict,
        responses={201: dict}
    )
    def post(self, request, username, slug):
        """Process Participant 1's selections"""
        user = get_user_by_slug(username)
        meeting_type = get_object_or_404(
            MeetingType,
            user=user,
            slug=slug,
            meeting_mode='facilitator',
            is_active=True
        )
        
        # Extract data from request
        participant_info = request.data.get('participant_info', {})
        meeting_params = request.data.get('meeting_params', {})
        selected_slots = request.data.get('selected_slots', [])
        
        # Validate required fields
        if not participant_info.get('email'):
            return Response(
                {'error': 'Participant 1 email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not participant_info.get('participant_2_email'):
            return Response(
                {'error': 'Participant 2 email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not meeting_params.get('duration'):
            return Response(
                {'error': 'Meeting duration is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not meeting_params.get('location_type'):
            return Response(
                {'error': 'Meeting location type is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not selected_slots:
            return Response(
                {'error': 'At least one time slot must be selected'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate slot count
        facilitator_settings = meeting_type.facilitator_settings or {}
        max_slots = facilitator_settings.get('max_time_options', 3)
        if len(selected_slots) > max_slots:
            return Response(
                {'error': f'Maximum {max_slots} time slots allowed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Process the booking
            processor = FacilitatorBookingProcessor(meeting_type)
            booking = processor.process_facilitator_step1_sync(
                participant_info,
                meeting_params,
                selected_slots
            )
            
            return Response({
                'success': True,
                'booking_id': str(booking.id),
                'participant_2_email': booking.participant_2_email,
                'shareable_link': booking.get_shareable_link(request),
                'expires_at': booking.expires_at.isoformat(),
                'message': f'Invitation sent to {booking.participant_2_email}. They have {facilitator_settings.get("link_expiry_hours", 72)} hours to select a time.',
                'selected_slots': booking.selected_slots,
                'tracking': {
                    'invitation_sent': True,
                    'sent_at': booking.invitation_sent_at.isoformat() if booking.invitation_sent_at else None
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Failed to process facilitator booking step 1: {e}")
            return Response(
                {'error': 'Failed to process booking. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FacilitatorParticipant1View(APIView):
    """
    View for Participant 1 to configure meeting and select time slots
    Accessed via participant_1_token
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Get booking details for Participant 1",
        responses={200: dict}
    )
    def get(self, request, token):
        """Get booking details using P1 token"""
        try:
            booking = get_object_or_404(FacilitatorBooking, participant_1_token=token)
            
            # Debug logging for retrieved booking
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Retrieved booking ID: {booking.id}")
            logger.info(f"Booking P1 name from DB: '{booking.participant_1_name}'")
            logger.info(f"Booking P2 name from DB: '{booking.participant_2_name}'")
            
            # Check if expired
            if booking.is_expired():
                return Response(
                    {'error': 'This booking link has expired', 'status': 'expired'},
                    status=status.HTTP_410_GONE
                )
            
            # Check status
            if booking.status != 'pending_p1':
                return Response(
                    {'error': 'You have already configured this meeting', 'status': booking.status},
                    status=status.HTTP_410_GONE
                )
            
            meeting_type = booking.meeting_type
            facilitator_settings = meeting_type.facilitator_settings or {}
            
            # Get available conference providers based on calendar connection
            available_providers = ['phone', 'in_person', 'custom']
            if meeting_type.calendar_connection:
                if meeting_type.calendar_connection.channel_type == 'gmail':
                    available_providers.append('google_meet')
                elif meeting_type.calendar_connection.channel_type == 'outlook':
                    available_providers.append('teams')
            
            # Filter location options
            configured_locations = facilitator_settings.get('location_options', available_providers)
            location_options = [loc for loc in configured_locations if loc in available_providers]
            
            # Get tenant organization info (following the same pattern as PublicMeetingTypeSerializer)
            from django.db import connection
            
            organization_data = {}
            
            # Get the current tenant
            if hasattr(connection, 'tenant'):
                tenant = connection.tenant
                
                # Build logo URL properly
                logo_url = ''
                if hasattr(tenant, 'organization_logo') and tenant.organization_logo:
                    try:
                        # Build absolute URL if possible
                        if request and tenant.organization_logo:
                            logo_url = request.build_absolute_uri(tenant.organization_logo.url)
                        elif tenant.organization_logo:
                            logo_url = tenant.organization_logo.url
                    except (ValueError, AttributeError):
                        # If organization_logo doesn't have a file, it might raise an error
                        logo_url = ''
                
                # Get organization details from tenant model fields
                organization_data = {
                    'name': tenant.name if hasattr(tenant, 'name') else '',
                    'logo': logo_url,
                    'website': tenant.organization_website if hasattr(tenant, 'organization_website') else ''
                }
            
            # Log what we're about to return
            logger.info(f"Returning P1 name: '{booking.participant_1_name}'")
            logger.info(f"Returning P2 name: '{booking.participant_2_name}'")
            
            return Response({
                'booking_id': str(booking.id),
                'status': booking.status,
                'meeting_type': {
                    'name': meeting_type.name,
                    'description': meeting_type.description,
                    'pipeline_id': meeting_type.pipeline_id
                },
                'facilitator': {
                    'name': booking.facilitator.get_full_name() or booking.facilitator.username,
                    'email': booking.facilitator.email
                },
                'participant_1': {
                    'name': booking.participant_1_name,
                    'email': booking.participant_1_email
                },
                'participant_2': {
                    'name': booking.participant_2_name,
                    'email': booking.participant_2_email
                },
                'settings': {
                    'duration_options': facilitator_settings.get('duration_options', [30, 60, 90]),
                    'default_duration': meeting_type.duration_minutes,
                    'location_options': location_options,
                    'max_time_options': facilitator_settings.get('max_time_options', 3)
                },
                'organization': organization_data,
                'expires_at': booking.expires_at.isoformat()
            })
            
        except FacilitatorBooking.DoesNotExist:
            return Response(
                {'error': 'Invalid booking link'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        summary="Submit Participant 1 configuration",
        request=dict,
        responses={200: dict}
    )
    def post(self, request, token):
        """Submit P1's configuration and time slots"""
        try:
            booking = get_object_or_404(FacilitatorBooking, participant_1_token=token)
            
            # Validate booking status
            if booking.is_expired():
                return Response(
                    {'error': 'This booking link has expired'},
                    status=status.HTTP_410_GONE
                )
            
            if booking.status != 'pending_p1':
                return Response(
                    {'error': 'You have already configured this meeting'},
                    status=status.HTTP_410_GONE
                )
            
            # Extract data
            duration_minutes = request.data.get('duration_minutes')
            location_type = request.data.get('location_type')
            location_details = request.data.get('location_details', {})
            selected_slots = request.data.get('selected_slots', [])
            message = request.data.get('message', '')
            
            # Validate required fields
            if not all([duration_minutes, location_type, selected_slots]):
                return Response(
                    {'error': 'duration_minutes, location_type, and selected_slots are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate slot count
            facilitator_settings = booking.meeting_type.facilitator_settings or {}
            max_slots = facilitator_settings.get('max_time_options', 3)
            if len(selected_slots) > max_slots:
                return Response(
                    {'error': f'Maximum {max_slots} time slots allowed'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update booking
            booking.selected_duration_minutes = duration_minutes
            booking.selected_location_type = location_type
            booking.selected_location_details = location_details
            booking.selected_slots = selected_slots
            booking.participant_1_message = message
            booking.participant_1_completed_at = timezone.now()
            booking.status = 'pending_p2'
            booking.save()
            
            # Send email to Participant 2
            from .tasks import send_facilitator_p2_invitation
            send_facilitator_p2_invitation.delay(
                str(booking.id),
                booking.facilitator.tenant.schema_name if hasattr(booking.facilitator, 'tenant') else None
            )
            
            return Response({
                'success': True,
                'message': f'Configuration saved. Invitation sent to {booking.participant_2_name or booking.participant_2_email}',
                'participant_2_token_url': request.build_absolute_uri(
                    f'/book/facilitator/{booking.participant_2_token}/'
                )
            })
            
        except FacilitatorBooking.DoesNotExist:
            return Response(
                {'error': 'Invalid booking link'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Failed to process P1 configuration: {e}")
            return Response(
                {'error': 'Failed to save configuration'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FacilitatorBookingDetailView(APIView):
    """
    Get facilitator booking details for Participant 2
    Accessed via unique token
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Get facilitator booking details",
        responses={200: dict}
    )
    def get(self, request, token):
        """Get booking details using token"""
        try:
            # Try participant_2_token first (new flow), fall back to unique_token (legacy)
            try:
                booking = FacilitatorBooking.objects.get(participant_2_token=token)
            except FacilitatorBooking.DoesNotExist:
                booking = get_object_or_404(FacilitatorBooking, unique_token=token)
            
            # Check if expired
            if booking.is_expired():
                return Response(
                    {'error': 'This booking link has expired', 'status': 'expired'},
                    status=status.HTTP_410_GONE
                )
            
            # Check if already completed
            if booking.status == 'completed':
                return Response(
                    {'error': 'This meeting has already been scheduled', 'status': 'completed'},
                    status=status.HTTP_410_GONE
                )
            
            # Mark as opened if first time
            if not booking.invitation_opened_at:
                booking.invitation_opened_at = timezone.now()
                booking.save(update_fields=['invitation_opened_at'])
            
            # Get meeting type info
            meeting_type = booking.meeting_type
            facilitator_settings = meeting_type.facilitator_settings or {}
            
            # Get tenant organization info
            from django.db import connection
            organization_data = None
            if hasattr(connection, 'tenant'):
                tenant = connection.tenant
                logo_url = ''
                if hasattr(tenant, 'organization_logo') and tenant.organization_logo:
                    try:
                        if request and tenant.organization_logo:
                            logo_url = request.build_absolute_uri(tenant.organization_logo.url)
                        elif tenant.organization_logo:
                            logo_url = tenant.organization_logo.url
                    except (ValueError, AttributeError):
                        logo_url = ''
                
                organization_data = {
                    'name': tenant.name if hasattr(tenant, 'name') else '',
                    'logo': logo_url,
                    'website': tenant.organization_website if hasattr(tenant, 'organization_website') else ''
                }
            
            return Response({
                'status': booking.status,
                'meeting_details': {
                    'name': meeting_type.name,
                    'description': meeting_type.description,
                    'duration_minutes': booking.selected_duration_minutes,
                    'location_type': booking.selected_location_type,
                    'location_details': booking.selected_location_details
                },
                'facilitator': {
                    'name': booking.facilitator.get_full_name() or booking.facilitator.username,
                    'email': booking.facilitator.email
                },
                'participant_1': {
                    'name': booking.participant_1_name,
                    'message': booking.participant_1_message
                },
                'participant_2': {
                    'email': booking.participant_2_email,
                    'name': booking.participant_2_name
                },
                'selected_slots': booking.selected_slots,
                'expires_at': booking.expires_at.isoformat(),
                'labels': {
                    'participant_1': facilitator_settings.get('participant_1_label', 'First Participant'),
                    'participant_2': facilitator_settings.get('participant_2_label', 'Second Participant')
                },
                'pipeline_id': meeting_type.pipeline_id if meeting_type.pipeline_id else None,
                'organization': organization_data
            })
            
        except FacilitatorBooking.DoesNotExist:
            return Response(
                {'error': 'Invalid booking link'},
                status=status.HTTP_404_NOT_FOUND
            )


class FacilitatorBookingStep2View(APIView):
    """
    Handle Participant 2's final selection
    Creates the actual meeting and sends confirmations
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Confirm Participant 2 selection",
        request=dict,
        responses={201: dict}
    )
    def post(self, request, token):
        """Process Participant 2's final selection"""
        try:
            # Try participant_2_token first (new flow), fall back to unique_token (legacy)
            try:
                booking = FacilitatorBooking.objects.get(participant_2_token=token)
            except FacilitatorBooking.DoesNotExist:
                booking = get_object_or_404(FacilitatorBooking, unique_token=token)
            
            # Validate booking status
            if booking.is_expired():
                return Response(
                    {'error': 'This booking link has expired'},
                    status=status.HTTP_410_GONE
                )
            
            if booking.status != 'pending_p2':
                return Response(
                    {'error': 'This meeting has already been scheduled'},
                    status=status.HTTP_410_GONE
                )
            
            # Extract data
            participant_info = request.data.get('participant_info', {})
            selected_slot = request.data.get('selected_slot')
            
            if not selected_slot:
                return Response(
                    {'error': 'Selected slot is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Process the final booking
            processor = FacilitatorBookingProcessor(booking.meeting_type)
            meeting = processor.process_facilitator_step2_sync(
                booking,
                participant_info,
                selected_slot
            )
            
            return Response({
                'success': True,
                'meeting_id': str(meeting.id),
                'confirmation': {
                    'meeting_type': booking.meeting_type.name,
                    'start_time': meeting.start_time.isoformat(),
                    'end_time': meeting.end_time.isoformat(),
                    'timezone': meeting.timezone,
                    'location_type': booking.selected_location_type,
                    'meeting_url': meeting.meeting_url,
                    'location': meeting.meeting_location,
                    'participants': [
                        booking.participant_1_name,
                        booking.participant_2_name
                    ],
                    'facilitator': booking.facilitator.get_full_name() or booking.facilitator.username
                }
            }, status=status.HTTP_201_CREATED)
            
        except FacilitatorBooking.DoesNotExist:
            return Response(
                {'error': 'Invalid booking link'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Failed to process facilitator booking step 2: {e}")
            return Response(
                {'error': 'Failed to complete booking. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )