#!/usr/bin/env python
"""
Test script to debug facilitator meeting calendar event creation.
Run this after participant 2 confirms their time slot.
"""
import os
import sys
import django
import asyncio
import logging
from datetime import datetime, timedelta
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

# Setup tenant context
from django_tenants.utils import schema_context

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from django.contrib.auth import get_user_model
from communications.scheduling.models import (
    FacilitatorBooking, 
    MeetingType, 
    ScheduledMeeting,
    SchedulingProfile
)
from communications.scheduling.services import FacilitatorBookingProcessor
from communications.unipile.clients.calendar import UnipileCalendarClient

User = get_user_model()


async def test_calendar_event_creation():
    """Test calendar event creation for facilitator meetings"""
    
    # Get the most recent facilitator booking
    from asgiref.sync import sync_to_async
    
    booking = await sync_to_async(
        FacilitatorBooking.objects.filter(
            status='completed'
        ).order_by('-created_at').first
    )()
    
    if not booking:
        logger.error("No completed facilitator booking found")
        return
    
    logger.info(f"Testing with booking ID: {booking.id}")
    logger.info(f"Booking details:")
    logger.info(f"  - Facilitator: {booking.facilitator}")
    logger.info(f"  - P1: {booking.participant_1_name} ({booking.participant_1_email})")
    logger.info(f"  - P2: {booking.participant_2_name} ({booking.participant_2_email})")
    logger.info(f"  - Selected slot: {booking.selected_slot}")
    logger.info(f"  - Status: {booking.status}")
    
    # Check if a meeting was created
    meeting = await sync_to_async(
        ScheduledMeeting.objects.filter(
            facilitator_booking=booking
        ).first
    )()
    
    if not meeting:
        logger.error("No ScheduledMeeting found for this booking")
        return
    
    logger.info(f"\nScheduledMeeting found:")
    logger.info(f"  - ID: {meeting.id}")
    logger.info(f"  - Start: {meeting.start_time}")
    logger.info(f"  - End: {meeting.end_time}")
    logger.info(f"  - Calendar event ID: {meeting.calendar_event_id or 'Not created'}")
    logger.info(f"  - Meeting URL: {meeting.meeting_url or 'None'}")
    logger.info(f"  - Conversation ID: {meeting.conversation_id}")
    
    # Check the facilitator's scheduling profile
    profile = await sync_to_async(
        SchedulingProfile.objects.filter(
            user=booking.facilitator
        ).select_related('calendar_connection').first
    )()
    
    if not profile:
        logger.error("No SchedulingProfile found for facilitator")
        return
    
    logger.info(f"\nSchedulingProfile:")
    logger.info(f"  - ID: {profile.id}")
    logger.info(f"  - Calendar connection: {profile.calendar_connection}")
    
    if profile.calendar_connection:
        logger.info(f"  - UniPile account ID: {profile.calendar_connection.unipile_account_id}")
        logger.info(f"  - Connection status: {profile.calendar_connection.connection_status}")
        logger.info(f"  - Selected calendar ID: {profile.calendar_connection.selected_calendar_id}")
    else:
        logger.error("  - No calendar connection found!")
        return
    
    # Now let's try to manually create the calendar event
    logger.info("\n" + "="*50)
    logger.info("Attempting to manually create calendar event...")
    logger.info("="*50)
    
    service = FacilitatorBookingProcessor(facilitator=booking.facilitator)
    
    # Test UniPile connection
    logger.info("\nTesting UniPile connection...")
    calendar_client = UnipileCalendarClient()
    
    try:
        # Test if we can list calendars
        calendars_response = await calendar_client.list_calendars(
            profile.calendar_connection.unipile_account_id
        )
        logger.info(f"UniPile calendars response: {calendars_response}")
        
        if calendars_response and 'data' in calendars_response:
            logger.info(f"Found {len(calendars_response['data'])} calendars")
            for cal in calendars_response['data'][:3]:  # Show first 3
                logger.info(f"  - {cal.get('name')} (ID: {cal.get('id')})")
    except Exception as e:
        logger.error(f"Failed to list calendars: {e}")
        return
    
    # Try to create the event
    logger.info("\nAttempting to create calendar event...")
    
    # Prepare event data
    start_time = meeting.start_time
    end_time = meeting.end_time
    
    event_data = {
        'title': f"{booking.meeting_type.name} - {booking.participant_1_name} & {booking.participant_2_name}",
        'description': f"""Facilitator Meeting

Participants:
- {booking.participant_1_name} ({booking.participant_1_email})
- {booking.participant_2_name} ({booking.participant_2_email})

Facilitated by: {booking.facilitator.get_full_name()}

Meeting Type: {booking.meeting_type.name}
""",
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'UTC'
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'UTC'
        },
        'attendees': [
            {
                'email': booking.participant_1_email,
                'displayName': booking.participant_1_name,
                'responseStatus': 'needsAction'
            },
            {
                'email': booking.participant_2_email,
                'displayName': booking.participant_2_name,
                'responseStatus': 'needsAction'
            }
        ],
        'conferenceData': {
            'createRequest': {
                'requestId': f"facilitator-{booking.id}",
                'conferenceSolutionKey': {'type': 'hangoutsMeet'}
            }
        }
    }
    
    logger.info(f"Event data: {event_data}")
    
    try:
        # Call UniPile to create the event
        result = await calendar_client.create_event(
            account_id=profile.calendar_connection.unipile_account_id,
            calendar_id=profile.calendar_connection.selected_calendar_id or 'primary',
            event_data=event_data,
            send_updates='all'
        )
        
        logger.info(f"UniPile create event response: {result}")
        
        if result and 'data' in result:
            event_id = result['data'].get('id')
            meet_link = None
            
            if 'conferenceData' in result['data']:
                conference = result['data']['conferenceData']
                if 'entryPoints' in conference:
                    for entry in conference['entryPoints']:
                        if entry.get('entryPointType') == 'video':
                            meet_link = entry.get('uri')
                            break
            
            logger.info(f"✅ Calendar event created successfully!")
            logger.info(f"  - Event ID: {event_id}")
            logger.info(f"  - Meet link: {meet_link}")
            
            # Update the meeting with the calendar event ID
            meeting.calendar_event_id = event_id
            meeting.meeting_url = meet_link
            await sync_to_async(meeting.save)()
            
            logger.info("✅ Meeting record updated with calendar event details")
        else:
            logger.error(f"Failed to create calendar event: No data in response")
            
    except Exception as e:
        logger.error(f"Failed to create calendar event: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def check_missing_calendar_events():
    """Check for meetings missing calendar events and attempt to create them"""
    
    logger.info("\nChecking for meetings without calendar events...")
    
    # Find all completed facilitator meetings without calendar events
    meetings = ScheduledMeeting.objects.filter(
        facilitator_booking__isnull=False,
        facilitator_booking__status='completed',
        calendar_event_id__isnull=True
    ).select_related('facilitator_booking', 'meeting_type')
    
    count = await meetings.acount()
    logger.info(f"Found {count} meetings without calendar events")
    
    async for meeting in meetings:
        booking = meeting.facilitator_booking
        logger.info(f"\nMeeting {meeting.id}:")
        logger.info(f"  - Created: {meeting.created_at}")
        logger.info(f"  - Start: {meeting.start_time}")
        logger.info(f"  - Facilitator: {booking.facilitator}")
        logger.info(f"  - Participants: {booking.participant_1_name}, {booking.participant_2_name}")


async def main():
    """Main test function"""
    logger.info("="*60)
    logger.info("FACILITATOR CALENDAR EVENT CREATION TEST")
    logger.info("="*60)
    
    # Run the test in oneotalent tenant context
    with schema_context('oneotalent'):
        await test_calendar_event_creation()
        await check_missing_calendar_events()
    
    logger.info("\n" + "="*60)
    logger.info("TEST COMPLETE")
    logger.info("="*60)


if __name__ == "__main__":
    asyncio.run(main())