"""
Celery tasks for scheduling functionality
"""
import logging
from celery import shared_task
from django.conf import settings
from asgiref.sync import async_to_sync
from datetime import datetime, timezone

from .models import ScheduledMeeting, SchedulingProfile
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
    
    logger.info(f"Using primary calendar: {primary_calendar}")
    
    # Create the event
    try:
        logger.info(f"Creating calendar event for meeting {meeting.id}")
        
        # Determine conference provider based on location type
        conference_provider = None
        if meeting.meeting_type.location_type == 'google_meet':
            conference_provider = 'google_meet'
            logger.info("Adding Google Meet conference to calendar event")
        elif meeting.meeting_type.location_type == 'teams':
            conference_provider = 'teams'
            logger.info("Adding Microsoft Teams conference to calendar event")
        
        # Prepare description
        description = f"""Meeting booked via {meeting.meeting_type.name}
        
Participant: {meeting.participant.name}
Email: {meeting.participant.email}
Phone: {meeting.participant.phone or 'Not provided'}

Meeting Link: {meeting.meeting_url or 'Will be provided'}

Notes: {meeting.booking_data.get('notes', 'No additional notes')}
"""
        
        event_response = await calendar_client.create_event(
            account_id=account_id,
            calendar_id=primary_calendar,
            title=meeting.meeting_type.name,
            start_time=meeting.start_time.isoformat(),
            end_time=meeting.end_time.isoformat(),
            description=description,
            location=meeting.meeting_location or meeting.meeting_url or '',
            attendees=[meeting.participant.email] if meeting.participant.email else None,
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
            # Store the event ID in the booking_data JSON field since external_calendar_event_id doesn't exist
            meeting.booking_data['calendar_event_id'] = event_id
            
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
            
            await meeting.asave(update_fields=['booking_data', 'meeting_url'])
            logger.info(f"✅ Calendar event created successfully: {event_id}")
        else:
            logger.error(f"❌ Failed to create calendar event: {event_response}")
            
    except Exception as e:
        logger.error(f"Error creating calendar event: {e}")


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