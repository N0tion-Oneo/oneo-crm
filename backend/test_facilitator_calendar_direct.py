#!/usr/bin/env python
"""
Direct test script for facilitator booking calendar event creation.
Tests the flow directly in Django without authentication.
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
    MeetingType, 
    FacilitatorBooking,
    ScheduledMeeting,
    SchedulingProfile
)
from communications.scheduling.services import FacilitatorBookingProcessor
from asgiref.sync import sync_to_async

User = get_user_model()


async def test_facilitator_booking_with_calendar():
    """Test facilitator booking flow with calendar event creation"""
    
    logger.info("="*60)
    logger.info("🧪 DIRECT FACILITATOR BOOKING CALENDAR TEST")
    logger.info("="*60)
    
    # Find the user Josh and a facilitator meeting type
    user = await sync_to_async(User.objects.filter(email="josh@oneodigital.com").first)()
    
    if not user:
        logger.error("❌ User josh@oneodigital.com not found")
        return False
        
    logger.info(f"✅ Found user: {user.email} (ID: {user.id})")
    
    # Find or create a facilitator meeting type
    meeting_type = await sync_to_async(
        MeetingType.objects.filter(
            user=user,
            meeting_mode='facilitator'
        ).first
    )()
    
    if not meeting_type:
        logger.info("Creating facilitator meeting type...")
        meeting_type = await sync_to_async(MeetingType.objects.create)(
            user=user,
            name="Test Facilitator Meeting",
            slug="test-facilitator",
            duration=30,
            meeting_mode='facilitator',
            is_active=True,
            facilitator_settings={
                'include_facilitator': True,  # This enables conflict checking and calendar events
                'instructions': 'Test facilitator meeting'
            }
        )
        logger.info(f"✅ Created meeting type: {meeting_type.name}")
    else:
        logger.info(f"✅ Found meeting type: {meeting_type.name}")
        # Ensure include_facilitator is set
        if not meeting_type.facilitator_settings.get('include_facilitator'):
            meeting_type.facilitator_settings['include_facilitator'] = True
            await sync_to_async(meeting_type.save)()
            logger.info("✅ Updated meeting type to include facilitator")
    
    # Check if user has a scheduling profile with calendar connection
    profile = await sync_to_async(
        SchedulingProfile.objects.filter(user=user).select_related('calendar_connection').first
    )()
    
    if not profile:
        logger.error("❌ No scheduling profile found for user")
        return False
        
    if not profile.calendar_connection:
        logger.error("❌ No calendar connection found for user")
        logger.info("ℹ️ Calendar events cannot be created without UniPile calendar connection")
        return False
        
    logger.info(f"✅ Calendar connection found: {profile.calendar_connection.unipile_account_id}")
    
    # Create the processor
    processor = FacilitatorBookingProcessor(meeting_type)
    
    # Generate available slots
    logger.info("📅 Generating available slots...")
    tomorrow = datetime.now().date() + timedelta(days=1)
    available_slots = await processor.get_available_slots(
        start_date=tomorrow,
        end_date=tomorrow + timedelta(days=7)
    )
    
    if not available_slots or not available_slots[0]['slots']:
        logger.error("❌ No available slots found")
        return False
        
    first_slot = available_slots[0]['slots'][0]
    logger.info(f"✅ Using slot: {first_slot['start']}")
    
    # Create a facilitator booking
    logger.info("🚀 Creating facilitator booking...")
    booking_data = {
        'meeting_type': meeting_type,
        'facilitator': user,
        'participant_1_name': 'Test User One',
        'participant_1_email': 'test1@example.com',
        'participant_2_name': 'Test User Two',
        'participant_2_email': 'test2@example.com',
        'selected_slots': [first_slot['start']],
        'additional_info': 'Direct test for calendar event creation'
    }
    
    booking = await processor.initiate_booking(
        participant_1_name=booking_data['participant_1_name'],
        participant_1_email=booking_data['participant_1_email'],
        participant_2_name=booking_data['participant_2_name'],
        participant_2_email=booking_data['participant_2_email'],
        selected_slots=booking_data['selected_slots'],
        additional_info=booking_data['additional_info']
    )
    
    if not booking:
        logger.error("❌ Failed to create booking")
        return False
        
    logger.info(f"✅ Booking created: {booking.id}")
    logger.info(f"   Status: {booking.status}")
    
    # Simulate participant 2 confirmation
    logger.info("👤 Simulating participant 2 confirmation...")
    
    # Use the first selected slot
    selected_slot = booking.selected_slots[0] if booking.selected_slots else None
    if not selected_slot:
        logger.error("❌ No selected slot found")
        return False
        
    result = await processor.confirm_participant_2(
        booking_id=str(booking.id),
        token=booking.participant_2_token,
        selected_slot=selected_slot
    )
    
    if not result:
        logger.error("❌ Failed to confirm participant 2")
        return False
        
    logger.info(f"✅ Participant 2 confirmed")
    logger.info(f"   Booking status: {result['status']}")
    
    # Check if calendar event was created
    logger.info("📅 Checking calendar event...")
    
    # Refresh the booking
    await sync_to_async(booking.refresh_from_db)()
    
    # Check for scheduled meeting
    meeting = await sync_to_async(
        ScheduledMeeting.objects.filter(
            facilitator_booking=booking
        ).first
    )()
    
    if meeting:
        logger.info(f"✅ Scheduled meeting found: {meeting.id}")
        logger.info(f"   Start: {meeting.start_time}")
        logger.info(f"   End: {meeting.end_time}")
        logger.info(f"   Calendar Event ID: {meeting.calendar_event_id or 'NOT CREATED'}")
        logger.info(f"   Meeting URL: {meeting.meeting_url or 'No URL'}")
        
        if meeting.calendar_event_id:
            logger.info("="*60)
            logger.info("🎉 SUCCESS: Calendar event was created via UniPile!")
            logger.info("="*60)
            return True
        else:
            logger.warning("⚠️ Meeting exists but no calendar event ID")
            logger.info("This may be due to:")
            logger.info("  1. UniPile calendar not connected")
            logger.info("  2. Calendar API rate limiting")
            logger.info("  3. Async processing delay")
    else:
        logger.error("❌ No scheduled meeting found")
        
    return False


async def main():
    """Main test function"""
    # Run the test in oneotalent tenant context
    with schema_context('oneotalent'):
        success = await test_facilitator_booking_with_calendar()
        
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())