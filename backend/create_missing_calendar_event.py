#!/usr/bin/env python
"""
Script to create missing calendar events for completed facilitator bookings.
"""
import os
import sys
import django
import asyncio
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

# Setup tenant context
from django_tenants.utils import schema_context

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from django.contrib.auth import get_user_model
from communications.scheduling.models import (
    FacilitatorBooking, 
    ScheduledMeeting
)
from communications.scheduling.services import FacilitatorBookingProcessor

User = get_user_model()


async def create_missing_calendar_event():
    """Create calendar event for the existing completed booking"""
    
    with schema_context('oneotalent'):
        from asgiref.sync import sync_to_async
        
        # Get the specific booking
        booking = await sync_to_async(
            FacilitatorBooking.objects.get
        )(id='1b59f8e2-f6c2-4115-a96f-cd7d4bd1d181')
        
        logger.info(f"Found booking: {booking.id}")
        logger.info(f"  Status: {booking.status}")
        logger.info(f"  P1: {booking.participant_1_name} ({booking.participant_1_email})")
        logger.info(f"  P2: {booking.participant_2_name} ({booking.participant_2_email})")
        
        # Get the associated meeting
        meeting = await sync_to_async(
            ScheduledMeeting.objects.filter(facilitator_booking=booking).first
        )()
        
        if not meeting:
            logger.error("No meeting found for this booking!")
            return
            
        logger.info(f"\nFound meeting: {meeting.id}")
        logger.info(f"  Start: {meeting.start_time}")
        logger.info(f"  End: {meeting.end_time}")
        logger.info(f"  Current calendar event ID: {meeting.calendar_event_id or 'None'}")
        
        if meeting.calendar_event_id:
            logger.info("Calendar event already exists, skipping")
            return
        
        # Create the processor
        logger.info("\nCreating FacilitatorBookingProcessor...")
        processor = FacilitatorBookingProcessor(booking.meeting_type)
        
        # Call the calendar event creation method
        logger.info("Calling _create_facilitator_calendar_event...")
        try:
            await processor._create_facilitator_calendar_event(meeting, booking)
            logger.info("✅ Calendar event creation completed!")
            
            # Reload the meeting to check if it was updated
            await sync_to_async(meeting.refresh_from_db)()
            logger.info(f"\nMeeting after creation:")
            logger.info(f"  Calendar event ID: {meeting.calendar_event_id or 'Still None'}")
            logger.info(f"  Meeting URL: {meeting.meeting_url or 'No URL'}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create calendar event: {e}")
            import traceback
            logger.error(traceback.format_exc())


async def main():
    """Main function"""
    logger.info("="*60)
    logger.info("CREATING MISSING CALENDAR EVENT")
    logger.info("="*60)
    
    await create_missing_calendar_event()
    
    logger.info("\n" + "="*60)
    logger.info("COMPLETE")
    logger.info("="*60)


if __name__ == "__main__":
    asyncio.run(main())