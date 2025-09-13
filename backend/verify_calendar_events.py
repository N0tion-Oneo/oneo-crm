#!/usr/bin/env python
"""
Verify calendar events are actually created in Google Calendar via UniPile
"""

import os
import sys
import django
import asyncio
import logging
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model
from communications.scheduling.models import SchedulingProfile, ScheduledMeeting
from communications.unipile.clients.calendar import UnipileCalendarClient
from asgiref.sync import sync_to_async

User = get_user_model()


async def verify_calendar_events():
    """Verify calendar events exist in Google Calendar"""
    
    # Get user and calendar connection within schema context
    user = await sync_to_async(lambda: (
        setattr(verify_calendar_events, '_result', None),
        schema_context('oneotalent').__enter__(),
        setattr(verify_calendar_events, '_result', User.objects.filter(email='josh@oneodigital.com').first()),
        schema_context('oneotalent').__exit__(None, None, None),
        verify_calendar_events._result
    )[-1])()
        if not user:
            logger.error("User not found")
            return
            
        profile = await sync_to_async(
            SchedulingProfile.objects.filter(user=user).select_related('calendar_connection').first
        )()
        
        if not profile or not profile.calendar_connection:
            logger.error("No calendar connection found")
            return
            
        account_id = profile.calendar_connection.unipile_account_id
        calendar_id = profile.calendar_connection.selected_calendar_id or 'primary'
        
        logger.info(f"Checking calendar for account: {account_id}")
        logger.info(f"Calendar ID: {calendar_id}")
        
        # Initialize UniPile client
        client = UnipileCalendarClient()
        
        # Get events for tomorrow (when our test events are scheduled)
        tomorrow = datetime.now() + timedelta(days=1)
        start_date = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        logger.info(f"\nFetching events for {tomorrow.strftime('%Y-%m-%d')}...")
        
        try:
            # Get events from UniPile
            response = await client.list_events(
                account_id=account_id,
                calendar_id=calendar_id,
                min_time=start_date.isoformat(),
                max_time=end_date.isoformat()
            )
            
            if response and 'data' in response:
                events = response['data']
                logger.info(f"\n✅ Found {len(events)} events in Google Calendar:")
                logger.info("="*60)
                
                for event in events:
                    logger.info(f"Event ID: {event.get('id')}")
                    logger.info(f"  Title: {event.get('summary', 'No title')}")
                    logger.info(f"  Start: {event.get('start', {}).get('dateTime', 'No time')}")
                    logger.info(f"  End: {event.get('end', {}).get('dateTime', 'No time')}")
                    
                    # Check attendees
                    attendees = event.get('attendees', [])
                    if attendees:
                        logger.info(f"  Attendees:")
                        for attendee in attendees:
                            logger.info(f"    - {attendee.get('email')} ({attendee.get('responseStatus', 'unknown')})")
                    
                    # Check for meeting link
                    if 'hangoutLink' in event:
                        logger.info(f"  Meet Link: {event['hangoutLink']}")
                    
                    logger.info("-"*40)
                    
                # Check our test event IDs
                logger.info("\n📋 Checking specific test event IDs:")
                test_event_ids = [
                    '7mfoak56mf32v9217l73n85ffk',
                    'a4dnu7umdpcc9he64fvo07mgp0',
                    'uav8ls0pm8ko0fd62103bga1jk'
                ]
                
                found_ids = [e.get('id') for e in events]
                for test_id in test_event_ids:
                    if test_id in found_ids:
                        logger.info(f"  ✅ {test_id} - FOUND in calendar")
                    else:
                        logger.info(f"  ❌ {test_id} - NOT found in calendar")
                        
            else:
                logger.warning("No events found or error in response")
                logger.warning(f"Response: {response}")
                
        except Exception as e:
            logger.error(f"Error fetching events: {e}")
            import traceback
            traceback.print_exc()
        
        # Also check recent meetings in our database
        logger.info("\n📊 Recent meetings in database:")
        logger.info("="*60)
        
        meetings = await sync_to_async(list)(
            ScheduledMeeting.objects.filter(
                start_time__gte=start_date,
                start_time__lte=end_date,
                calendar_event_id__isnull=False
            ).order_by('start_time')[:10]
        )
        
        for meeting in meetings:
            logger.info(f"DB Meeting: {meeting.id}")
            logger.info(f"  Start: {meeting.start_time}")
            logger.info(f"  Calendar Event ID: {meeting.calendar_event_id}")
            logger.info("-"*40)


async def main():
    """Main function"""
    logger.info("="*60)
    logger.info("🔍 VERIFYING CALENDAR EVENTS IN GOOGLE CALENDAR")
    logger.info("="*60)
    
    await verify_calendar_events()
    
    logger.info("\n" + "="*60)
    logger.info("VERIFICATION COMPLETE")
    logger.info("="*60)


if __name__ == "__main__":
    asyncio.run(main())