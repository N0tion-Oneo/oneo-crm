"""
Public API views for scheduling
Handles unauthenticated booking operations for external users
"""
import logging
import pytz
from datetime import datetime
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema, OpenApiParameter
from asgiref.sync import async_to_sync

from .models import SchedulingLink, SchedulingProfile, ScheduledMeeting, MeetingType
from django.contrib.auth import get_user_model

User = get_user_model()
from .serializers import (
    PublicSchedulingLinkSerializer,
    BookingRequestSerializer,
    AvailabilityRequestSerializer,
    PublicMeetingTypeSerializer
)
from .services import AvailabilityCalculator, BookingProcessor
from pipelines.form_generation import DynamicFormGenerator

logger = logging.getLogger(__name__)


def get_user_by_slug(username_slug):
    """
    Get user by username slug which could be firstname-lastname or username
    """
    user = None
    
    if '-' in username_slug:
        # Could be firstname-lastname format
        parts = username_slug.split('-', 1)
        if len(parts) == 2:
            first_name = parts[0]
            last_name = parts[1]
            # Try to find user by first and last name (case-insensitive)
            try:
                user = User.objects.get(
                    first_name__iexact=first_name.replace('-', ' '),
                    last_name__iexact=last_name.replace('-', ' ')
                )
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                pass
    
    # If not found by name, try by username
    if not user:
        user = get_object_or_404(User, username=username_slug)
    
    return user


