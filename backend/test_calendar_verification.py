#!/usr/bin/env python
"""
Comprehensive test to verify calendar events are created in the correct calendar
"""

import os
import sys
import django
import asyncio
import logging
from datetime import datetime, timedelta
import random

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model
from communications.scheduling.models import MeetingType, FacilitatorBooking, ScheduledMeeting, SchedulingProfile
from communications.scheduling.services import FacilitatorBookingProcessor
from communications.unipile.clients.calendar import UnipileCalendarClient
from communications.unipile.core.client import UnipileClient
from django.conf import settings
from asgiref.sync import async_to_sync

User = get_user_model()


def test_calendar_event_creation():
    """Test that events are created in the correct calendar"""
    
    with schema_context('oneotalent'):
        logger.info("="*60)
        logger.info("🧪 TESTING CALENDAR EVENT CREATION IN CORRECT CALENDAR")
        logger.info("="*60)
        
        # Get user
        user = User.objects.filter(email='josh@oneodigital.com').first()
        if not user:
            logger.error("❌ User not found")
            return
        logger.info(f"✅ User: {user.email}")
        
        # Get the Interview meeting type
        meeting_type = MeetingType.objects.filter(
            user=user,
            name='Interview'
        ).first()
        
        if not meeting_type:
            logger.error("❌ Interview meeting type not found")
            return
            
        logger.info(f"\n📋 Meeting Type Configuration:")
        logger.info(f"  Name: {meeting_type.name}")
        logger.info(f"  Calendar ID: {meeting_type.calendar_id}")
        logger.info(f"  Calendar Name: {meeting_type.calendar_name}")
        logger.info(f"  Mode: {meeting_type.meeting_mode}")
        
        # Ensure it's in facilitator mode
        if meeting_type.meeting_mode != 'facilitator':
            meeting_type.meeting_mode = 'facilitator'
            meeting_type.save()
            logger.info("  ✅ Updated to facilitator mode")
        
        # Create processor
        processor = FacilitatorBookingProcessor(meeting_type)
        
        # Create unique time slot to avoid conflicts
        hour = random.randint(8, 16)
        minute = random.choice([0, 30])
        tomorrow = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=1)
        
        slots = [
            {'start': tomorrow.isoformat(), 'end': (tomorrow + timedelta(minutes=30)).isoformat()}
        ]
        
        logger.info(f"\n📅 Creating booking for: {tomorrow.strftime('%Y-%m-%d %H:%M')}")
        
        # Step 1: Create booking
        participant_data = {
            'email': f'test1_{datetime.now().timestamp()}@example.com',
            'name': 'Test Participant One',
            'participant_2_email': f'test2_{datetime.now().timestamp()}@example.com',
            'participant_2_name': 'Test Participant Two'
        }
        
        meeting_params = {
            'duration': 30,
            'location_type': 'google_meet'
        }
        
        booking = async_to_sync(processor.process_facilitator_step1)(
            participant_data=participant_data,
            meeting_params=meeting_params,
            selected_slots=slots
        )
        
        logger.info(f"✅ Booking created: {booking.id}")
        
        # Step 2: Confirm P2
        meeting = async_to_sync(processor.process_facilitator_step2)(
            booking=booking,
            participant_data={'name': 'Test Participant Two'},
            selected_slot=slots[0]
        )
        
        logger.info(f"✅ Meeting scheduled: {meeting.id}")
        
        # Check the calendar event
        logger.info(f"\n📊 Calendar Event Details:")
        logger.info(f"  Event ID: {meeting.calendar_event_id or 'NOT CREATED'}")
        logger.info(f"  Meeting URL: {meeting.meeting_url or 'None'}")
        
        # Verify with UniPile API which calendar the event was created in
        if meeting.calendar_event_id:
            logger.info(f"\n🔍 Verifying event location in Google Calendar...")
            
            profile = SchedulingProfile.objects.filter(user=user).select_related('calendar_connection').first()
            if profile and profile.calendar_connection:
                account_id = profile.calendar_connection.unipile_account_id
                
                # Initialize UniPile client
                client = UnipileClient(settings.UNIPILE_DSN, settings.UNIPILE_API_KEY)
                calendar_client = UnipileCalendarClient(client)
                
                # Try to get the event from the configured calendar
                logger.info(f"  Checking in configured calendar: {meeting_type.calendar_id}")
                
                try:
                    # Get events from the specific calendar
                    response = async_to_sync(calendar_client.list_events)(
                        account_id=account_id,
                        calendar_id=meeting_type.calendar_id,
                        min_time=tomorrow.isoformat(),
                        max_time=(tomorrow + timedelta(hours=1)).isoformat()
                    )
                    
                    if response and 'data' in response:
                        events = response['data']
                        found = False
                        for event in events:
                            if event.get('id') == meeting.calendar_event_id:
                                found = True
                                logger.info(f"  ✅ Event FOUND in {meeting_type.calendar_name} calendar!")
                                logger.info(f"     Title: {event.get('summary', 'No title')}")
                                logger.info(f"     Time: {event.get('start', {}).get('dateTime', 'No time')}")
                                break
                        
                        if not found:
                            logger.warning(f"  ⚠️ Event NOT found in {meeting_type.calendar_name} calendar")
                            
                            # Check primary calendar as fallback
                            logger.info(f"\n  Checking primary calendar...")
                            response = async_to_sync(calendar_client.list_events)(
                                account_id=account_id,
                                calendar_id='primary',
                                min_time=tomorrow.isoformat(),
                                max_time=(tomorrow + timedelta(hours=1)).isoformat()
                            )
                            
                            if response and 'data' in response:
                                for event in response['data']:
                                    if event.get('id') == meeting.calendar_event_id:
                                        logger.warning(f"  ⚠️ Event found in PRIMARY calendar (should be in {meeting_type.calendar_name})")
                                        break
                    
                except Exception as e:
                    logger.error(f"  ❌ Error verifying event: {e}")
            
            logger.info("\n" + "="*60)
            logger.info("✅ TEST COMPLETE - Calendar event created successfully!")
            logger.info("="*60)
        else:
            logger.error("\n❌ No calendar event ID - event may not have been created")


if __name__ == "__main__":
    test_calendar_event_creation()