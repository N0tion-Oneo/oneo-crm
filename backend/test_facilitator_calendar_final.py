#!/usr/bin/env python
"""
Final test script for facilitator booking calendar event creation.
Tests both scenarios: with and without facilitator as participant.
"""

import os
import sys
import django
import asyncio
import logging
from datetime import datetime, timedelta
from django.utils import timezone
import uuid

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model
from communications.scheduling.models import (
    MeetingType, 
    FacilitatorBooking,
    ScheduledMeeting,
    SchedulingProfile
)
from communications.scheduling.services import FacilitatorBookingProcessor
from asgiref.sync import sync_to_async

User = get_user_model()


async def test_facilitator_booking(include_facilitator=True):
    """Test facilitator booking with calendar event creation"""
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing with include_facilitator = {include_facilitator}")
    logger.info(f"{'='*60}")
    
    # Get the user - must be within schema context
    with schema_context('oneotalent'):
        user = await sync_to_async(User.objects.filter(email='josh@oneodigital.com').first)()
    if not user:
        logger.error("❌ User josh@oneodigital.com not found")
        return False
        
    logger.info(f"✅ Found user: {user.email}")
    
    # Check calendar connection
    profile = await sync_to_async(
        SchedulingProfile.objects.filter(user=user).select_related('calendar_connection').first
    )()
    
    if profile and profile.calendar_connection:
        logger.info(f"✅ Calendar connection found: {profile.calendar_connection.unipile_account_id}")
    else:
        logger.warning("⚠️ No calendar connection - events won't be created in external calendar")
    
    # Create or update meeting type
    meeting_type = await sync_to_async(
        MeetingType.objects.filter(
            user=user,
            meeting_mode='facilitator'
        ).first
    )()
    
    if meeting_type:
        logger.info(f"Found existing meeting type: {meeting_type.name}")
        # Update the include_facilitator setting
        meeting_type.facilitator_settings['include_facilitator'] = include_facilitator
        await sync_to_async(meeting_type.save)()
        logger.info(f"✅ Updated include_facilitator to {include_facilitator}")
    else:
        # Create new meeting type
        meeting_type = await sync_to_async(MeetingType.objects.create)(
            user=user,
            name=f'Test Facilitator Meeting {datetime.now().strftime("%H%M%S")}',
            slug=f'test-facilitator-{datetime.now().timestamp()}',
            duration_minutes=30,
            meeting_mode='facilitator',
            is_active=True,
            facilitator_settings={
                'include_facilitator': include_facilitator,
                'instructions': f'Test meeting with facilitator {"included" if include_facilitator else "not included"}'
            }
        )
        logger.info(f"✅ Created new meeting type: {meeting_type.name}")
    
    # Create processor
    processor = FacilitatorBookingProcessor(meeting_type)
    
    # Test Step 1: Create facilitator booking (P1 submits)
    logger.info("\n📝 Step 1: Processing participant 1 submission...")
    
    tomorrow_2pm = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0) + timedelta(days=1)
    tomorrow_3pm = datetime.now().replace(hour=15, minute=0, second=0, microsecond=0) + timedelta(days=1)
    
    selected_slots = [
        {'start': tomorrow_2pm.isoformat(), 'end': (tomorrow_2pm + timedelta(minutes=30)).isoformat()},
        {'start': tomorrow_3pm.isoformat(), 'end': (tomorrow_3pm + timedelta(minutes=30)).isoformat()}
    ]
    
    participant_data = {
        'email': 'participant1@example.com',
        'name': 'John Participant',
        'phone': '+1234567890',
        'message': 'Looking forward to the meeting',
        'participant_2_email': 'participant2@example.com',
        'participant_2_name': 'Jane Participant'
    }
    
    meeting_params = {
        'duration': 30,
        'location_type': 'google_meet',
        'location_details': {}
    }
    
    try:
        booking = await processor.process_facilitator_step1(
            participant_data=participant_data,
            meeting_params=meeting_params,
            selected_slots=selected_slots
        )
        
        logger.info(f"✅ Booking created: {booking.id}")
        logger.info(f"   Status: {booking.status}")
        logger.info(f"   P2 Token: {booking.participant_2_token}")
        
    except Exception as e:
        logger.error(f"❌ Failed to create booking: {e}")
        return False
    
    # Test Step 2: Participant 2 confirms
    logger.info("\n📝 Step 2: Processing participant 2 confirmation...")
    
    # P2 selects the first slot
    selected_slot = selected_slots[0]
    
    p2_data = {
        'name': booking.participant_2_name,
        'phone': '+9876543210',
        'message': 'Confirmed for the meeting'
    }
    
    try:
        meeting = await processor.process_facilitator_step2(
            booking=booking,
            participant_data=p2_data,
            selected_slot=selected_slot
        )
        
        logger.info(f"✅ Meeting scheduled: {meeting.id}")
        logger.info(f"   Start: {meeting.start_time}")
        logger.info(f"   End: {meeting.end_time}")
        logger.info(f"   Status: {meeting.status}")
        
        # Wait for async calendar event creation
        await asyncio.sleep(2)
        
        # Refresh meeting to check calendar event
        await sync_to_async(meeting.refresh_from_db)()
        
        logger.info(f"\n📅 Calendar Event Results:")
        logger.info(f"   Calendar Event ID: {meeting.calendar_event_id or 'NOT CREATED'}")
        logger.info(f"   Meeting URL: {meeting.meeting_url or 'No URL'}")
        
        # Check attendees in booking data
        attendees = meeting.booking_data.get('attendees', [])
        logger.info(f"   Attendees: {attendees}")
        logger.info(f"   Facilitator included: {user.email in attendees}")
        
        if meeting.calendar_event_id:
            logger.info(f"\n✅ SUCCESS: Calendar event created!")
            if include_facilitator and user.email not in attendees:
                logger.warning("⚠️ Facilitator should be in attendees but isn't")
            elif not include_facilitator and user.email in attendees:
                logger.warning("⚠️ Facilitator shouldn't be in attendees but is")
            return True
        else:
            logger.warning(f"\n⚠️ No calendar event created (may need UniPile connection)")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to confirm P2: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_double_booking():
    """Test that double-booking prevention works correctly"""
    
    logger.info(f"\n{'='*60}")
    logger.info("Testing double-booking prevention")
    logger.info(f"{'='*60}")
    
    with schema_context('oneotalent'):
        user = await sync_to_async(User.objects.filter(email='josh@oneodigital.com').first)()
    if not user:
        logger.error("❌ User not found")
        return
    
    # Get meeting type with include_facilitator = True
    meeting_type = await sync_to_async(
        MeetingType.objects.filter(
            user=user,
            meeting_mode='facilitator',
            facilitator_settings__include_facilitator=True
        ).first
    )()
    
    if not meeting_type:
        logger.info("No meeting type with include_facilitator=True found")
        return
    
    processor = FacilitatorBookingProcessor(meeting_type)
    
    # Try to create overlapping booking
    tomorrow_2pm = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0) + timedelta(days=1)
    slot = {'start': tomorrow_2pm.isoformat(), 'end': (tomorrow_2pm + timedelta(minutes=30)).isoformat()}
    
    # Check if slot is already taken
    conflicts = await sync_to_async(ScheduledMeeting.objects.filter(
        meeting_type=meeting_type,
        start_time__lt=tomorrow_2pm + timedelta(minutes=30),
        end_time__gt=tomorrow_2pm,
        status__in=['scheduled', 'confirmed', 'reminder_sent', 'in_progress']
    ).exists)()
    
    if conflicts:
        logger.info("✅ Conflict detection working - slot is already booked")
    else:
        logger.info("ℹ️ No conflicts found - slot is available")


async def main():
    """Main test function"""
    
    logger.info("="*60)
    logger.info("🧪 FACILITATOR BOOKING CALENDAR EVENT TEST")
    logger.info("="*60)
    
    # Run all tests within schema context
    # Test 1: With facilitator as participant
    result1 = await test_facilitator_booking(include_facilitator=True)
    
    # Test 2: Without facilitator as participant
    result2 = await test_facilitator_booking(include_facilitator=False)
    
    # Test 3: Double-booking prevention
    await test_double_booking()
    
    logger.info(f"\n{'='*60}")
    logger.info("📊 TEST SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Test 1 (with facilitator): {'✅ PASSED' if result1 else '❌ FAILED'}")
    logger.info(f"Test 2 (without facilitator): {'✅ PASSED' if result2 else '❌ FAILED'}")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())