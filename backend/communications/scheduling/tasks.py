"""
Celery tasks for scheduling functionality
"""
import logging
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from asgiref.sync import async_to_sync
from datetime import datetime, timezone

from .models import ScheduledMeeting, SchedulingProfile, FacilitatorBooking
from communications.unipile.core.client import UnipileClient
from communications.unipile.clients.calendar import UnipileCalendarClient

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_calendar_invite(self, meeting_id: str, tenant_schema: str = None):
    """
    Send calendar invite for a scheduled meeting
    
    Args:
        meeting_id: UUID of the ScheduledMeeting
        tenant_schema: Optional tenant schema (for direct calls)
    """
    logger.info(f"🚀 send_calendar_invite task started for meeting_id: {meeting_id}")
    logger.info(f"Task request info: {self.request}")
    logger.info(f"Passed tenant_schema: {tenant_schema}")
    
    try:
        # Get tenant schema from task headers
        from django_tenants.utils import schema_context
        
        # Use passed tenant_schema if available, otherwise try to get from request headers
        if not tenant_schema:
            # Try to get from request headers (proper way for Celery tasks)
            if hasattr(self.request, 'headers') and self.request.headers:
                tenant_schema = self.request.headers.get('tenant_schema')
                logger.info(f"Tenant schema from headers: {tenant_schema}")
            
            # Fallback: try to get from request attributes (legacy)
            if not tenant_schema:
                tenant_schema = getattr(self.request, 'tenant_schema', None)
                logger.info(f"Tenant schema from request attribute: {tenant_schema}")
        
        if not tenant_schema:
            # Last resort: try to extract from queue name (e.g., oneotalent_communications -> oneotalent)
            delivery_info = getattr(self.request, 'delivery_info', None)
            if delivery_info:
                queue_name = delivery_info.get('routing_key', '')
                logger.info(f"Trying to extract from queue name: {queue_name}")
                if '_' in queue_name:
                    tenant_schema = queue_name.split('_')[0]
                    logger.info(f"Extracted tenant schema: {tenant_schema}")
            else:
                logger.warning("No delivery_info available (running synchronously?)")
        
        if not tenant_schema or tenant_schema == 'public':
            logger.error(f"No tenant schema found for task {self.request.id}")
            raise ValueError("Tenant schema required for calendar invite task")
        
        logger.info(f"Using tenant schema: {tenant_schema}")
        # Execute in tenant context
        with schema_context(tenant_schema):
            # Get the meeting
            meeting = ScheduledMeeting.objects.select_related(
                'meeting_type', 
                'host', 
                'participant'
            ).get(id=meeting_id)
            
            # Get user's scheduling profile
            profile = SchedulingProfile.objects.filter(
                user=meeting.host
            ).select_related('calendar_connection').first()
            
            logger.info(f"Found profile: {profile is not None}")
            if profile:
                logger.info(f"Calendar connection exists: {profile.calendar_connection is not None}")
                if profile.calendar_connection:
                    logger.info(f"Unipile account ID: {profile.calendar_connection.unipile_account_id}")
            
            if not profile or not profile.calendar_connection:
                logger.warning(f"No calendar connection for user {meeting.host.id} ({meeting.host.email})")
                return
            
            # Get UniPile client
            account_id = profile.calendar_connection.unipile_account_id
            logger.info(f"Using Unipile account ID: {account_id}")
            
            from django.db import connection
            tenant = connection.tenant
            
            if hasattr(tenant, 'unipile_config') and tenant.unipile_config.is_configured():
                logger.info(f"Using tenant-specific Unipile config")
                client = UnipileClient(tenant.unipile_config.dsn, tenant.unipile_config.get_access_token())
            else:
                # Fall back to global config
                logger.info(f"Trying global Unipile config")
                if not hasattr(settings, 'UNIPILE_DSN') or not hasattr(settings, 'UNIPILE_API_KEY'):
                    logger.warning("UniPile not configured for calendar event creation")
                    logger.warning(f"Settings has UNIPILE_DSN: {hasattr(settings, 'UNIPILE_DSN')}")
                    logger.warning(f"Settings has UNIPILE_API_KEY: {hasattr(settings, 'UNIPILE_API_KEY')}")
                    return
                logger.info(f"Using global Unipile config from settings")
                client = UnipileClient(settings.UNIPILE_DSN, settings.UNIPILE_API_KEY)
            
            # Run the async calendar creation synchronously
            async_to_sync(create_calendar_event_async)(
                client, account_id, meeting
            )
            
            logger.info(f"Calendar invite sent for meeting {meeting_id}")
        
    except ScheduledMeeting.DoesNotExist:
        logger.error(f"Meeting {meeting_id} not found")
    except Exception as e:
        logger.error(f"Failed to send calendar invite for meeting {meeting_id}: {e}")
        # Retry the task
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))


