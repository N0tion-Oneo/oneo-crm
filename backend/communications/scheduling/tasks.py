"""
Celery tasks for scheduling functionality
"""
import logging
from celery import shared_task
from django.conf import settings
from asgiref.sync import async_to_sync
from datetime import datetime, timezone

from .models import ScheduledMeeting, SchedulingProfile
from communications.unipile.client import UnipileClient
from communications.unipile.calendar import UnipileCalendarClient

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_calendar_invite(self, meeting_id: str):
    """
    Send calendar invite for a scheduled meeting
    
    Args:
        meeting_id: UUID of the ScheduledMeeting
    """
    try:
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
        
        if not profile or not profile.calendar_connection:
            logger.warning(f"No calendar connection for user {meeting.host.id}")
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
    calendar_client = UnipileCalendarClient(client)
    
    # Get calendars to find primary one
    calendars_response = await calendar_client.get_calendars(account_id)
    if not calendars_response or 'data' not in calendars_response:
        logger.error("Failed to get calendars")
        return
    
    # Find primary calendar
    primary_calendar = None
    for calendar in calendars_response['data']:
        if calendar.get('is_primary'):
            primary_calendar = calendar['id']
            break
    
    if not primary_calendar and calendars_response['data']:
        # Use first calendar if no primary
        primary_calendar = calendars_response['data'][0]['id']
    
    if not primary_calendar:
        logger.error("No calendar found")
        return
    
    # Prepare event data
    event_data = {
        'title': meeting.meeting_type.name,
        'description': f"""Meeting booked via {meeting.meeting_type.name}
        
Participant: {meeting.participant.name}
Email: {meeting.participant.email}
Phone: {meeting.participant.phone or 'Not provided'}

Meeting Link: {meeting.meeting_url or 'Will be provided'}

Notes: {meeting.booking_data.get('notes', 'No additional notes')}
""",
        'start_time': meeting.start_time.isoformat(),
        'end_time': meeting.end_time.isoformat(),
        'timezone': meeting.timezone,
        'location': meeting.meeting_location or meeting.meeting_url or '',
        'attendees': [
            {
                'email': meeting.participant.email,
                'name': meeting.participant.name,
                'status': 'needsAction'
            }
        ],
        'reminders': [
            {'method': 'email', 'minutes': 60},  # 1 hour before
            {'method': 'popup', 'minutes': 15}   # 15 minutes before
        ]
    }
    
    # Create the event
    try:
        event_response = await calendar_client.create_event(
            account_id=account_id,
            calendar_id=primary_calendar,
            event_data=event_data
        )
        
        if event_response and 'data' in event_response:
            # Update meeting with calendar event ID
            meeting.external_calendar_event_id = event_response['data'].get('id')
            await meeting.asave(update_fields=['external_calendar_event_id'])
            logger.info(f"Calendar event created: {event_response['data'].get('id')}")
        else:
            logger.error(f"Failed to create calendar event: {event_response}")
            
    except Exception as e:
        logger.error(f"Error creating calendar event: {e}")


@shared_task
def send_booking_confirmation_email(meeting_id: str):
    """
    Send booking confirmation email
    
    Args:
        meeting_id: UUID of the ScheduledMeeting
    """
    try:
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