class PublicSchedulingLinkView(APIView):
    """
    Public view for scheduling link information
    No authentication required
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Get public scheduling link information",
        responses={200: PublicSchedulingLinkSerializer}
    )
    def get(self, request, slug):
        """Get public information about a scheduling link"""
        # Get the link
        link = get_object_or_404(SchedulingLink, slug=slug)
        
        # Check if link is accessible
        can_book, message = link.can_book()
        if not can_book:
            return Response(
                {'error': message},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Track view
        link.increment_view()
        
        # Return public information with request context
        serializer = PublicSchedulingLinkSerializer(link, context={'request': request})
        return Response(serializer.data)


class PublicAvailabilityView(APIView):
    """
    Public view for checking availability
    No authentication required
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Get available time slots for booking",
        request=AvailabilityRequestSerializer,
        responses={200: dict}
    )
    def post(self, request, slug):
        """Get available time slots for a scheduling link"""
        # Get the link
        link = get_object_or_404(SchedulingLink, slug=slug)
        
        # Check if link is accessible
        can_book, message = link.can_book()
        if not can_book:
            return Response(
                {'error': message},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate request data
        serializer = AvailabilityRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Get parameters
        start_date = serializer.validated_data['start_date']
        end_date = serializer.validated_data['end_date']
        duration_minutes = link.meeting_type.duration_minutes
        
        # Store the originally requested date to filter results
        requested_date = start_date.date()
        
        # Get user's scheduling profile
        try:
            profile = SchedulingProfile.objects.filter(
                user=link.meeting_type.user,
                is_active=True
            ).first()
            
            if not profile:
                return Response(
                    {'error': 'Scheduling not configured for this user'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            # Calculate availability
            calculator = AvailabilityCalculator(profile)
            slots = async_to_sync(calculator.get_available_slots)(
                start_date, end_date, duration_minutes, link
            )
            
            # Filter out already booked slots
            booked_times = ScheduledMeeting.objects.filter(
                meeting_type=link.meeting_type,
                start_time__gte=start_date,
                end_time__lte=end_date,
                status__in=['scheduled', 'confirmed', 'reminder_sent', 'in_progress']
            ).values_list('start_time', 'end_time')
            
            # Remove booked slots
            available_slots = []
            for slot in slots:
                slot_start = datetime.fromisoformat(slot['start'].replace('Z', '+00:00'))
                slot_end = datetime.fromisoformat(slot['end'].replace('Z', '+00:00'))
                
                # Ensure timezone awareness
                if slot_start.tzinfo is None:
                    slot_start = timezone.make_aware(slot_start)
                if slot_end.tzinfo is None:
                    slot_end = timezone.make_aware(slot_end)
                
                is_available = True
                for booked_start, booked_end in booked_times:
                    # Ensure booked times are timezone aware
                    if booked_start.tzinfo is None:
                        booked_start = timezone.make_aware(booked_start)
                    if booked_end.tzinfo is None:
                        booked_end = timezone.make_aware(booked_end)
                    
                    # Check for overlap
                    if not (slot_end <= booked_start or slot_start >= booked_end):
                        is_available = False
                        break
                
                if is_available:
                    available_slots.append(slot)
            
            # Filter slots to only include the requested date
            filtered_slots = []
            for slot in available_slots:
                slot_start = datetime.fromisoformat(slot['start'].replace('Z', '+00:00'))
                if slot_start.date() == requested_date:
                    filtered_slots.append(slot)
            
            logger.info(f"Filtered from {len(available_slots)} to {len(filtered_slots)} slots for date {requested_date}")
            
            # Deduplicate slots before returning
            unique_slots = []
            seen_slots = set()
            for slot in filtered_slots:
                slot_key = (slot['start'], slot['end'])
                if slot_key not in seen_slots:
                    seen_slots.add(slot_key)
                    unique_slots.append(slot)
            
            logger.info(f"After deduplication: {len(unique_slots)} unique slots being returned")
            
            return Response({
                'slots': unique_slots,
                'duration_minutes': duration_minutes,
                'timezone': profile.timezone
            })
            
        except Exception as e:
            logger.error(f"Failed to get availability: {e}")
            return Response(
                {'error': 'Failed to calculate availability'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PublicBookingView(APIView):
    """
    Public view for creating bookings
    No authentication required
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Book a meeting",
        request=BookingRequestSerializer,
        responses={201: dict}
    )
    def post(self, request, slug):
        """Create a booking for a scheduling link"""
        # Get the link
        link = get_object_or_404(SchedulingLink, slug=slug)
        
        # Check if link is accessible
        email = request.data.get('email')
        can_book, message = link.can_book(email=email)
        if not can_book:
            return Response(
                {'error': message},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check password if required
        if link.password:
            provided_password = request.data.get('password')
            if provided_password != link.password:
                return Response(
                    {'error': 'Invalid password'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        
        # Validate booking data
        serializer = BookingRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        booking_data = serializer.validated_data
        selected_slot = booking_data.pop('selected_slot')
        
        # Add metadata
        booking_data['ip_address'] = self._get_client_ip(request)
        booking_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        
        # Merge with custom booking data
        custom_data = booking_data.pop('booking_data', {})
        booking_data.update(custom_data)
        
        # Check if slot is still available
        slot_start = datetime.fromisoformat(selected_slot['start'])
        slot_end = datetime.fromisoformat(selected_slot['end'])
        
        # Check for conflicts
        conflicts = ScheduledMeeting.objects.filter(
            meeting_type=link.meeting_type,
            start_time__lt=slot_end,
            end_time__gt=slot_start,
            status__in=['scheduled', 'confirmed', 'reminder_sent', 'in_progress']
        ).exists()
        
        if conflicts:
            return Response(
                {'error': 'Selected time slot is no longer available'},
                status=status.HTTP_409_CONFLICT
            )
        
        # Process the booking
        try:
            processor = BookingProcessor(link)
            meeting = processor.process_booking_sync(
                booking_data, selected_slot
            )
            
            return Response({
                'success': True,
                'meeting_id': str(meeting.id),
                'confirmation': {
                    'meeting_type': link.meeting_type.name,
                    'start_time': meeting.start_time.isoformat(),
                    'end_time': meeting.end_time.isoformat(),
                    'timezone': meeting.timezone,
                    'location_type': link.meeting_type.location_type,
                    'meeting_url': meeting.meeting_url,
                    'location': meeting.meeting_location,
                    'host': link.meeting_type.user.get_full_name() or link.meeting_type.user.username
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Failed to process booking: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to process booking. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PublicMeetingStatusView(APIView):
    """
    Public view for checking meeting status
    Limited information for privacy
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Check meeting status",
        responses={200: dict}
    )
    def get(self, request, meeting_id):
        """Get basic meeting status"""
        try:
            meeting = ScheduledMeeting.objects.get(id=meeting_id)
            
            # Return limited information
            return Response({
                'status': meeting.status,
                'start_time': meeting.start_time.isoformat(),
                'end_time': meeting.end_time.isoformat(),
                'timezone': meeting.timezone,
                'can_cancel': meeting.can_cancel(),
                'can_reschedule': meeting.can_reschedule()
            })
            
        except ScheduledMeeting.DoesNotExist:
            return Response(
                {'error': 'Meeting not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class PublicMeetingCancelView(APIView):
    """
    Public view for cancelling meetings
    Requires meeting ID and email verification
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Cancel a meeting",
        request={'email': str, 'reason': str},
        responses={200: dict}
    )
    def post(self, request, meeting_id):
        """Cancel a meeting"""
        try:
            meeting = ScheduledMeeting.objects.get(id=meeting_id)
            
            # Verify email matches
            email = request.data.get('email')
            if email != meeting.participant.email:
                return Response(
                    {'error': 'Email verification failed'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check if can cancel
            if not meeting.can_cancel():
                return Response(
                    {'error': 'Meeting cannot be cancelled at this time'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Cancel the meeting
            reason = request.data.get('reason', 'Cancelled by participant')
            meeting.cancel(reason=reason)
            
            # TODO: Send cancellation notifications
            
            return Response({
                'success': True,
                'message': 'Meeting has been cancelled'
            })
            
        except ScheduledMeeting.DoesNotExist:
            return Response(
                {'error': 'Meeting not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class PublicMeetingTypeView(APIView):
    """
    Public view for meeting type information using clean URLs
    No authentication required
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Get public meeting type information",
        responses={200: PublicMeetingTypeSerializer}
    )
    def get(self, request, username, slug):
        """Get public information about a meeting type"""
        # Get user by username or firstname-lastname format
        user = get_user_by_slug(username)
        
        meeting_type = get_object_or_404(
            MeetingType, 
            user=user, 
            slug=slug,
            is_active=True
        )
        
        # Return public information with request context
        serializer = PublicMeetingTypeSerializer(meeting_type, context={'request': request})
        return Response(serializer.data)


class PublicMeetingTypeFormView(APIView):
    """
    Public view for getting dynamic form schema for meeting type bookings
    No authentication required
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Get dynamic form schema for meeting type",
        responses={200: dict}
    )
    def get(self, request, username, slug):
        """Get dynamic form schema based on meeting type's configuration"""
        # Get user by username or firstname-lastname format
        user = get_user_by_slug(username)
        
        meeting_type = get_object_or_404(
            MeetingType, 
            user=user, 
            slug=slug,
            is_active=True
        )
        
        # Meeting type MUST have a pipeline configuration
        if not meeting_type.pipeline:
            return Response(
                {'error': 'Meeting type is not configured with a pipeline'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate dynamic form based on the meeting type's pipeline and stage configuration
        generator = DynamicFormGenerator(meeting_type.pipeline)
        
        # Use the stage specified in meeting type, or fall back to public_filtered mode
        form_mode = 'stage_public' if meeting_type.pipeline_stage else 'public_filtered'
        form_schema = generator.generate_form(
            mode=form_mode,
            stage=meeting_type.pipeline_stage if meeting_type.pipeline_stage else None
        )
        
        # Check if meeting type has specific field selections in booking_form_config
        if meeting_type.booking_form_config and meeting_type.booking_form_config.get('selected_fields'):
            # Filter to only include selected fields
            selected_field_ids = meeting_type.booking_form_config.get('selected_fields', [])
            
            # Filter fields to only those selected in configuration
            filtered_fields = [
                field for field in form_schema.fields 
                if str(field.field_id) in selected_field_ids or field.field_slug in selected_field_ids
            ]
        else:
            # Use all public fields from the stage (or all public fields if no stage)
            filtered_fields = form_schema.fields
        
        # Update required fields based on meeting type configuration
        if meeting_type.required_fields:
            for field in filtered_fields:
                if field.field_slug in meeting_type.required_fields:
                    field.is_required = True
        
        # Convert to dict format for API response
        response_fields = [
            {
                'field_id': field.field_id,
                'field_slug': field.field_slug,
                'field_name': field.display_name,
                'field_type': field.field_type,
                'is_required': field.is_required if field.field_slug not in (meeting_type.required_fields or []) else True,
                'is_visible': field.is_visible,
                'display_order': field.display_order,
                'help_text': field.help_text,
                'placeholder': field.placeholder,
                'field_config': field.field_config,
                'validation_rules': field.form_validation_rules,
                'business_rules': field.business_rules
            }
            for field in filtered_fields
        ]
        
        # Add custom questions from meeting type configuration
        for idx, question in enumerate(meeting_type.custom_questions or []):
            response_fields.append({
                'field_slug': question.get('slug', f'custom_{idx}'),
                'field_name': question.get('label', f'Custom Question {idx + 1}'),
                'field_type': question.get('type', 'text'),
                'is_required': question.get('required', False),
                'display_order': len(response_fields) + idx + 1,
                'help_text': question.get('help_text', ''),
                'placeholder': question.get('placeholder', ''),
                'is_custom': True
            })
        
        return Response({
            'fields': response_fields,
            'pipeline_id': str(meeting_type.pipeline.id),
            'pipeline_name': meeting_type.pipeline.name,
            'stage': meeting_type.pipeline_stage,
            'total_fields': len(response_fields),
            'required_fields': len([f for f in response_fields if f['is_required']])
        })


class PublicMeetingTypeAvailabilityView(APIView):
    """
    Public view for checking meeting type availability
    No authentication required
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Get available time slots for meeting type",
        request=AvailabilityRequestSerializer,
        responses={200: dict}
    )
    def post(self, request, username, slug):
        """Get available time slots for a meeting type"""
        # Get user by username or firstname-lastname format
        user = get_user_by_slug(username)
        meeting_type = get_object_or_404(
            MeetingType,
            user=user,
            slug=slug,
            is_active=True
        )
        
        # Validate request data
        serializer = AvailabilityRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Get parameters
        start_date = serializer.validated_data['start_date']
        end_date = serializer.validated_data['end_date']
        user_timezone = serializer.validated_data.get('timezone', 'UTC')
        duration_minutes = meeting_type.duration_minutes
        
        # Get the profile to determine the timezone
        profile = SchedulingProfile.objects.filter(
            user=user,
            calendar_connection=meeting_type.calendar_connection,
            is_active=True
        ).first()
        
        if not profile:
            # Create a basic profile if none exists
            profile = SchedulingProfile.objects.create(
                user=user,
                calendar_connection=meeting_type.calendar_connection
            )
        
        # Use the profile's timezone for calculations
        profile_tz = pytz.timezone(profile.timezone)
        
        # If dates come without timezone info, treat them as being in the user's timezone
        if start_date.tzinfo is None or start_date.tzinfo.utcoffset(start_date) is None:
            # Dates are naive or have no offset
            # First interpret them in the user's timezone if provided
            if user_timezone != 'UTC':
                try:
                    user_tz = pytz.timezone(user_timezone)
                    start_date = user_tz.localize(start_date.replace(tzinfo=None))
                    end_date = user_tz.localize(end_date.replace(tzinfo=None))
                    # Now convert to profile timezone for calculations
                    start_date = start_date.astimezone(profile_tz)
                    end_date = end_date.astimezone(profile_tz)
                except:
                    # Fallback to profile timezone if user timezone is invalid
                    start_date = profile_tz.localize(start_date.replace(tzinfo=None))
                    end_date = profile_tz.localize(end_date.replace(tzinfo=None))
            else:
                # No user timezone, use profile timezone
                start_date = profile_tz.localize(start_date.replace(tzinfo=None))
                end_date = profile_tz.localize(end_date.replace(tzinfo=None))
        else:
            # Dates have timezone info, convert to profile timezone
            start_date = start_date.astimezone(profile_tz)
            end_date = end_date.astimezone(profile_tz)
        
        # Store the originally requested date to filter results
        requested_date = start_date.date()
        
        # Calculate availability using the meeting type's calendar
        try:
            calculator = AvailabilityCalculator(profile, meeting_type=meeting_type)
            slots = async_to_sync(calculator.get_available_slots)(
                start_date, end_date, duration_minutes
            )
            
            # Filter out already booked slots
            booked_times = ScheduledMeeting.objects.filter(
                meeting_type=meeting_type,
                start_time__gte=start_date,
                end_time__lte=end_date,
                status__in=['scheduled', 'confirmed', 'reminder_sent', 'in_progress']
            ).values_list('start_time', 'end_time')
            
            # Remove booked slots
            available_slots = []
            for slot in slots:
                slot_start = datetime.fromisoformat(slot['start'].replace('Z', '+00:00'))
                slot_end = datetime.fromisoformat(slot['end'].replace('Z', '+00:00'))
                
                # Ensure timezone awareness
                if slot_start.tzinfo is None:
                    slot_start = timezone.make_aware(slot_start)
                if slot_end.tzinfo is None:
                    slot_end = timezone.make_aware(slot_end)
                
                is_available = True
                for booked_start, booked_end in booked_times:
                    # Ensure booked times are timezone aware
                    if booked_start.tzinfo is None:
                        booked_start = timezone.make_aware(booked_start)
                    if booked_end.tzinfo is None:
                        booked_end = timezone.make_aware(booked_end)
                    
                    # Check for overlap
                    if not (slot_end <= booked_start or slot_start >= booked_end):
                        is_available = False
                        break
                
                if is_available:
                    available_slots.append(slot)
            
            # Filter slots to only include the requested date
            filtered_slots = []
            for slot in available_slots:
                slot_start = datetime.fromisoformat(slot['start'].replace('Z', '+00:00'))
                if slot_start.date() == requested_date:
                    filtered_slots.append(slot)
            
            logger.info(f"Filtered from {len(available_slots)} to {len(filtered_slots)} slots for date {requested_date}")
            
            # Deduplicate slots before returning
            unique_slots = []
            seen_slots = set()
            for slot in filtered_slots:
                slot_key = (slot['start'], slot['end'])
                if slot_key not in seen_slots:
                    seen_slots.add(slot_key)
                    unique_slots.append(slot)
            
            logger.info(f"After deduplication: {len(unique_slots)} unique slots being returned")
            
            return Response({
                'slots': unique_slots,
                'duration_minutes': duration_minutes,
                'timezone': profile.timezone
            })
            
        except Exception as e:
            logger.error(f"Failed to get availability: {e}")
            return Response(
                {'error': 'Failed to calculate availability'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PublicMeetingTypeBookingView(APIView):
    """
    Public view for creating bookings on meeting types
    No authentication required
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Book a meeting",
        request=BookingRequestSerializer,
        responses={201: dict}
    )
    def post(self, request, username, slug):
        """Create a booking for a meeting type"""
        # Get user by username or firstname-lastname format
        user = get_user_by_slug(username)
        meeting_type = get_object_or_404(
            MeetingType,
            user=user,
            slug=slug,
            is_active=True
        )
        
        # Validate booking data
        serializer = BookingRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        booking_data = serializer.validated_data
        selected_slot = booking_data.pop('selected_slot')
        
        # Add metadata
        booking_data['ip_address'] = self._get_client_ip(request)
        booking_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        
        # Merge with custom booking data
        custom_data = booking_data.pop('booking_data', {})
        booking_data.update(custom_data)
        
        # Check if slot is still available
        slot_start = datetime.fromisoformat(selected_slot['start'])
        slot_end = datetime.fromisoformat(selected_slot['end'])
        
        # Check for conflicts
        conflicts = ScheduledMeeting.objects.filter(
            meeting_type=meeting_type,
            start_time__lt=slot_end,
            end_time__gt=slot_start,
            status__in=['scheduled', 'confirmed', 'reminder_sent', 'in_progress']
        ).exists()
        
        if conflicts:
            return Response(
                {'error': 'Selected time slot is no longer available'},
                status=status.HTTP_409_CONFLICT
            )
        
        # Process the booking
        try:
            processor = BookingProcessor(meeting_type=meeting_type)
            meeting = processor.process_booking_sync(
                booking_data, selected_slot
            )
            
            return Response({
                'success': True,
                'meeting_id': str(meeting.id),
                'confirmation': {
                    'meeting_type': meeting_type.name,
                    'start_time': meeting.start_time.isoformat(),
                    'end_time': meeting.end_time.isoformat(),
                    'timezone': meeting.timezone,
                    'location_type': meeting_type.location_type,
                    'meeting_url': meeting.meeting_url,
                    'location': meeting.meeting_location,
                    'host': user.get_full_name() or user.username
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Failed to process booking: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to process booking. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PublicMeetingRescheduleView(APIView):
    """
    Public view for rescheduling meetings
    Requires meeting ID and email verification
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Request to reschedule a meeting",
        request={'email': str, 'new_slot': dict, 'reason': str},
        responses={200: dict}
    )
    def post(self, request, meeting_id):
        """Request to reschedule a meeting"""
        try:
            meeting = ScheduledMeeting.objects.get(id=meeting_id)
            
            # Verify email matches
            email = request.data.get('email')
            if email != meeting.participant.email:
                return Response(
                    {'error': 'Email verification failed'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check if can reschedule
            if not meeting.can_reschedule():
                return Response(
                    {'error': 'Meeting cannot be rescheduled at this time'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get new slot
            new_slot = request.data.get('new_slot')
            if not new_slot:
                return Response(
                    {'error': 'New time slot required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                slot_start = datetime.fromisoformat(new_slot['start'])
                slot_end = datetime.fromisoformat(new_slot['end'])
            except (KeyError, ValueError):
                return Response(
                    {'error': 'Invalid time slot format'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if new slot is available
            conflicts = ScheduledMeeting.objects.filter(
                meeting_type=meeting.meeting_type,
                start_time__lt=slot_end,
                end_time__gt=slot_start,
                status__in=['scheduled', 'confirmed', 'reminder_sent', 'in_progress']
            ).exclude(id=meeting.id).exists()
            
            if conflicts:
                return Response(
                    {'error': 'Selected time slot is not available'},
                    status=status.HTTP_409_CONFLICT
                )
            
            # Create new meeting
            new_meeting = ScheduledMeeting.objects.create(
                meeting_type=meeting.meeting_type,
                scheduling_link=meeting.scheduling_link,
                conversation=meeting.conversation,
                participant=meeting.participant,
                host=meeting.host,
                record=meeting.record,
                start_time=slot_start,
                end_time=slot_end,
                timezone=meeting.timezone,
                booking_data=meeting.booking_data,
                status='scheduled'
            )
            
            # Mark old meeting as rescheduled
            meeting.status = 'rescheduled'
            meeting.rescheduled_to = new_meeting
            meeting.save(update_fields=['status', 'rescheduled_to'])
            
            # TODO: Send rescheduling notifications
            
            return Response({
                'success': True,
                'message': 'Meeting has been rescheduled',
                'new_meeting_id': str(new_meeting.id),
                'confirmation': {
                    'start_time': new_meeting.start_time.isoformat(),
                    'end_time': new_meeting.end_time.isoformat(),
                    'timezone': new_meeting.timezone
                }
            })
            
        except ScheduledMeeting.DoesNotExist:
            return Response(
                {'error': 'Meeting not found'},
                status=status.HTTP_404_NOT_FOUND
            )