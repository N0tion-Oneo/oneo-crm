#!/usr/bin/env python
"""
Simple test for facilitator booking calendar event creation.
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
from communications.scheduling.models import MeetingType, FacilitatorBooking, ScheduledMeeting
from communications.scheduling.services import FacilitatorBookingProcessor
from asgiref.sync import async_to_sync

User = get_user_model()


def test_facilitator_booking():
    """Test facilitator booking synchronously with proper schema context"""
    
    with schema_context('oneotalent'):
        logger.info("="*60)
        logger.info("🧪 TESTING FACILITATOR BOOKING CALENDAR EVENTS")
        logger.info("="*60)
        
        # Get user
        user = User.objects.filter(email='josh@oneodigital.com').first()
        if not user:
            logger.error("❌ User not found")
            return
        logger.info(f"✅ User: {user.email}")
        
        # Get or create meeting type
        meeting_type = MeetingType.objects.filter(
            user=user,
            meeting_mode='facilitator'
        ).first()
        
        if not meeting_type:
            meeting_type = MeetingType.objects.create(
                user=user,
                name='Test Facilitator Meeting',
                slug=f'test-facilitator-{datetime.now().timestamp()}',
                duration_minutes=30,
                meeting_mode='facilitator',
                is_active=True,
                facilitator_settings={'include_facilitator': False}
            )
            logger.info(f"✅ Created meeting type: {meeting_type.name}")
        else:
            logger.info(f"✅ Found meeting type: {meeting_type.name}")
            # Update to test without facilitator as participant
            meeting_type.facilitator_settings['include_facilitator'] = False
            meeting_type.save()
            logger.info("📝 Updated include_facilitator to False")
        
        # Log current settings
        include_facilitator = meeting_type.facilitator_settings.get('include_facilitator', True)
        logger.info(f"📋 Include Facilitator: {include_facilitator}")
        
        # Create processor
        processor = FacilitatorBookingProcessor(meeting_type)
        
        # Create slots - use random hour to avoid conflicts
        import random
        hour = random.randint(8, 18)
        tomorrow = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(days=1)
        slots = [
            {'start': tomorrow.isoformat(), 'end': (tomorrow + timedelta(minutes=30)).isoformat()},
            {'start': (tomorrow + timedelta(hours=1)).isoformat(), 'end': (tomorrow + timedelta(hours=1, minutes=30)).isoformat()}
        ]
        logger.info(f"📅 Using time slot: {tomorrow.strftime('%Y-%m-%d %H:%M')}")
        
        # Step 1: Process P1
        logger.info("\n📝 Step 1: Creating booking...")
        participant_data = {
            'email': 'p1@test.com',
            'name': 'Participant One',
            'participant_2_email': 'p2@test.com',
            'participant_2_name': 'Participant Two'
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
        logger.info(f"   Status: {booking.status}")
        
        # Step 2: Process P2
        logger.info("\n📝 Step 2: Confirming P2...")
        p2_data = {'name': 'Participant Two'}
        
        meeting = async_to_sync(processor.process_facilitator_step2)(
            booking=booking,
            participant_data=p2_data,
            selected_slot=slots[0]
        )
        
        logger.info(f"✅ Meeting created: {meeting.id}")
        logger.info(f"   Start: {meeting.start_time}")
        
        # Check calendar event
        logger.info("\n📅 Calendar Event Check:")
        logger.info(f"   Calendar Event ID: {meeting.calendar_event_id or 'NOT CREATED'}")
        logger.info(f"   Meeting URL: {meeting.meeting_url or 'None'}")
        
        # Check attendees
        attendees = meeting.booking_data.get('attendees', [])
        logger.info(f"   Attendees: {attendees}")
        logger.info(f"   Facilitator in attendees: {user.email in attendees}")
        
        # Test double-booking if facilitator is included
        if include_facilitator:
            logger.info("\n🔄 Testing double-booking prevention...")
            try:
                # Try to create another meeting at same time
                booking2 = async_to_sync(processor.process_facilitator_step1)(
                    participant_data={'email': 'p3@test.com', 'name': 'P3', 'participant_2_email': 'p4@test.com', 'participant_2_name': 'P4'},
                    meeting_params=meeting_params,
                    selected_slots=[slots[0]]  # Same slot
                )
                
                # Try to confirm P2 with same slot
                meeting2 = async_to_sync(processor.process_facilitator_step2)(
                    booking=booking2,
                    participant_data={'name': 'P4'},
                    selected_slot=slots[0]
                )
                logger.warning("⚠️ Double-booking was allowed (shouldn't happen with include_facilitator=True)")
            except ValueError as e:
                if "no longer available" in str(e):
                    logger.info("✅ Double-booking prevented correctly")
                else:
                    logger.error(f"❌ Unexpected error: {e}")
        else:
            logger.info("\n✅ Facilitator not included - can coordinate multiple meetings simultaneously")
        
        logger.info("\n" + "="*60)
        if meeting.calendar_event_id:
            logger.info("✅✅✅ SUCCESS: Calendar event created!")
        else:
            logger.info("⚠️ Calendar event not created (check UniPile connection)")
        logger.info("="*60)


if __name__ == "__main__":
    test_facilitator_booking()