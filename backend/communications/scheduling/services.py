"""
Scheduling services for availability calculation and booking management
Integrates with UniPile calendar and pipeline systems
"""
import logging
import pytz
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Dict, List, Any, Optional, Tuple
from django.utils import timezone
from django.db import transaction
from asgiref.sync import sync_to_async, async_to_sync

from communications.models import (
    Channel, Conversation, Participant, Message, ChannelType, 
    UserChannelConnection, ConversationParticipant,
    MessageDirection, MessageStatus
)
from communications.unipile.core.client import UnipileClient
from communications.unipile.clients.calendar import UnipileCalendarClient
from django.conf import settings
from django.contrib.auth import get_user_model
from pipelines.models import Pipeline, Record
from .models import (
    SchedulingProfile, MeetingType, SchedulingLink,
    ScheduledMeeting
)

User = get_user_model()

logger = logging.getLogger(__name__)


class AvailabilityCalculator:
    """
    Service for calculating available time slots
    Combines user preferences, working hours, and calendar events
    """
    
    def __init__(self, scheduling_profile: SchedulingProfile, meeting_type: Optional[MeetingType] = None):
        self.profile = scheduling_profile
        self.user = scheduling_profile.user
        self.meeting_type = meeting_type
        # Use meeting type's calendar if available, otherwise profile's
        if meeting_type and meeting_type.calendar_connection:
            self.calendar_connection = meeting_type.calendar_connection
            self.calendar_id = meeting_type.calendar_id
        else:
            self.calendar_connection = scheduling_profile.calendar_connection
            self.calendar_id = None
    
    async def get_available_slots(
        self,
        start_date: datetime,
        end_date: datetime,
        duration_minutes: int,
        scheduling_link: Optional[SchedulingLink] = None
    ) -> List[Dict[str, Any]]:
        """
        Get available time slots for a date range
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            duration_minutes: Duration of meeting in minutes
            scheduling_link: Optional scheduling link with custom settings
            
        Returns:
            List of available time slots
        """
        try:
            # Apply maximum advance booking
            max_end = timezone.now() + timedelta(days=self.profile.max_advance_days)
            if end_date > max_end:
                end_date = max_end
            
            # Get working hours (use override if provided by scheduling link)
            working_hours = self._get_working_hours(scheduling_link)
            
            # Get blocked dates and overrides
            blocked_dates = self._get_blocked_dates(start_date, end_date)
            
            # Get available slots
            if self.profile.calendar_sync_enabled:
                if not self.calendar_connection:
                    raise Exception("Calendar sync is enabled but no calendar connection is configured")
                    
                # Must check calendar - no fallback
                slots = await self._get_calendar_availability(
                    start_date, end_date, duration_minutes, working_hours, blocked_dates
                )
            else:
                # Use working hours without calendar events when sync is disabled
                slots = self._calculate_available_slots(
                    start_date, end_date, duration_minutes, 
                    working_hours, blocked_dates, []  # Empty busy_times list
                )
            
            return slots
            
        except Exception as e:
            logger.error(f"Failed to get available slots: {e}")
            raise
    
    def _get_working_hours(self, scheduling_link: Optional[SchedulingLink] = None) -> Dict[str, List[Dict]]:
        """Get working hours, considering link overrides"""
        if scheduling_link and scheduling_link.override_availability:
            return scheduling_link.override_availability.get('working_hours', self.profile.working_hours)
        return self.profile.working_hours or self.profile.get_default_working_hours()
    
    def _get_blocked_dates(self, start_date: datetime, end_date: datetime) -> List[datetime]:
        """Get list of blocked dates in the range"""
        blocked = []
        
        # Add profile blocked dates
        for date_str in self.profile.blocked_dates:
            try:
                date = datetime.fromisoformat(date_str).date()
                if start_date.date() <= date <= end_date.date():
                    blocked.append(date)
            except (ValueError, TypeError):
                continue
        
        # TODO: Add dates from availability overrides
        # overrides = AvailabilityOverride.objects.filter(
        #     profile=self.profile,
        #     date__gte=start_date.date(),
        #     date__lte=end_date.date(),
        #     override_type='blocked'
        # )
        # for override in overrides:
        #     blocked.append(override.date)
        
        return blocked
    
    async def _get_calendar_availability(
        self,
        start_date: datetime,
        end_date: datetime,
        duration_minutes: int,
        working_hours: Dict[str, List[Dict]],
        blocked_dates: List[datetime]
    ) -> List[Dict[str, Any]]:
        """Get availability from UniPile calendar"""
        try:
            # Get UniPile account ID from the user's calendar connection
            if not self.calendar_connection or not self.calendar_connection.unipile_account_id:
                raise Exception("No calendar connection configured - cannot determine availability")
            
            account_id = self.calendar_connection.unipile_account_id
            
            # Get UniPile client
            from django.db import connection
            tenant = connection.tenant
            
            if hasattr(tenant, 'unipile_config') and tenant.unipile_config.is_configured():
                client = UnipileClient(tenant.unipile_config.dsn, tenant.unipile_config.get_access_token())
            else:
                # Fall back to global config
                if not hasattr(settings, 'UNIPILE_DSN') or not hasattr(settings, 'UNIPILE_API_KEY'):
                    raise Exception("UniPile not configured - cannot determine availability")
                client = UnipileClient(settings.UNIPILE_DSN, settings.UNIPILE_API_KEY)
            
            calendar_client = UnipileCalendarClient(client)
            
            # Use specific calendar ID if provided by meeting type
            if self.calendar_id:
                calendar_id = self.calendar_id
            else:
                # First get the user's calendars
                calendars_response = await calendar_client.get_calendars(account_id)
                calendar_id = None
                
                if calendars_response and 'data' in calendars_response:
                    # Find primary calendar or first available
                    for cal in calendars_response['data']:
                        if cal.get('is_primary'):
                            calendar_id = cal['id']
                            break
                    if not calendar_id and calendars_response['data']:
                        calendar_id = calendars_response['data'][0]['id']
                
                if not calendar_id:
                    raise Exception("No calendar found for user - cannot determine availability")
            
            # Get busy times from calendar
            # IMPORTANT: We need to fetch events for the ENTIRE day range, not just from current time
            # This ensures we properly block all calendar events, even if some slots are in the past
            # We'll filter out past slots later when checking minimum notice
            calendar_start = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            calendar_end = end_date.replace(hour=23, minute=59, second=59, microsecond=0)
            
            # Convert to UTC for UniPile API
            # UniPile expects UTC dates with Z suffix
            calendar_start_utc = calendar_start.astimezone(pytz.UTC)
            calendar_end_utc = calendar_end.astimezone(pytz.UTC)
            
            # Format dates cleanly for UniPile API - no microseconds
            # UniPile expects format like: 2025-09-10T00:00:00Z
            start_date_str = calendar_start_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
            end_date_str = calendar_end_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            logger.info(f"Fetching calendar events for account {account_id}, calendar {calendar_id}")
            logger.info(f"Date range: {start_date_str} to {end_date_str}")
            logger.info(f"Original start_date: {start_date}, end_date: {end_date}")
            logger.info(f"Profile timezone: {self.profile.timezone}")
            
            events_response = await calendar_client.get_events(
                account_id=account_id,
                calendar_id=calendar_id,
                start_date=start_date_str,
                end_date=end_date_str,
                expand_recurring=True  # Use UniPile's native recurring event expansion
            )
            
            # Log the raw response for debugging
            logger.info(f"UniPile events response status: {events_response.get('status') if isinstance(events_response, dict) else 'unknown'}")
            if events_response and 'data' in events_response:
                logger.info(f"Total events returned (with recurring expanded): {len(events_response.get('data', []))}")
                # Log events for debugging
                for i, event in enumerate(events_response.get('data', [])):
                    logger.info(f"Event {i+1}: {event.get('title', 'Untitled')} - Start: {event.get('start', {})}")
            else:
                logger.warning(f"Unexpected response format from UniPile: {events_response}")
            
            # Extract busy times from events (UniPile has already expanded recurring events)
            busy_times = []
            if events_response and 'data' in events_response:
                logger.info(f"Processing {len(events_response.get('data', []))} calendar events")
                
                for event in events_response.get('data', []):
                    # Skip cancelled events
                    if event.get('is_cancelled'):
                        logger.info(f"Skipping cancelled event: {event.get('title', 'Untitled')}")
                        continue
                    
                    # Skip all-day events
                    if event.get('is_all_day'):
                        logger.info(f"Skipping all-day event: {event.get('title', 'Untitled')}")
                        continue
                    
                    # Extract start and end times
                    start_obj = event.get('start', {})
                    end_obj = event.get('end', {})
                    
                    # Handle both date_time and date formats
                    start_str = start_obj.get('date_time') or start_obj.get('date')
                    end_str = end_obj.get('date_time') or end_obj.get('date')
                    
                    if start_str and end_str:
                        try:
                            event_start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                            event_end = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                            
                            logger.info(f"Event '{event.get('title', 'Untitled')}': {event_start} to {event_end}")
                            busy_times.append({
                                'start': event_start,
                                'end': event_end
                            })
                        except Exception as e:
                            logger.warning(f"Failed to parse event times for '{event.get('title', 'Untitled')}': {e}")
                            logger.warning(f"  Start string: {start_str}, End string: {end_str}")
                    else:
                        logger.warning(f"Event '{event.get('title', 'Untitled')}' missing time data")
                        logger.warning(f"  Start: {start_obj}, End: {end_obj}")
            
            # Calculate available slots based on working hours and busy times
            slots = self._calculate_available_slots(
                start_date, end_date, duration_minutes, 
                working_hours, blocked_dates, busy_times
            )
            
            return slots
            
        except Exception as e:
            logger.error(f"Failed to get calendar availability: {e}")
            # Don't fall back - fail if we can't check calendar
            raise Exception(f"Unable to check calendar availability: {e}")
    
    def _calculate_available_slots(
        self,
        start_date: datetime,
        end_date: datetime,
        duration_minutes: int,
        working_hours: Dict[str, List[Dict]],
        blocked_dates: List[datetime],
        busy_times: List[Dict[str, datetime]]
    ) -> List[Dict[str, str]]:
        """
        Simple slot calculation:
        1. Generate all possible slots from working hours
        2. Remove any that overlap with calendar events
        3. Remove any that don't meet minimum notice (today only)
        """
        slots = []
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        # Get timezone info
        profile_tz = pytz.timezone(self.profile.timezone)
        now_in_tz = timezone.now().astimezone(profile_tz)
        today_in_tz = now_in_tz.date()
        
        # Use configurable slot interval from profile
        slot_interval = self.profile.slot_interval_minutes
        
        while current_date <= end_date_only:
            # Skip blocked dates
            if current_date in blocked_dates:
                current_date += timedelta(days=1)
                continue
            
            # Get working hours for this day
            day_name = current_date.strftime('%A').lower()
            day_hours = working_hours.get(day_name, [])
            
            for hours in day_hours:
                # Skip if disabled
                if hours.get('enabled') is False:
                    continue
                
                # Parse working hours
                start_time = datetime.strptime(hours['start'], '%H:%M').time()
                end_time = datetime.strptime(hours['end'], '%H:%M').time()
                
                # Create timezone-aware datetime objects
                work_start = profile_tz.localize(datetime.combine(current_date, start_time))
                work_end = profile_tz.localize(datetime.combine(current_date, end_time))
                
                # Generate all possible slots for this working period
                # Important: We generate slots based on start times that fall within working hours
                # This allows a 2pm slot if working hours end at 2pm (meeting can extend past work hours)
                slot_start = work_start
                while slot_start <= work_end:
                    slot_end = slot_start + timedelta(minutes=duration_minutes)
                    
                    # Check if slot is available
                    is_available = True
                    
                    # 1. Check calendar conflicts (buffer time disabled for now)
                    for busy in busy_times:
                        busy_start = busy['start']
                        busy_end = busy['end']
                        
                        # Buffer time temporarily disabled for debugging
                        # if self.profile.buffer_minutes > 0:
                        #     busy_start = busy_start - timedelta(minutes=self.profile.buffer_minutes)
                        #     busy_end = busy_end + timedelta(minutes=self.profile.buffer_minutes)
                        
                        # Convert busy times to profile timezone for accurate comparison
                        if busy_start.tzinfo:
                            busy_start = busy_start.astimezone(profile_tz)
                        if busy_end.tzinfo:
                            busy_end = busy_end.astimezone(profile_tz)
                        
                        # Debug logging for 11:30 AM slot
                        if slot_start.hour == 11 and slot_start.minute == 30:
                            logger.info(f"[DEBUG 11:30 SLOT] Checking overlap:")
                            logger.info(f"  Slot: {slot_start} to {slot_end}")
                            logger.info(f"  Busy: {busy_start} to {busy_end}")
                            logger.info(f"  Slot timezone: {slot_start.tzinfo}")
                            logger.info(f"  Busy timezone: {busy_start.tzinfo}")
                        
                        # Check for overlap - allow back-to-back scheduling
                        # Slots can end exactly when a meeting starts or start exactly when a meeting ends
                        # Only mark as unavailable if there's actual overlap (not just touching boundaries)
                        if slot_end <= busy_start or slot_start >= busy_end:
                            # No overlap - slot is before or after the busy period
                            if slot_start.hour == 11 and slot_start.minute == 30:
                                logger.info(f"  [11:30] No overlap detected - slot is available")
                            continue
                        else:
                            # There is overlap
                            if slot_start.hour == 11 and slot_start.minute == 30:
                                logger.info(f"  [11:30] OVERLAP DETECTED - marking unavailable")
                            is_available = False
                            break
                    
                    # 2. Check minimum notice (disabled for now)
                    # if is_available and current_date == today_in_tz:
                    #     min_start_time = now_in_tz + timedelta(hours=self.profile.min_notice_hours)
                    #     if slot_start < min_start_time:
                    #         is_available = False
                    
                    # Add slot if available
                    if is_available:
                        slots.append({
                            'start': slot_start.isoformat(),
                            'end': slot_end.isoformat()
                        })
                    
                    # Move to next slot
                    slot_start = slot_start + timedelta(minutes=slot_interval)
            
            current_date += timedelta(days=1)
        
        # Sort slots by start time
        slots.sort(key=lambda x: x['start'])
        
        # Log the number of slots for debugging
        logger.info(f"Generated {len(slots)} slots for {current_date - timedelta(days=(current_date - start_date.date()).days)} to {current_date - timedelta(days=1)}")
        
        # Remove duplicates using a set of slot keys
        unique_slots = []
        seen_slots = set()
        for slot in slots:
            slot_key = (slot['start'], slot['end'])
            if slot_key not in seen_slots:
                seen_slots.add(slot_key)
                unique_slots.append(slot)
        
        logger.info(f"After deduplication: {len(unique_slots)} unique slots")
        
        return unique_slots
    