async def create_calendar_event_async(client: UnipileClient, account_id: str, meeting: ScheduledMeeting):
    """
    Async function to create calendar event via UniPile
    
    Args:
        client: UniPile client
        account_id: UniPile account ID
        meeting: ScheduledMeeting instance
    """
    logger.info(f"🚀 Starting calendar event creation for meeting {meeting.id}")
    logger.info(f"Account ID: {account_id}")
    
    calendar_client = UnipileCalendarClient(client)
    
    # Get calendars to find primary one
    logger.info(f"Getting calendars for account {account_id}")
    calendars_response = await calendar_client.get_calendars(account_id)
    logger.info(f"Calendars response: {calendars_response}")
    
    if not calendars_response or 'data' not in calendars_response:
        logger.error(f"Failed to get calendars - Response: {calendars_response}")
        return
    
    # Determine which calendar to use
    target_calendar = None
    
    # Check if meeting type has a specific calendar configured
    if meeting.meeting_type and meeting.meeting_type.calendar_id:
        target_calendar = meeting.meeting_type.calendar_id
        logger.info(f"Using meeting type's configured calendar: {target_calendar}")
    else:
        # Find primary calendar as fallback
        for calendar in calendars_response['data']:
            if calendar.get('is_primary'):
                target_calendar = calendar['id']
                break
        
        if not target_calendar and calendars_response['data']:
            # Use first calendar if no primary
            target_calendar = calendars_response['data'][0]['id']
    
    if not target_calendar:
        logger.error("No calendar found")
        return
    
    logger.info(f"Using calendar: {target_calendar}")
    
    # Create the event
    try:
        logger.info(f"Creating calendar event for meeting {meeting.id}")
        
        # Check if this is a facilitator meeting
        is_facilitator_meeting = meeting.booking_data.get('facilitator_booking_id') is not None
        
        # Determine conference provider
        conference_provider = None
        if is_facilitator_meeting:
            # For facilitator meetings, check booking_data for conference provider
            provider = meeting.booking_data.get('conference_provider', '')
            if provider == 'google_meet':
                conference_provider = 'google_meet'
                logger.info("Adding Google Meet conference to facilitator meeting")
            elif provider == 'teams':
                conference_provider = 'teams'
                logger.info("Adding Microsoft Teams conference to facilitator meeting")
        else:
            # For direct bookings, use meeting type location type
            if meeting.meeting_type.location_type == 'google_meet':
                conference_provider = 'google_meet'
                logger.info("Adding Google Meet conference to calendar event")
            elif meeting.meeting_type.location_type == 'teams':
                conference_provider = 'teams'
                logger.info("Adding Microsoft Teams conference to calendar event")
        
        # Prepare attendees
        attendees = []
        if is_facilitator_meeting and 'attendees' in meeting.booking_data:
            # Use the attendees list from booking_data for facilitator meetings
            attendees = meeting.booking_data['attendees']
            logger.info(f"Facilitator meeting with attendees: {attendees}")
        elif meeting.participant and meeting.participant.email:
            # For direct bookings, just the participant
            attendees = [meeting.participant.email]
        
        # Prepare description and title
        if is_facilitator_meeting:
            # Get facilitator booking details if available
            from .models import FacilitatorBooking
            facilitator_booking = None
            try:
                booking_id = meeting.booking_data.get('facilitator_booking_id')
                if booking_id:
                    facilitator_booking = await FacilitatorBooking.objects.aget(id=booking_id)
            except:
                pass
            
            if facilitator_booking:
                title = f"{meeting.meeting_type.name} - {facilitator_booking.participant_1_name} & {facilitator_booking.participant_2_name}"
                description = f"""Facilitator Meeting

Participants:
- {facilitator_booking.participant_1_name} ({facilitator_booking.participant_1_email})
- {facilitator_booking.participant_2_name} ({facilitator_booking.participant_2_email})

Meeting Type: {meeting.meeting_type.name}
Duration: {facilitator_booking.selected_duration_minutes} minutes

{meeting.meeting_type.description or ''}
"""
            else:
                # Fallback if we can't get the booking
                title = meeting.meeting_type.name
                description = f"Meeting booked via {meeting.meeting_type.name}"
        else:
            # Direct booking
            title = meeting.meeting_type.name
            description = f"""Meeting booked via {meeting.meeting_type.name}
        
Participant: {meeting.participant.name}
Email: {meeting.participant.email}
Phone: {meeting.participant.phone or 'Not provided'}

Meeting Link: {meeting.meeting_url or 'Will be provided'}

Notes: {meeting.booking_data.get('notes', 'No additional notes')}
"""
        
        event_response = await calendar_client.create_event(
            account_id=account_id,
            calendar_id=target_calendar,
            title=title,
            start_time=meeting.start_time.isoformat(),
            end_time=meeting.end_time.isoformat(),
            description=description,
            location=meeting.meeting_location or meeting.meeting_url or '',
            attendees=attendees if attendees else None,
            conference_provider=conference_provider  # This will auto-create conference if provider is set
        )
        
        logger.info(f"Event creation response: {event_response}")
        
        # UniPile might return the ID as 'id' or 'event_id' or in a 'data' wrapper
        event_id = None
        if event_response:
            if isinstance(event_response, dict):
                # Check different possible response formats
                event_id = event_response.get('id') or event_response.get('event_id')
                # Check if response is wrapped in 'data'
                if not event_id and 'data' in event_response:
                    event_data = event_response['data']
                    if isinstance(event_data, dict):
                        event_id = event_data.get('id') or event_data.get('event_id')
                
                # Also check for conference URL in the create response
                conference_url = None
                if 'conference' in event_response and 'url' in event_response['conference']:
                    conference_url = event_response['conference']['url']
                elif 'data' in event_response and 'conference' in event_response['data']:
                    if 'url' in event_response['data']['conference']:
                        conference_url = event_response['data']['conference']['url']
                
                if conference_url:
                    meeting.meeting_url = conference_url
                    meeting.booking_data['conference_url'] = conference_url
                    logger.info(f"📹 Conference URL from create response: {conference_url}")
        
        if event_id:
            # Update meeting with calendar event ID
            meeting.calendar_event_id = event_id  # Save to the actual field
            meeting.booking_data['calendar_event_id'] = event_id  # Also save to booking_data for reference
            
            # If we created a conference, fetch the event to get the conference URL
            if conference_provider:
                logger.info(f"Fetching event details to get conference URL...")
                try:
                    # Get events from the calendar to find our newly created event
                    from datetime import timedelta
                    start_date = (meeting.start_time - timedelta(minutes=1)).isoformat()
                    end_date = (meeting.end_time + timedelta(minutes=1)).isoformat()
                    
                    events_response = await calendar_client.get_events(
                        account_id=account_id,
                        calendar_id=primary_calendar,
                        start_date=start_date,
                        end_date=end_date,
                        limit=10
                    )
                    
                    if events_response and 'data' in events_response:
                        # Find our event by ID
                        for event in events_response['data']:
                            if event.get('id') == event_id:
                                if 'conference' in event and 'url' in event['conference']:
                                    conference_url = event['conference']['url']
                                    meeting.meeting_url = conference_url
                                    meeting.booking_data['conference_url'] = conference_url
                                    logger.info(f"📹 Conference URL retrieved: {conference_url}")
                                break
                except Exception as e:
                    logger.warning(f"Could not fetch conference URL: {e}")
            
            from asgiref.sync import sync_to_async
            await sync_to_async(meeting.save)(update_fields=['booking_data', 'meeting_url', 'calendar_event_id'])
            logger.info(f"✅ Calendar event created successfully: {event_id}")
        else:
            logger.error(f"❌ Failed to create calendar event: {event_response}")
            
    except Exception as e:
        logger.error(f"Error creating calendar event: {e}")


