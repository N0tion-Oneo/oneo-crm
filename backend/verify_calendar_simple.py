#!/usr/bin/env python
"""
Simple verification of calendar events in Google Calendar
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
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model
from communications.scheduling.models import SchedulingProfile, ScheduledMeeting
from communications.unipile.clients.calendar import UnipileCalendarClient
from asgiref.sync import async_to_sync

User = get_user_model()


def verify_calendar_events():
    """Verify calendar events exist in Google Calendar"""
    
    with schema_context('oneotalent'):
        # Get user and calendar connection
        user = User.objects.filter(email='josh@oneodigital.com').first()
        if not user:
            logger.error("❌ User not found")
            return
            
        logger.info(f"✅ User: {user.email}")
        
        profile = SchedulingProfile.objects.filter(user=user).select_related('calendar_connection').first()
        
        if not profile or not profile.calendar_connection:
            logger.error("❌ No calendar connection found")
            return
            
        account_id = profile.calendar_connection.unipile_account_id
        # Use primary calendar
        calendar_id = 'primary'
        
        logger.info(f"📅 Calendar Account: {account_id}")
        logger.info(f"📅 Calendar ID: {calendar_id}")
        
        # Initialize UniPile client
        client = UnipileCalendarClient()
        
        # Get events for tomorrow (when our test events are scheduled)
        tomorrow = datetime.now() + timedelta(days=1)
        start_date = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        logger.info(f"\n🔍 Fetching events for {tomorrow.strftime('%Y-%m-%d')}...")
        
        try:
            # Get events from UniPile
            response = async_to_sync(client.list_events)(
                account_id=account_id,
                calendar_id=calendar_id,
                min_time=start_date.isoformat(),
                max_time=end_date.isoformat()
            )
            
            if response and 'data' in response:
                events = response['data']
                logger.info(f"\n✅ Found {len(events)} events in Google Calendar:")
                logger.info("="*60)
                
                # Check our test event IDs first
                test_event_ids = {
                    '7mfoak56mf32v9217l73n85ffk': None,
                    'a4dnu7umdpcc9he64fvo07mgp0': None,
                    'uav8ls0pm8ko0fd62103bga1jk': None
                }
                
                for event in events:
                    event_id = event.get('id')
                    title = event.get('summary', 'No title')
                    start = event.get('start', {}).get('dateTime', 'No time')
                    
                    # Check if this is one of our test events
                    if event_id in test_event_ids:
                        test_event_ids[event_id] = True
                        logger.info(f"✅ FOUND TEST EVENT: {event_id}")
                    
                    logger.info(f"\nEvent: {title}")
                    logger.info(f"  ID: {event_id}")
                    logger.info(f"  Time: {start}")
                    
                    # Check attendees
                    attendees = event.get('attendees', [])
                    if attendees:
                        logger.info(f"  Attendees: {', '.join([a.get('email', 'unknown') for a in attendees])}")
                    
                    # Check for meeting link
                    if 'hangoutLink' in event:
                        logger.info(f"  Meet Link: {event['hangoutLink']}")
                
                logger.info("\n" + "="*60)
                logger.info("📋 TEST EVENT STATUS:")
                for test_id, found in test_event_ids.items():
                    if found:
                        logger.info(f"  ✅ {test_id} - FOUND in calendar")
                    else:
                        logger.info(f"  ❌ {test_id} - NOT found in calendar")
                        
            else:
                logger.warning("❌ No events found or error in response")
                if response:
                    logger.warning(f"Response: {response}")
                
        except Exception as e:
            logger.error(f"❌ Error fetching events: {e}")
            import traceback
            traceback.print_exc()
        
        # Check recent meetings in our database
        logger.info("\n" + "="*60)
        logger.info("📊 Recent meetings in database:")
        logger.info("="*60)
        
        meetings = ScheduledMeeting.objects.filter(
            start_time__gte=start_date,
            start_time__lte=end_date,
            calendar_event_id__isnull=False
        ).order_by('start_time')[:10]
        
        for meeting in meetings:
            logger.info(f"\nMeeting: {meeting.id}")
            logger.info(f"  Start: {meeting.start_time}")
            logger.info(f"  Calendar Event ID: {meeting.calendar_event_id}")
            if meeting.facilitator_booking:
                fb = meeting.facilitator_booking
                logger.info(f"  Participants: {fb.participant_1_name}, {fb.participant_2_name}")


def main():
    """Main function"""
    logger.info("="*60)
    logger.info("🔍 VERIFYING CALENDAR EVENTS IN GOOGLE CALENDAR")
    logger.info("="*60)
    
    verify_calendar_events()
    
    logger.info("\n" + "="*60)
    logger.info("VERIFICATION COMPLETE")
    logger.info("="*60)


if __name__ == "__main__":
    main()