class BookingProcessor:
    """
    Service for processing meeting bookings
    Handles participant creation, record management, and calendar events
    """
    
    def __init__(self, scheduling_link: Optional[SchedulingLink] = None, meeting_type: Optional[MeetingType] = None):
        """
        Initialize with either a SchedulingLink or MeetingType directly
        """
        if scheduling_link:
            self.link = scheduling_link
            self.meeting_type = scheduling_link.meeting_type
        elif meeting_type:
            self.link = None
            self.meeting_type = meeting_type
        else:
            # Allow initialization without meeting_type for manual events
            self.link = None
            self.meeting_type = None
        
        self.user = self.meeting_type.user if self.meeting_type else None
    
    @transaction.atomic
    async def process_booking(
        self,
        booking_data: Dict[str, Any],
        selected_slot: Dict[str, Any]
    ) -> ScheduledMeeting:
        """
        Process a booking request
        
        Args:
            booking_data: Form data from booking request
            selected_slot: Selected time slot
            
        Returns:
            Created ScheduledMeeting instance
        """
        try:
            # Extract participant info
            email = booking_data.get('email')
            name = booking_data.get('name', '')
            phone = booking_data.get('phone', '')
            
            # Find or create participant
            participant = await self._find_or_create_participant(email, name, phone)
            
            # Find or create conversation
            conversation = await self._find_or_create_conversation(participant)
            
            # Create or update pipeline record if configured
            record = None
            if self.link and self.link.auto_create_record and self.link.pipeline:
                record = await self._create_or_update_record(participant, booking_data)
            elif self.meeting_type.pipeline:
                # If no link but meeting type has pipeline, create record
                record = await self._create_or_update_record(participant, booking_data)
            
            # Create scheduled meeting
            meeting = await sync_to_async(ScheduledMeeting.objects.create)(
                meeting_type=self.meeting_type,
                scheduling_link=self.link if self.link else None,
                conversation=conversation,
                participant=participant,
                host=self.user,
                record=record,
                start_time=datetime.fromisoformat(selected_slot['start']),
                end_time=datetime.fromisoformat(selected_slot['end']),
                timezone=booking_data.get('timezone', 'UTC'),
                booking_data=booking_data,
                booking_ip=booking_data.get('ip_address'),
                booking_user_agent=booking_data.get('user_agent', ''),
                status='scheduled'
            )
            
            # Create calendar event
            await self._create_calendar_event(meeting)
            
            # Send confirmation email
            await self._send_confirmation_email(meeting)
            
            # Create message in conversation
            await self._create_booking_message(meeting, conversation)
            
            # Update link analytics (only if booking through a link)
            if self.link:
                await sync_to_async(self.link.increment_booking)()
            
            # Update meeting type analytics
            await sync_to_async(lambda: setattr(self.meeting_type, 'total_bookings', self.meeting_type.total_bookings + 1))()
            await sync_to_async(self.meeting_type.save)(update_fields=['total_bookings'])
            
            return meeting
            
        except Exception as e:
            logger.error(f"Failed to process booking: {e}")
            raise
    
    def _find_or_create_participant_sync(self, email: str, name: str, phone: str) -> Participant:
        """Find existing participant or create new one (sync version)"""
        # Try to find by email first
        participant = Participant.objects.filter(email=email).first()
        
        if not participant and phone:
            # Try to find by phone
            participant = Participant.objects.filter(phone=phone).first()
        
        if not participant:
            # Create new participant
            participant = Participant.objects.create(
                email=email,
                name=name,
                phone=phone
            )
        else:
            # Update participant info if needed
            updated = False
            if name and not participant.name:
                participant.name = name
                updated = True
            if phone and not participant.phone:
                participant.phone = phone
                updated = True
            if updated:
                participant.save()
        
        return participant
    
    def _find_or_create_conversation_sync(self, participant: Participant) -> Conversation:
        """Find or create conversation for scheduling (sync version)"""
        import uuid
        
        # Check if link already has a conversation
        if self.link and self.link.conversation:
            return self.link.conversation
        
        # Create a scheduling channel if needed
        channel = self._get_or_create_scheduling_channel_sync()
        
        # Prepare metadata and subject
        metadata = {'meeting_type': self.meeting_type.name}
        if self.link:
            subject = f"Scheduling - {self.link.name}"
            metadata['scheduling_link_id'] = str(self.link.id)
        else:
            subject = f"Scheduling - {self.meeting_type.name}"
            metadata['meeting_type_id'] = str(self.meeting_type.id)
        
        # Generate a unique external_thread_id for this scheduling conversation
        external_thread_id = f"scheduling_{uuid.uuid4()}"
        
        # Create new conversation with unique external_thread_id
        conversation = Conversation.objects.create(
            channel=channel,
            external_thread_id=external_thread_id,
            subject=subject,
            conversation_type='direct',
            status='active',
            metadata=metadata
        )
        
        # Add participant to conversation
        from communications.models import ConversationParticipant
        ConversationParticipant.objects.create(
            conversation=conversation,
            participant=participant,
            role='primary'
        )
        
        # Update link with conversation if we have one
        if self.link:
            self.link.conversation = conversation
            self.link.save(update_fields=['conversation'])
        
        return conversation
    
    def _get_or_create_scheduling_channel_sync(self) -> Channel:
        """Get or create a calendar channel for the user (sync version)"""
        channel = Channel.objects.filter(
            channel_type=ChannelType.CALENDAR,
            created_by=self.user
        ).first()
        
        if not channel:
            channel = Channel.objects.create(
                name=f"{self.user.username} - Calendar",
                channel_type=ChannelType.CALENDAR,
                unipile_account_id=f"calendar_{self.user.id}",
                auth_status='authenticated',
                created_by=self.user
            )
        
        return channel
    
    def _create_or_update_record_sync(
        self,
        participant: Participant,
        booking_data: Dict[str, Any]
    ) -> Optional['Record']:
        """Create or update pipeline record from booking (sync version)"""
        try:
            # Check if participant already has a linked record
            if participant.contact_record:
                record = participant.contact_record
                
                # Update record with booking data if field mapping exists
                if self.link.field_mapping:
                    updates = {}
                    for booking_field, pipeline_field in self.link.field_mapping.items():
                        if booking_field in booking_data:
                            updates[pipeline_field] = booking_data[booking_field]
                    
                    if updates:
                        record.data.update(updates)
                        record.save(update_fields=['data'])
                
                return record
            
            # Create new record with booking data directly (from dynamic form)
            record_data = booking_data.copy()
            
            # Apply field mapping if configured
            field_mapping = self.link.field_mapping if self.link else {}
            if field_mapping:
                for booking_field, pipeline_field in field_mapping.items():
                    if booking_field in booking_data:
                        record_data[pipeline_field] = booking_data[booking_field]
            
            # Determine which pipeline to use
            pipeline = self.link.pipeline if self.link and self.link.pipeline else self.meeting_type.pipeline
            
            # Set pipeline stage if configured
            if pipeline and pipeline.pipeline_type == 'deals' and self.meeting_type.pipeline_stage:
                record_data['stage'] = self.meeting_type.pipeline_stage
            
            # Create the record with both created_by and updated_by
            from pipelines.models import Record
            record = Record.objects.create(
                pipeline=pipeline,
                data=record_data,
                created_by=self.user,
                updated_by=self.user  # Add updated_by to satisfy constraint
            )
            
            # Link to participant
            participant.contact_record = record
            participant.save(update_fields=['contact_record'])
            
            return record
            
        except Exception as e:
            logger.error(f"Failed to create/update record: {e}")
            return None
    
    def _create_calendar_event_sync(self, meeting: ScheduledMeeting) -> None:
        """Create calendar event for the meeting (sync version)"""
        try:
            # Get user's scheduling profile
            profile = SchedulingProfile.objects.filter(user=self.user).select_related('calendar_connection').first()
            
            if not profile or not profile.calendar_connection:
                logger.warning("No calendar connection configured for user")
                return
            
            # Get UniPile client
            account_id = profile.calendar_connection.unipile_account_id
            
            from django.db import connection
            tenant = connection.tenant
            
            if hasattr(tenant, 'unipile_config') and tenant.unipile_config.is_configured():
                client = UnipileClient(tenant.unipile_config.dsn, tenant.unipile_config.get_access_token())
            else:
                # Fall back to global config
                if not hasattr(settings, 'UNIPILE_DSN') or not hasattr(settings, 'UNIPILE_API_KEY'):
                    logger.warning("UniPile not configured for calendar event creation")
                    return
                client = UnipileClient(settings.UNIPILE_DSN, settings.UNIPILE_API_KEY)
            
            # Note: UniPile calendar operations are async-only
            # We'll skip calendar event creation in sync mode for now
            logger.info(f"Calendar event creation skipped in sync mode for meeting {meeting.id}")
            
        except Exception as e:
            logger.error(f"Failed to create calendar event: {e}")
    
    def _create_booking_message_sync(self, meeting: ScheduledMeeting, conversation: Conversation) -> None:
        """Create a message in the conversation about the booking (sync version)"""
        try:
            message_content = f"""New meeting scheduled:
- Meeting Type: {meeting.meeting_type.name}
- Date: {meeting.start_time.strftime('%B %d, %Y')}
- Time: {meeting.start_time.strftime('%I:%M %p')} - {meeting.end_time.strftime('%I:%M %p')} ({meeting.timezone})
- Participant: {meeting.participant.name} ({meeting.participant.email})
- Notes: {meeting.booking_data.get('notes', 'No notes provided')}"""

            Message.objects.create(
                conversation=conversation,
                channel=conversation.channel,
                content=message_content,
                direction='outbound',
                status='sent',
                metadata={
                    'type': 'booking_confirmation',
                    'meeting_id': str(meeting.id)
                }
            )
        except Exception as e:
            logger.error(f"Failed to create booking message: {e}")
    
    def process_booking_sync(
        self,
        booking_data: Dict[str, Any],
        selected_slot: Dict[str, str]
    ) -> ScheduledMeeting:
        """
        Process a booking request (synchronous version)
        
        Args:
            booking_data: Booking form data
            selected_slot: Selected time slot
            
        Returns:
            Created ScheduledMeeting instance
        """
        try:
            # Extract participant info
            email = booking_data.get('email')
            name = booking_data.get('name', '')
            phone = booking_data.get('phone', '')
            
            # Find or create participant
            participant = self._find_or_create_participant_sync(email, name, phone)
            
            # Find or create conversation
            conversation = self._find_or_create_conversation_sync(participant)
            
            # Create or update pipeline record if configured
            record = None
            if self.link and self.link.auto_create_record and self.link.pipeline:
                record = self._create_or_update_record_sync(participant, booking_data)
            elif self.meeting_type.pipeline:
                # If no link but meeting type has pipeline, create record
                record = self._create_or_update_record_sync(participant, booking_data)
            
            # Create scheduled meeting
            meeting = ScheduledMeeting.objects.create(
                meeting_type=self.meeting_type,
                scheduling_link=self.link if self.link else None,
                conversation=conversation,
                participant=participant,
                host=self.user,
                record=record,
                start_time=datetime.fromisoformat(selected_slot['start']),
                end_time=datetime.fromisoformat(selected_slot['end']),
                timezone=booking_data.get('timezone', 'UTC'),
                booking_data=booking_data,
                booking_ip=booking_data.get('ip_address'),
                booking_user_agent=booking_data.get('user_agent', ''),
                status='scheduled'
            )
            
            # Update link analytics (only if booking through a link)
            if self.link:
                self.link.increment_booking()
            
            # Update meeting type analytics
            self.meeting_type.total_bookings += 1
            self.meeting_type.save(update_fields=['total_bookings'])
            
            # Create message in conversation
            self._create_booking_message_sync(meeting, conversation)
            
            # Send calendar invite asynchronously via Celery
            from .tasks import send_calendar_invite, send_booking_confirmation_email
            from django.db import connection
            
            # Get tenant schema for queue routing
            tenant_schema = connection.schema_name
            # Route scheduling tasks to communications queue (not general)
            queue_name = f'{tenant_schema}_communications' if tenant_schema != 'public' else 'celery'
            
            logger.info(f"📅 Attempting to queue calendar invite for meeting {meeting.id}")
            logger.info(f"Current tenant schema: {tenant_schema}, Queue: {queue_name}")
            logger.info(f"Meeting host: {meeting.host.email if meeting.host else 'None'}")
            
            # Queue tasks to tenant-specific queue with tenant schema in headers
            result = send_calendar_invite.apply_async(
                args=[str(meeting.id)], 
                queue=queue_name,
                headers={'tenant_schema': tenant_schema}
            )
            logger.info(f"✅ Queued calendar invite task - Task ID: {result.id}")
            
            # Send confirmation email asynchronously
            email_result = send_booking_confirmation_email.apply_async(
                args=[str(meeting.id)], 
                queue=queue_name,
                headers={'tenant_schema': tenant_schema}
            )
            logger.info(f"✅ Queued booking confirmation email - Task ID: {email_result.id}")
            
            return meeting
            
        except Exception as e:
            logger.error(f"Failed to process booking: {e}")
            raise
    
    async def _find_or_create_participant(self, email: str, name: str, phone: str) -> Participant:
        """Find existing participant or create new one"""
        # Try to find by email first
        participant = await sync_to_async(
            Participant.objects.filter(email=email).first
        )()
        
        if not participant and phone:
            # Try to find by phone
            participant = await sync_to_async(
                Participant.objects.filter(phone=phone).first
            )()
        
        if not participant:
            # Create new participant
            participant = await sync_to_async(Participant.objects.create)(
                email=email,
                name=name,
                phone=phone
            )
        else:
            # Update participant info if needed
            updated = False
            if name and not participant.name:
                participant.name = name
                updated = True
            if phone and not participant.phone:
                participant.phone = phone
                updated = True
            if updated:
                await sync_to_async(participant.save)()
        
        return participant
    
    async def _find_or_create_conversation(self, participant: Participant) -> Conversation:
        """Find or create conversation for scheduling"""
        # Check if link already has a conversation
        if self.link and self.link.conversation:
            return self.link.conversation
        
        # Create a scheduling channel if needed
        channel = await self._get_or_create_scheduling_channel()
        
        # Prepare metadata and subject
        metadata = {'meeting_type': self.meeting_type.name}
        if self.link:
            subject = f"Scheduling - {self.link.name}"
            metadata['scheduling_link_id'] = str(self.link.id)
        else:
            subject = f"Scheduling - {self.meeting_type.name}"
            metadata['meeting_type_id'] = str(self.meeting_type.id)
        
        # Try to find existing conversation for this channel without external_thread_id
        conversation = await sync_to_async(
            Conversation.objects.filter(
                channel=channel,
                external_thread_id__isnull=True,
                subject=subject
            ).first
        )()
        
        if not conversation:
            # Create new conversation if it doesn't exist with unique external_thread_id
            import uuid
            conversation = await sync_to_async(Conversation.objects.create)(
                channel=channel,
                external_thread_id=f"booking_{uuid.uuid4().hex[:12]}",
                subject=subject,
                conversation_type='direct',
                status='active',
                metadata=metadata
            )
            
            # Add participant to conversation
            from communications.models import ConversationParticipant
            await sync_to_async(ConversationParticipant.objects.create)(
                conversation=conversation,
                participant=participant,
                role='primary'
            )
        
        # Update link with conversation if we have one
        if self.link:
            self.link.conversation = conversation
            await sync_to_async(self.link.save)(update_fields=['conversation'])
        
        return conversation
    
    async def _get_or_create_scheduling_channel(self) -> Channel:
        """Get or create a calendar channel for the user"""
        channel = await sync_to_async(
            Channel.objects.filter(
                channel_type=ChannelType.CALENDAR,
                created_by=self.user
            ).first
        )()
        
        if not channel:
            channel = await sync_to_async(Channel.objects.create)(
                name=f"{self.user.username} - Calendar",
                channel_type=ChannelType.CALENDAR,
                unipile_account_id=f"calendar_{self.user.id}",
                auth_status='authenticated',
                created_by=self.user
            )
        
        return channel
    
    async def _create_or_update_record(
        self,
        participant: Participant,
        booking_data: Dict[str, Any]
    ) -> Optional[Record]:
        """Create or update pipeline record from booking"""
        try:
            # Check if participant already has a linked record
            if participant.contact_record:
                record = participant.contact_record
                
                # Update record with booking data if field mapping exists
                if self.link.field_mapping:
                    updates = {}
                    for booking_field, pipeline_field in self.link.field_mapping.items():
                        if booking_field in booking_data:
                            updates[pipeline_field] = booking_data[booking_field]
                    
                    if updates:
                        record.data.update(updates)
                        await sync_to_async(record.save)(update_fields=['data'])
                
                return record
            
            # Create new record
            record_data = {
                'email': participant.email,
                'name': participant.name,
                'phone': participant.phone
            }
            
            # Apply field mapping
            field_mapping = self.link.field_mapping if self.link else {}
            if field_mapping:
                for booking_field, pipeline_field in field_mapping.items():
                    if booking_field in booking_data:
                        record_data[pipeline_field] = booking_data[booking_field]
            
            # Determine which pipeline to use
            pipeline = self.link.pipeline if self.link and self.link.pipeline else self.meeting_type.pipeline
            
            # Set pipeline stage if configured
            if pipeline and pipeline.pipeline_type == 'deals' and self.meeting_type.pipeline_stage:
                record_data['stage'] = self.meeting_type.pipeline_stage
            
            # Create the record
            record = await sync_to_async(Record.objects.create)(
                pipeline=pipeline,
                data=record_data,
                created_by=self.user
            )
            
            # Link to participant
            participant.contact_record = record
            await sync_to_async(participant.save)(update_fields=['contact_record'])
            
            return record
            
        except Exception as e:
            logger.error(f"Failed to create/update record: {e}")
            return None
    
    async def _create_unipile_calendar_event(
        self,
        account_id: str,
        title: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        conference_provider: Optional[str] = None,
        calendar_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Unified method to create calendar events via UniPile.
        Used by both booking flow and manual event creation.
        
        Returns:
            Dict with 'event_id' and optionally 'meeting_url' if conference was created
        """
        try:
            logger.info(f"_create_unipile_calendar_event called for account: {account_id}")
            from django.db import connection
            from django.conf import settings
            
            # Initialize UniPile client
            tenant = connection.tenant
            if hasattr(tenant, 'unipile_config') and tenant.unipile_config and tenant.unipile_config.is_configured():
                logger.info("Using tenant UniPile configuration")
                client = UnipileClient(tenant.unipile_config.dsn, tenant.unipile_config.get_access_token())
            else:
                if not hasattr(settings, 'UNIPILE_DSN'):
                    logger.warning("UniPile not configured - no DSN in settings")
                    return None
                logger.info("Using global UniPile configuration from settings")
                client = UnipileClient(settings.UNIPILE_DSN, settings.UNIPILE_API_KEY)
            
            calendar_client = UnipileCalendarClient(client)
            
            # Get calendars and find primary
            calendars_response = await calendar_client.get_calendars(account_id)
            if not calendars_response:
                logger.error("Failed to get calendars")
                return None
            
            # Handle both response formats (data/items)
            calendars = calendars_response.get('data', calendars_response.get('items', []))
            if not calendars:
                logger.error("No calendars found")
                return None
            
            # Use provided calendar_id or find primary calendar
            target_calendar = calendar_id
            if not target_calendar:
                # Find primary calendar as fallback
                for calendar in calendars:
                    # Handle both field names (is_primary/primary)
                    if calendar.get('is_primary') or calendar.get('primary'):
                        target_calendar = calendar['id']
                        break
                
                # If no primary, use first calendar
                if not target_calendar:
                    target_calendar = calendars[0]['id']
            
            logger.info(f"Using calendar ID: {target_calendar}")
            
            # Create the event
            event_response = await calendar_client.create_event(
                account_id=account_id,
                calendar_id=target_calendar,
                title=title,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                description=description or '',
                location=location or '',
                attendees=attendees if attendees else None,
                conference_provider=conference_provider
            )
            
            if not event_response:
                logger.error("No response from calendar event creation")
                return None
            
            # Log the full response to debug meeting URL extraction
            logger.info(f"UniPile calendar event response: {event_response}")
            
            # Extract event ID and meeting URL
            result = {}
            
            # Handle different response formats
            event_data = event_response
            if 'data' in event_response:
                event_data = event_response['data']
            
            # Get event ID
            event_id = event_data.get('id') or event_data.get('event_id')
            if event_id:
                result['event_id'] = event_id
            
            # Get meeting URL if conference was created
            if 'conference' in event_data and 'url' in event_data['conference']:
                result['meeting_url'] = event_data['conference']['url']
            elif 'hangoutLink' in event_data:  # Google Meet specific
                result['meeting_url'] = event_data['hangoutLink']
            elif 'onlineMeetingUrl' in event_data:  # Microsoft Teams specific
                result['meeting_url'] = event_data['onlineMeetingUrl']
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return None
    
    async def _create_calendar_event(self, meeting: ScheduledMeeting) -> None:
        """Create calendar event for the meeting"""
        try:
            # Get user's scheduling profile
            profile = await sync_to_async(
                SchedulingProfile.objects.filter(user=self.user).select_related('calendar_connection').first
            )()
            
            if not profile or not profile.calendar_connection:
                logger.warning("No calendar connection configured for user")
                return
            
            account_id = profile.calendar_connection.unipile_account_id
            
            # Prepare meeting details
            title = f"{self.meeting_type.name} with {meeting.participant.name or meeting.participant.email}"
            description = self._generate_meeting_description(meeting)
            
            # Determine conference provider based on meeting type configuration
            conference_provider = None
            if self.meeting_type.location_type == 'google_meet':
                conference_provider = 'google_meet'
            elif self.meeting_type.location_type == 'teams':
                conference_provider = 'teams'
            elif self.meeting_type.location_type == 'zoom':
                conference_provider = 'zoom'
            
            # Use unified method to create event with meeting type's calendar
            result = await self._create_unipile_calendar_event(
                account_id=account_id,
                title=title,
                start_time=meeting.start_time,
                end_time=meeting.end_time,
                description=description,
                location=meeting.meeting_location or meeting.meeting_url,
                attendees=[meeting.participant.email] if meeting.participant.email else None,
                conference_provider=conference_provider,
                calendar_id=self.meeting_type.calendar_id  # Use meeting type's specified calendar
            )
            
            # Update meeting with results
            if result:
                if result.get('event_id'):
                    meeting.calendar_event_id = result['event_id']
                    meeting.calendar_sync_status = 'synced'
                
                if result.get('meeting_url'):
                    meeting.meeting_url = result['meeting_url']
                
                await sync_to_async(meeting.save)(
                    update_fields=['calendar_event_id', 'calendar_sync_status', 'meeting_url']
                )
            
        except Exception as e:
            logger.error(f"Failed to create calendar event: {e}")
            meeting.calendar_sync_status = 'failed'
            await sync_to_async(meeting.save)(update_fields=['calendar_sync_status'])
    
    def _generate_meeting_description(self, meeting: ScheduledMeeting) -> str:
        """Generate meeting description"""
        description = f"{self.meeting_type.description}\n\n"
        description += f"Attendee: {meeting.participant.name or 'Guest'}\n"
        description += f"Email: {meeting.participant.email}\n"
        
        if meeting.participant.phone:
            description += f"Phone: {meeting.participant.phone}\n"
        
        # Add booking data if there are custom questions
        if meeting.booking_data:
            custom_data = {k: v for k, v in meeting.booking_data.items() 
                          if k not in ['email', 'name', 'phone', 'timezone']}
            if custom_data:
                description += "\nAdditional Information:\n"
                for key, value in custom_data.items():
                    description += f"- {key}: {value}\n"
        
        return description
    
    async def _send_confirmation_email(self, meeting: ScheduledMeeting) -> None:
        """Send confirmation email to participant"""
        # TODO: Implement email sending via UniPile or other service
        logger.info(f"Would send confirmation email for meeting {meeting.id}")
    
    async def _create_booking_message(self, meeting: ScheduledMeeting, conversation: Conversation) -> None:
        """Create a message in the conversation for the booking"""
        try:
            content = f"Meeting scheduled: {self.meeting_type.name}\n"
            content += f"Date: {meeting.start_time.strftime('%B %d, %Y')}\n"
            content += f"Time: {meeting.start_time.strftime('%I:%M %p')} - {meeting.end_time.strftime('%I:%M %p')} {meeting.timezone}\n"
            
            if meeting.meeting_url:
                content += f"Meeting Link: {meeting.meeting_url}\n"
            elif meeting.meeting_location:
                content += f"Location: {meeting.meeting_location}\n"
            
            await sync_to_async(Message.objects.create)(
                conversation=conversation,
                channel=conversation.channel,
                sender_participant=meeting.participant,
                direction='inbound',
                content=content,
                subject=f"Booking Confirmation - {self.meeting_type.name}",
                sent_at=timezone.now(),
                received_at=timezone.now(),
                status='delivered',
                metadata={
                    'type': 'booking_confirmation',
                    'meeting_id': str(meeting.id)
                }
            )
        except Exception as e:
            logger.error(f"Failed to create booking message: {e}")


    async def create_manual_event(
        self,
        user: User,
        title: str,
        start_time: datetime,
        end_time: datetime,
        attendees: List[str] = None,
        location: Optional[str] = None,
        location_type: Optional[str] = 'other',
        description: Optional[str] = None,
        record: Optional['Record'] = None,
        add_to_calendar: bool = True
    ) -> Dict[str, Any]:
        """
        Create a manual calendar event without booking flow
        
        Args:
            user: User creating the event
            title: Event title
            start_time: Event start time
            end_time: Event end time
            attendees: List of attendee email addresses
            location: Event location/meeting link
            location_type: Type of location (google_meet, teams, zoom, in_person, etc.)
            description: Event description
            record: Optional associated record
            add_to_calendar: Whether to create in UniPile calendar
            
        Returns:
            Dict with conversation and event details
        """
        try:
            # Override the user from meeting_type with the manual event creator
            self.user = user
            
            # Get or create scheduling channel
            channel = await self._get_or_create_scheduling_channel()
            
            # Create conversation for the event
            import uuid
            conversation = await sync_to_async(Conversation.objects.create)(
                channel=channel,
                external_thread_id=f"event_{uuid.uuid4().hex[:12]}",
                subject=title,
                conversation_type='calendar_event',
                status='scheduled',
                metadata={
                    'event_type': 'manual',
                    'event_details': {
                        'title': title,
                        'start_time': start_time.isoformat(),
                        'end_time': end_time.isoformat(),
                        'location': location or '',
                        'location_type': location_type,
                        'description': description or '',
                    },
                    'created_by': user.id,
                    'is_manual_event': True
                }
            )
            
            # Add organizer as participant
            organizer = await self._find_or_create_participant(
                email=user.email,
                name=user.get_full_name() or user.username,
                phone=''
            )
            
            await sync_to_async(ConversationParticipant.objects.create)(
                conversation=conversation,
                participant=organizer,
                role='organizer'
            )
            
            # Add attendees as participants
            participant_list = [organizer]
            if attendees:
                for email in attendees:
                    if email and email != user.email:
                        participant = await self._find_or_create_participant(
                            email=email,
                            name=email.split('@')[0],
                            phone=''
                        )
                        participant_list.append(participant)
                        
                        await sync_to_async(ConversationParticipant.objects.create)(
                            conversation=conversation,
                            participant=participant,
                            role='attendee'
                        )
            
            # Add record participant if provided
            if record and hasattr(record, 'communication_identifiers'):
                record_email = record.communication_identifiers.get('email', [None])[0]
                if record_email and record_email not in (attendees or []) + [user.email]:
                    from pipelines.serializers import RecordSerializer
                    record_data = RecordSerializer(record).data
                    
                    participant = await self._find_or_create_participant(
                        email=record_email,
                        name=record_data.get('title', record_email.split('@')[0]),
                        phone=record.communication_identifiers.get('phone', [''])[0]
                    )
                    participant.contact_record = record
                    await sync_to_async(participant.save)(update_fields=['contact_record'])
                    participant_list.append(participant)
                    
                    await sync_to_async(ConversationParticipant.objects.create)(
                        conversation=conversation,
                        participant=participant,
                        role='contact'
                    )
            
            # Create calendar event in UniPile FIRST if requested
            calendar_event_id = None
            meeting_url = None
            if add_to_calendar:
                # Get user's scheduling profile
                profile = await sync_to_async(
                    SchedulingProfile.objects.filter(user=user).select_related('calendar_connection').first
                )()
                
                if profile and profile.calendar_connection:
                    # Determine conference provider based on location type
                    # Always set conference provider for virtual meeting types
                    conference_provider = None
                    if location_type == 'google_meet':
                        conference_provider = 'google_meet'
                    elif location_type == 'teams':
                        conference_provider = 'teams'
                    elif location_type == 'zoom':
                        conference_provider = 'zoom'
                    
                    # Use unified method to create event
                    result = await self._create_unipile_calendar_event(
                        account_id=profile.calendar_connection.unipile_account_id,
                        title=title,
                        start_time=start_time,
                        end_time=end_time,
                        description=description,
                        location=location,
                        attendees=attendees,
                        conference_provider=conference_provider
                    )
                    
                    if result:
                        calendar_event_id = result.get('event_id')
                        meeting_url = result.get('meeting_url')
                        
                        # Update location with actual meeting URL if we got one
                        if meeting_url and not location:
                            location = meeting_url
                        
                        if calendar_event_id:
                            conversation.metadata['calendar_event_id'] = calendar_event_id
                            conversation.metadata['unipile_event_id'] = calendar_event_id
                        if meeting_url:
                            conversation.metadata['meeting_url'] = meeting_url
                            
                        await sync_to_async(conversation.save)(update_fields=['metadata'])
                else:
                    logger.info(f"User {user.username} has no calendar connection for event sync")
            
            # Create event message with actual meeting link
            message_parts = [
                f"📅 **Event Created: {title}**",
                "",
                f"**Date & Time:**",
                f"📆 {start_time.strftime('%A, %B %d, %Y')}",
                f"🕐 {start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p %Z')}",
                ""
            ]
            
            # Add location/meeting link
            if meeting_url or location:
                location_icon = {
                    'google_meet': '🎥',
                    'teams': '🎥',
                    'zoom': '🎥',
                    'in_person': '📍',
                    'phone': '📞',
                    'other': '🔗'
                }.get(location_type, '🔗')
                
                # Use meeting URL if available, otherwise use location
                display_location = meeting_url if meeting_url else location
                
                message_parts.extend([
                    f"**Location:**",
                    f"{location_icon} {display_location}",
                    ""
                ])
            
            if description:
                message_parts.extend([
                    f"**Details:**",
                    description,
                    ""
                ])
            
            if participant_list:
                message_parts.append("**Participants:**")
                for p in participant_list:
                    role_suffix = " (Organizer)" if p.email == user.email else ""
                    message_parts.append(f"• {p.name or p.email}{role_suffix}")
                message_parts.append("")
            
            # Create the message with complete information
            await sync_to_async(Message.objects.create)(
                conversation=conversation,
                channel=channel,
                direction=MessageDirection.OUTBOUND,
                content="\n".join(message_parts),
                status=MessageStatus.SENT,
                sent_at=timezone.now(),
                metadata={
                    'message_type': 'event_created',
                    'sender_type': 'system',
                    'event_data': {
                        'title': title,
                        'start_time': start_time.isoformat(),
                        'end_time': end_time.isoformat(),
                        'location': location or '',
                        'meeting_url': meeting_url or '',
                        'location_type': location_type,
                        'description': description or '',
                        'attendees': attendees or [],
                        'organizer': {
                            'id': user.id,
                            'email': user.email,
                            'name': user.get_full_name() or user.username
                        }
                    },
                    'calendar_event_id': calendar_event_id
                }
            )
            
            return {
                'success': True,
                'conversation_id': str(conversation.id),
                'calendar_event_id': calendar_event_id,
                'message': f'Event "{title}" created successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to create manual event: {e}")
            raise
    


class FacilitatorBookingProcessor(BookingProcessor):
    """Service for handling facilitator meeting bookings"""
    
    def __init__(self, meeting_type):
        # Initialize parent BookingProcessor with meeting_type
        super().__init__(meeting_type=meeting_type)
        self.facilitator = meeting_type.user
    
    async def process_facilitator_step1(self, participant_data, meeting_params, selected_slots):
        """
        Process Participant 1's selections for a facilitator meeting
        
        Args:
            participant_data: P1's info (name, email, phone, etc.)
            meeting_params: Selected duration, location type, location details
            selected_slots: List of selected time slots
        
        Returns:
            FacilitatorBooking instance
        """
        from .models import FacilitatorBooking
        from datetime import timedelta
        
        try:
            # Validate selected slots against current availability
            for slot in selected_slots:
                # TODO: Validate each slot is still available
                pass
            
            # Get expiry time from settings or default to 72 hours
            facilitator_settings = self.meeting_type.facilitator_settings or {}
            expiry_hours = facilitator_settings.get('link_expiry_hours', 72)
            
            # Create FacilitatorBooking record
            booking = await sync_to_async(FacilitatorBooking.objects.create)(
                meeting_type=self.meeting_type,
                facilitator=self.facilitator,
                
                # Participant 1 info
                participant_1_email=participant_data['email'],
                participant_1_name=participant_data.get('name', ''),
                participant_1_phone=participant_data.get('phone', ''),
                participant_1_data=participant_data,
                participant_1_message=participant_data.get('message', ''),
                
                # Participant 2 email (required)
                participant_2_email=participant_data['participant_2_email'],
                participant_2_name=participant_data.get('participant_2_name', ''),
                
                # Meeting parameters
                selected_duration_minutes=meeting_params['duration'],
                selected_location_type=meeting_params['location_type'],
                selected_location_details=meeting_params.get('location_details', {}),
                
                # Slots and timing
                selected_slots=selected_slots,
                participant_1_completed_at=timezone.now(),
                expires_at=timezone.now() + timedelta(hours=expiry_hours),
                
                status='pending_p2'
            )
            
            # Send email to Participant 2
            from .tasks import send_facilitator_p2_invitation
            await sync_to_async(send_facilitator_p2_invitation.delay)(
                str(booking.id),
                self.facilitator.tenant.schema_name if hasattr(self.facilitator, 'tenant') else None
            )
            
            booking.invitation_sent_at = timezone.now()
            await sync_to_async(booking.save)(update_fields=['invitation_sent_at'])
            
            return booking
            
        except Exception as e:
            logger.error(f"Failed to process facilitator step 1: {e}")
            raise
    
    async def process_facilitator_step2(self, booking, participant_data, selected_slot):
        """
        Process Participant 2's final selection for a facilitator meeting
        
        Args:
            booking: FacilitatorBooking instance
            participant_data: P2's info (name, phone, etc.)
            selected_slot: The chosen time slot
        
        Returns:
            ScheduledMeeting instance
        """
        from .models import ScheduledMeeting
        from communications.models import Participant
        
        try:
            # Validate the booking is still valid
            if booking.is_expired():
                raise ValueError("This booking link has expired")
            
            if booking.status != 'pending_p2':
                raise ValueError("This booking has already been completed")
            
            # Validate selected slot is one of the options
            slot_found = False
            for slot in booking.selected_slots:
                if slot['start'] == selected_slot['start'] and slot['end'] == selected_slot['end']:
                    slot_found = True
                    break
            
            if not slot_found:
                raise ValueError("Invalid slot selection")
            
            # Parse slot times
            slot_start = datetime.fromisoformat(selected_slot['start'])
            slot_end = datetime.fromisoformat(selected_slot['end'])
            
            # Only check for conflicts if facilitator will be a participant in the meeting
            # If they're just coordinating (not attending), they can schedule multiple meetings at the same time
            include_facilitator = self.meeting_type.facilitator_settings.get('include_facilitator', True)
            
            if include_facilitator:
                conflicts = await sync_to_async(ScheduledMeeting.objects.filter(
                    meeting_type=self.meeting_type,
                    start_time__lt=slot_end,
                    end_time__gt=slot_start,
                    status__in=['scheduled', 'confirmed', 'reminder_sent', 'in_progress']
                ).exists)()
                
                if conflicts:
                    raise ValueError("Selected time slot is no longer available")
            
            # Update booking with P2 info
            booking.participant_2_name = participant_data.get('name', booking.participant_2_name)
            booking.participant_2_phone = participant_data.get('phone', '')
            booking.participant_2_data = participant_data
            booking.final_slot = selected_slot
            booking.participant_2_completed_at = timezone.now()
            booking.status = 'completed'
            
            # Create or get participants
            participant_1 = await sync_to_async(Participant.objects.get_or_create)(
                email=booking.participant_1_email,
                defaults={
                    'name': booking.participant_1_name,
                    'phone': booking.participant_1_phone
                }
            )
            participant_1 = participant_1[0] if isinstance(participant_1, tuple) else participant_1
            
            participant_2 = await sync_to_async(Participant.objects.get_or_create)(
                email=booking.participant_2_email,
                defaults={
                    'name': booking.participant_2_name,
                    'phone': booking.participant_2_phone
                }
            )
            participant_2 = participant_2[0] if isinstance(participant_2, tuple) else participant_2
            
            # Determine meeting location
            meeting_url = ''
            meeting_location = ''
            
            if booking.selected_location_type == 'in_person':
                meeting_location = booking.selected_location_details.get('address', '')
            elif booking.selected_location_type in ['google_meet', 'teams', 'zoom']:
                # Will be auto-generated during calendar event creation
                pass
            
            # Get or create scheduling channel for the facilitator
            from communications.models import Conversation, ConversationParticipant, Channel, ChannelType
            channel = await sync_to_async(
                Channel.objects.filter(
                    channel_type=ChannelType.CALENDAR,
                    created_by=self.facilitator
                ).first
            )()
            
            if not channel:
                channel = await sync_to_async(Channel.objects.create)(
                    name=f"{self.facilitator.username} - Calendar",
                    channel_type=ChannelType.CALENDAR,
                    unipile_account_id=f"calendar_{self.facilitator.id}",
                    auth_status='authenticated',
                    created_by=self.facilitator
                )
            
            # Create conversation for the meeting with unique external_thread_id
            import uuid
            conversation = await sync_to_async(Conversation.objects.create)(
                channel=channel,
                external_thread_id=f"facilitator_meeting_{booking.id}",
                subject=f"{self.meeting_type.name} - {booking.participant_1_name} & {booking.participant_2_name}",
                conversation_type='meeting',
                metadata={
                    'meeting_type_id': str(self.meeting_type.id),
                    'facilitator_booking_id': str(booking.id),
                    'participants': [
                        {'name': booking.participant_1_name, 'email': booking.participant_1_email},
                        {'name': booking.participant_2_name, 'email': booking.participant_2_email}
                    ]
                }
            )
            
            # Add participants to conversation
            await sync_to_async(ConversationParticipant.objects.create)(
                conversation=conversation,
                participant=participant_1,
                role='primary'
            )
            await sync_to_async(ConversationParticipant.objects.create)(
                conversation=conversation,
                participant=participant_2,
                role='secondary'
            )
            
            # Create the scheduled meeting
            meeting = await sync_to_async(ScheduledMeeting.objects.create)(
                meeting_type=self.meeting_type,
                host=self.facilitator,
                participant=participant_1,  # Primary participant
                conversation=conversation,
                start_time=slot_start,
                end_time=slot_end,
                timezone=participant_data.get('timezone', 'UTC'),
                meeting_url=meeting_url,
                meeting_location=meeting_location,
                booking_data={
                    'facilitator_booking_id': str(booking.id),
                    'participant_1': {
                        'name': booking.participant_1_name,
                        'email': booking.participant_1_email,
                        'phone': booking.participant_1_phone
                    },
                    'participant_2': {
                        'name': booking.participant_2_name,
                        'email': booking.participant_2_email,
                        'phone': booking.participant_2_phone
                    },
                    'selected_duration': booking.selected_duration_minutes,
                    'selected_location': booking.selected_location_type
                },
                status='scheduled'
            )
            
            # Link meeting to booking
            booking.scheduled_meeting = meeting
            await sync_to_async(booking.save)(update_fields=['status', 'participant_2_name', 'participant_2_phone', 
                                                             'participant_2_data', 'final_slot', 
                                                             'participant_2_completed_at', 'scheduled_meeting'])
            
            # Store attendees info in booking_data for the Celery task to use
            attendees = [
                booking.participant_1_email,
                booking.participant_2_email
            ]
            
            # Include facilitator if configured
            facilitator_settings = self.meeting_type.facilitator_settings or {}
            if facilitator_settings.get('include_facilitator', True):
                attendees.append(self.facilitator.email)
            
            meeting.booking_data['attendees'] = attendees
            meeting.booking_data['conference_provider'] = booking.selected_location_type
            meeting.booking_data['facilitator_booking_id'] = str(booking.id)
            await sync_to_async(meeting.save)(update_fields=['booking_data'])
            
            # Queue calendar invite creation via Celery (same as direct bookings)
            from .tasks import send_calendar_invite, send_facilitator_confirmations
            from django.db import connection
            
            # Get tenant schema for queue routing
            tenant_schema = await sync_to_async(lambda: connection.schema_name)()
            queue_name = f'{tenant_schema}_communications' if tenant_schema != 'public' else 'celery'
            
            logger.info(f"📅 Queueing calendar invite for facilitator meeting {meeting.id}")
            logger.info(f"Tenant schema: {tenant_schema}, Queue: {queue_name}")
            
            # Queue calendar creation task
            result = await sync_to_async(send_calendar_invite.apply_async)(
                args=[str(meeting.id)], 
                queue=queue_name,
                headers={'tenant_schema': tenant_schema}
            )
            logger.info(f"✅ Queued calendar invite task - Task ID: {result.id}")
            
            # Send confirmation emails to all parties
            await sync_to_async(send_facilitator_confirmations.delay)(
                str(meeting.id),
                self.facilitator.tenant.schema_name if hasattr(self.facilitator, 'tenant') else None
            )
            
            return meeting
            
        except Exception as e:
            logger.error(f"Failed to process facilitator step 2: {e}")
            raise
    
    # Synchronous wrapper methods for use in views
    def process_facilitator_step1_sync(self, participant_data, meeting_params, selected_slots):
        """Synchronous wrapper for process_facilitator_step1"""
        return async_to_sync(self.process_facilitator_step1)(participant_data, meeting_params, selected_slots)
    
    def process_facilitator_step2_sync(self, booking, participant_data, selected_slot):
        """Synchronous wrapper for process_facilitator_step2"""
        return async_to_sync(self.process_facilitator_step2)(booking, participant_data, selected_slot)


class MeetingReminderService:
    """Service for sending meeting reminders"""
    
    @staticmethod
    async def send_reminders():
        """Send reminders for upcoming meetings"""
        try:
            # Get meetings that need reminders
            now = timezone.now()
            
            # Get all meetings in the next 48 hours that haven't been reminded
            upcoming_meetings = await sync_to_async(list)(
                ScheduledMeeting.objects.filter(
                    start_time__gte=now,
                    start_time__lte=now + timedelta(hours=48),
                    status='scheduled'
                ).select_related('meeting_type', 'participant', 'host')
            )
            
            for meeting in upcoming_meetings:
                # Check if reminder should be sent
                hours_until = (meeting.start_time - now).total_seconds() / 3600
                reminder_hours = meeting.meeting_type.get_default_reminder_hours()
                
                for reminder_hour in reminder_hours:
                    # Check if we should send this reminder
                    if hours_until <= reminder_hour and hours_until > (reminder_hour - 0.5):
                        # Check if this reminder was already sent
                        reminder_key = f"{reminder_hour}h"
                        if reminder_key not in meeting.reminder_sent_at:
                            await MeetingReminderService._send_reminder(meeting, reminder_hour)
                            
                            # Mark reminder as sent
                            meeting.reminder_sent_at.append(reminder_key)
                            meeting.status = 'reminder_sent'
                            await sync_to_async(meeting.save)(
                                update_fields=['reminder_sent_at', 'status']
                            )
            
        except Exception as e:
            logger.error(f"Failed to send reminders: {e}")
    
    @staticmethod
    async def _send_reminder(meeting: ScheduledMeeting, hours_before: int):
        """Send a single reminder"""
        # TODO: Implement actual reminder sending
        logger.info(f"Would send {hours_before}h reminder for meeting {meeting.id}")


class MeetingStatusUpdater:
    """Service for updating meeting statuses"""
    
    @staticmethod
    async def update_statuses():
        """Update meeting statuses based on current time"""
        try:
            now = timezone.now()
            
            # Mark in-progress meetings
            await sync_to_async(
                ScheduledMeeting.objects.filter(
                    start_time__lte=now,
                    end_time__gte=now,
                    status__in=['scheduled', 'reminder_sent']
                ).update
            )(status='in_progress')
            
            # Mark completed meetings
            await sync_to_async(
                ScheduledMeeting.objects.filter(
                    end_time__lt=now,
                    status='in_progress'
                ).update
            )(status='completed')
            
            # TODO: Detect no-shows (would need integration with meeting platform)
            
        except Exception as e:
            logger.error(f"Failed to update meeting statuses: {e}")