@shared_task(bind=True)
def send_facilitator_p1_invitation(self, booking_id: str, tenant_schema: str = None):
    """
    Send invitation email to Participant 1 with configuration link
    
    Args:
        booking_id: UUID of the FacilitatorBooking
        tenant_schema: Tenant schema name
    """
    try:
        # Get tenant schema from task headers if not provided
        from django_tenants.utils import schema_context
        
        if not tenant_schema:
            if hasattr(self.request, 'headers') and self.request.headers:
                tenant_schema = self.request.headers.get('tenant_schema')
            if not tenant_schema:
                tenant_schema = getattr(self.request, 'tenant_schema', None)
        
        if not tenant_schema or tenant_schema == 'public':
            logger.error(f"No tenant schema found for task {self.request.id}")
            raise ValueError("Tenant schema required for participant invitation")
        
        # Execute in tenant context
        with schema_context(tenant_schema):
            from .models import FacilitatorBooking
            booking = FacilitatorBooking.objects.select_related(
                'meeting_type',
                'facilitator'
            ).get(id=booking_id)
            
            # Build the configuration link
            # TODO: Use proper domain configuration
            base_url = settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:3000'
            config_url = f"{base_url}/book/facilitator/{booking.participant_1_token}/participant1/"
            
            # Email content
            subject = f"Configure meeting with {booking.participant_2_name or booking.participant_2_email}"
            
            body = f"""Hi {booking.participant_1_name or 'there'},

{booking.facilitator.get_full_name() or booking.facilitator.username} has initiated a meeting between you and {booking.participant_2_name or booking.participant_2_email}.

You're invited to:
1. Choose the meeting duration
2. Select the meeting location type
3. Propose several time options

Please click the link below to configure the meeting:
{config_url}

This link expires on {booking.expires_at.strftime('%B %d, %Y at %I:%M %p')}.

Once you've made your selections, {booking.participant_2_name or booking.participant_2_email} will receive a link to choose from your proposed times.

Best regards,
{booking.facilitator.get_full_name() or booking.facilitator.username}"""
            
            # Send the actual email
            from django.core.mail import send_mail
            
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[booking.participant_1_email],
                fail_silently=False,
            )
            
            logger.info(f"Sent P1 invitation email to {booking.participant_1_email}")
            logger.info(f"Configuration URL: {config_url}")
            
    except Exception as e:
        logger.error(f"Failed to send participant 1 invitation: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True)
def send_facilitator_p2_invitation(self, booking_id: str, tenant_schema: str = None):
    """
    Send invitation email to Participant 2 with booking link
    
    Args:
        booking_id: UUID of the FacilitatorBooking
        tenant_schema: Tenant schema name
    """
    try:
        # Get tenant schema from task headers if not provided
        from django_tenants.utils import schema_context
        
        if not tenant_schema:
            if hasattr(self.request, 'headers') and self.request.headers:
                tenant_schema = self.request.headers.get('tenant_schema')
            if not tenant_schema:
                tenant_schema = getattr(self.request, 'tenant_schema', None)
        
        if not tenant_schema or tenant_schema == 'public':
            logger.error(f"No tenant schema found for task {self.request.id}")
            raise ValueError("Tenant schema required for participant invitation")
        
        # Execute in tenant context
        with schema_context(tenant_schema):
            from .models import FacilitatorBooking
            booking = FacilitatorBooking.objects.select_related(
                'meeting_type',
                'facilitator'
            ).get(id=booking_id)
            
            # Format the email content
            facilitator_settings = booking.meeting_type.facilitator_settings or {}
            location_display = {
                'google_meet': 'Google Meet',
                'teams': 'Microsoft Teams',
                'zoom': 'Zoom',
                'phone': 'Phone Call',
                'in_person': 'In Person',
                'custom': 'Custom Location'
            }.get(booking.selected_location_type, booking.selected_location_type)
            
            # Format time slots
            slots_text = "\n".join([
                f"• {slot['start']} - {slot['end']}"
                for slot in booking.selected_slots
            ])
            
            # Email content
            subject = f"Select a meeting time with {booking.participant_1_name}"
            
            body = f"""Hi {booking.participant_2_name or 'there'},

{booking.participant_1_name} has proposed a meeting with the following details:

📅 Duration: {booking.selected_duration_minutes} minutes
📍 Location: {location_display}
{f'📍 Address: {booking.selected_location_details.get("address")}' if booking.selected_location_type == 'in_person' else ''}
{f'💬 Message: {booking.participant_1_message}' if booking.participant_1_message else ''}

Please select from these time options:
{slots_text}

Click here to select a time: {booking.get_shareable_link()}

This link expires on {booking.expires_at.strftime('%B %d, %Y at %I:%M %p')}.

Best regards,
{booking.facilitator.get_full_name() or booking.facilitator.username}
"""
            
            # Send the actual email
            from django.core.mail import send_mail
            
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[booking.participant_2_email],
                fail_silently=False,
            )
            
            logger.info(f"Sent P2 invitation email to {booking.participant_2_email}")
            logger.info(f"Booking link: {booking.get_shareable_link()}")
            
    except Exception as e:
        logger.error(f"Failed to send participant 2 invitation: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True)
def send_facilitator_confirmations(self, meeting_id: str, tenant_schema: str = None):
    """
    Send confirmation emails to all parties after successful facilitator booking
    
    Args:
        meeting_id: UUID of the ScheduledMeeting
        tenant_schema: Tenant schema name
    """
    try:
        # Get tenant schema from task headers if not provided
        from django_tenants.utils import schema_context
        
        if not tenant_schema:
            if hasattr(self.request, 'headers') and self.request.headers:
                tenant_schema = self.request.headers.get('tenant_schema')
            if not tenant_schema:
                tenant_schema = getattr(self.request, 'tenant_schema', None)
        
        if not tenant_schema or tenant_schema == 'public':
            logger.error(f"No tenant schema found for task {self.request.id}")
            raise ValueError("Tenant schema required for confirmations")
        
        # Execute in tenant context
        with schema_context(tenant_schema):
            from .models import ScheduledMeeting, FacilitatorBooking
            meeting = ScheduledMeeting.objects.select_related(
                'meeting_type',
                'host'
            ).get(id=meeting_id)
            
            # Get the facilitator booking
            booking_id = meeting.booking_data.get('facilitator_booking_id')
            if booking_id:
                booking = FacilitatorBooking.objects.get(id=booking_id)
                
                # Send to Participant 1
                subject_p1 = "✅ Meeting Confirmed"
                body_p1 = f"""Your meeting with {booking.participant_2_name} is scheduled for:
{meeting.start_time.strftime('%B %d, %Y at %I:%M %p')} - {meeting.end_time.strftime('%I:%M %p')}
Location: {booking.selected_location_type}

The calendar invitation has been sent to your email."""
                
                # Send to Participant 2
                subject_p2 = "✅ Meeting Confirmed"
                body_p2 = f"""Your meeting with {booking.participant_1_name} is scheduled for:
{meeting.start_time.strftime('%B %d, %Y at %I:%M %p')} - {meeting.end_time.strftime('%I:%M %p')}
Location: {booking.selected_location_type}

The calendar invitation has been sent to your email."""
                
                # Send to Facilitator
                subject_facilitator = "✅ Meeting Successfully Scheduled"
                body_facilitator = f"""You've facilitated a meeting between:
- {booking.participant_1_name} ({booking.participant_1_email})
- {booking.participant_2_name} ({booking.participant_2_email})

Time: {meeting.start_time.strftime('%B %d, %Y at %I:%M %p')} - {meeting.end_time.strftime('%I:%M %p')}
Location: {booking.selected_location_type}

{'You are included in this meeting.' if booking.meeting_type.facilitator_settings.get('include_facilitator', True) else 'You are not included in this meeting.'}"""
                
                # TODO: Implement actual email sending
                logger.info(f"Would send confirmation emails")
                logger.info(f"P1: {booking.participant_1_email} - {subject_p1}")
                logger.info(f"P2: {booking.participant_2_email} - {subject_p2}")
                logger.info(f"Facilitator: {booking.facilitator.email} - {subject_facilitator}")
            
    except Exception as e:
        logger.error(f"Failed to send facilitator confirmations: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True)
def send_booking_confirmation_email(self, meeting_id: str):
    """
    Send booking confirmation email
    
    Args:
        meeting_id: UUID of the ScheduledMeeting
    """
    try:
        # Get tenant schema from task headers
        from django_tenants.utils import schema_context
        
        # Try to get from request headers (proper way for Celery tasks)
        tenant_schema = None
        if hasattr(self.request, 'headers') and self.request.headers:
            tenant_schema = self.request.headers.get('tenant_schema')
        
        # Fallback: try to get from request attributes (legacy)
        if not tenant_schema:
            tenant_schema = getattr(self.request, 'tenant_schema', None)
        
        if not tenant_schema:
            # Last resort: try to extract from queue name
            delivery_info = getattr(self.request, 'delivery_info', None)
            if delivery_info:
                queue_name = delivery_info.get('routing_key', '')
                if '_' in queue_name:
                    tenant_schema = queue_name.split('_')[0]
        
        if not tenant_schema or tenant_schema == 'public':
            logger.error(f"No tenant schema found for task {self.request.id}")
            raise ValueError("Tenant schema required for booking confirmation email task")
        
        # Execute in tenant context
        with schema_context(tenant_schema):
            meeting = ScheduledMeeting.objects.select_related(
                'meeting_type', 
                'host', 
                'participant'
            ).get(id=meeting_id)
            
            # TODO: Implement email sending via UniPile or other email service
            logger.info(f"Would send confirmation email for meeting {meeting_id}")
        
    except ScheduledMeeting.DoesNotExist:
        logger.error(f"Meeting {meeting_id} not found")
    except Exception as e:
        logger.error(f"Failed to send confirmation email: {e}")