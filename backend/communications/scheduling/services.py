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
from asgiref.sync import sync_to_async

from communications.models import Channel, Conversation, Participant, Message, ChannelType, UserChannelConnection
from communications.unipile.core.client import UnipileClient
from communications.unipile.clients.calendar import UnipileCalendarClient
from django.conf import settings
from pipelines.models import Pipeline, Record
from .models import (
    SchedulingProfile, MeetingType, SchedulingLink,
    ScheduledMeeting
)

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
            raise ValueError("Either scheduling_link or meeting_type must be provided")
        
        self.user = self.meeting_type.user
    
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
            # Create new conversation if it doesn't exist
            conversation = await sync_to_async(Conversation.objects.create)(
                channel=channel,
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
            
            calendar_client = UnipileCalendarClient(client)
            
            # Get calendars to find primary one
            calendars_response = await calendar_client.get_calendars(account_id)
            calendar_id = None
            
            if calendars_response and 'items' in calendars_response:
                # Find primary calendar or first available
                for cal in calendars_response['items']:
                    if cal.get('primary'):
                        calendar_id = cal['id']
                        break
                if not calendar_id and calendars_response['items']:
                    calendar_id = calendars_response['items'][0]['id']
            
            if not calendar_id:
                logger.warning("No suitable calendar found for scheduling")
                return
            
            # Prepare meeting details
            title = f"{self.meeting_type.name} with {meeting.participant.name or meeting.participant.email}"
            description = self._generate_meeting_description(meeting)
            
            # Create the event
            event = await calendar_client.create_event(
                account_id=account_id,
                calendar_id=calendar_id,
                title=title,
                start_time=meeting.start_time.isoformat(),
                end_time=meeting.end_time.isoformat(),
                description=description,
                location=meeting.meeting_location or meeting.meeting_url,
                attendees=[meeting.participant.email] if meeting.participant.email else None
            )
            
            # Update meeting with event ID
            if event and 'id' in event:
                meeting.calendar_event_id = event['id']
                meeting.calendar_sync_status = 'synced'
                
                # Extract meeting URL if provided
                if 'conference' in event and 'url' in event['conference']:
                    meeting.meeting_url = event['conference']['url']
                
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