#!/usr/bin/env python
"""
Test script to verify UniPile calendar event creation for facilitator bookings.
Tests the complete flow from booking initiation to calendar event creation.
"""

import os
import sys
import django
import asyncio
import requests
import logging
from datetime import datetime, timedelta
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://oneotalent.localhost:8000"
TENANT_DOMAIN = "oneotalent.localhost"
USERNAME = "josh@oneodigital.com"
PASSWORD = "Admin123!"

class FacilitatorBookingTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Host': TENANT_DOMAIN,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.session_cookie = None
        
    def authenticate(self):
        """Authenticate with the API using session-based authentication"""
        logger.info("🔐 Authenticating...")
        
        # Try different authentication formats
        # First try with email field (as error suggested)
        response = self.session.post(
            f"{BASE_URL}/auth/login/",
            json={
                "email": USERNAME,
                "password": PASSWORD
            }
        )
        
        # If that fails, try username
        if response.status_code != 200:
            response = self.session.post(
                f"{BASE_URL}/auth/login/",
                json={
                    "username": "Josh_Cowan",  # Use the actual username
                    "password": PASSWORD,
                    "remember_me": True
                }
            )
        
        if response.status_code == 200:
            logger.info("✅ Authentication successful")
            # Session cookie should be set automatically
            return True
        else:
            logger.error(f"❌ Authentication failed: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
    
    def get_meeting_types(self):
        """Get available meeting types"""
        logger.info("📋 Fetching meeting types...")
        
        response = self.session.get(f"{BASE_URL}/api/v1/scheduling/meeting-types/")
        
        if response.status_code == 200:
            meeting_types = response.json()
            facilitator_types = [mt for mt in meeting_types if mt.get('meeting_mode') == 'facilitator']
            
            if facilitator_types:
                logger.info(f"✅ Found {len(facilitator_types)} facilitator meeting types")
                for mt in facilitator_types:
                    logger.info(f"   - {mt['name']} (ID: {mt['id']})")
                return facilitator_types[0]  # Return first facilitator meeting type
            else:
                logger.warning("⚠️ No facilitator meeting types found")
                return None
        else:
            logger.error(f"❌ Failed to fetch meeting types: {response.status_code}")
            return None
    
    def initiate_facilitator_booking(self, meeting_type_id):
        """Initiate a new facilitator booking"""
        logger.info("🚀 Initiating facilitator booking...")
        
        # Get available time slots first
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        slots_response = self.session.get(
            f"{BASE_URL}/api/v1/scheduling/meeting-types/{meeting_type_id}/available-slots/",
            params={
                "start_date": tomorrow.isoformat(),
                "end_date": (tomorrow + timedelta(days=7)).isoformat()
            }
        )
        
        if slots_response.status_code != 200:
            logger.error(f"❌ Failed to get available slots: {slots_response.status_code}")
            return None
            
        slots_data = slots_response.json()
        if not slots_data or not slots_data[0].get('slots'):
            logger.error("❌ No available slots found")
            return None
            
        # Use the first available slot
        first_slot = slots_data[0]['slots'][0]
        logger.info(f"📅 Using slot: {first_slot['start']}")
        
        # Create facilitator booking for participant 1
        booking_data = {
            "meeting_type_id": meeting_type_id,
            "participant_1_name": "John Test",
            "participant_1_email": "john.test@example.com",
            "participant_2_name": "Jane Test", 
            "participant_2_email": "jane.test@example.com",
            "selected_slots": [first_slot['start']],
            "additional_info": "Test facilitator booking for calendar event verification",
            "meeting_mode": "facilitator"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/v1/scheduling/facilitator-bookings/",
            json=booking_data
        )
        
        if response.status_code in [200, 201]:
            booking = response.json()
            logger.info(f"✅ Facilitator booking created: {booking['id']}")
            logger.info(f"   - Status: {booking['status']}")
            logger.info(f"   - P1 token: {booking.get('participant_1_token', 'N/A')}")
            logger.info(f"   - P2 token: {booking.get('participant_2_token', 'N/A')}")
            return booking
        else:
            logger.error(f"❌ Failed to create booking: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None
    
    def confirm_participant_2(self, booking_id, token, selected_slot):
        """Confirm participant 2's time slot selection"""
        logger.info("👤 Confirming participant 2 slot...")
        
        # Use public endpoint (no auth required)
        response = requests.post(
            f"{BASE_URL}/api/v1/scheduling/facilitator-bookings/{booking_id}/confirm-participant2/",
            json={
                "token": token,
                "selected_slot": selected_slot
            },
            headers={
                'Host': TENANT_DOMAIN,
                'Content-Type': 'application/json'
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ Participant 2 confirmed: {result['status']}")
            return result
        else:
            logger.error(f"❌ Failed to confirm participant 2: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None
    
    def check_calendar_event(self, booking_id):
        """Check if calendar event was created"""
        logger.info("📅 Checking calendar event creation...")
        
        # Get the scheduled meeting associated with this booking
        response = self.session.get(
            f"{BASE_URL}/api/v1/scheduling/meetings/",
            params={"facilitator_booking": booking_id}
        )
        
        if response.status_code == 200:
            meetings = response.json()
            if meetings and len(meetings) > 0:
                meeting = meetings[0]
                logger.info(f"✅ Scheduled meeting found: {meeting['id']}")
                logger.info(f"   - Start: {meeting['start_time']}")
                logger.info(f"   - End: {meeting['end_time']}")
                logger.info(f"   - Calendar Event ID: {meeting.get('calendar_event_id', 'NOT CREATED')}")
                logger.info(f"   - Meeting URL: {meeting.get('meeting_url', 'No URL')}")
                
                if meeting.get('calendar_event_id'):
                    logger.info("🎉 SUCCESS: Calendar event was created via UniPile!")
                    return True
                else:
                    logger.warning("⚠️ Meeting exists but no calendar event ID found")
                    return False
            else:
                logger.warning("⚠️ No scheduled meeting found for this booking")
                return False
        else:
            logger.error(f"❌ Failed to fetch meetings: {response.status_code}")
            return False
    
    def run_test(self):
        """Run the complete facilitator booking test flow"""
        logger.info("="*60)
        logger.info("🧪 FACILITATOR BOOKING CALENDAR EVENT TEST")
        logger.info("="*60)
        
        # Step 1: Authenticate
        if not self.authenticate():
            logger.error("Test aborted: Authentication failed")
            return False
        
        # Step 2: Get meeting type
        meeting_type = self.get_meeting_types()
        if not meeting_type:
            logger.error("Test aborted: No facilitator meeting types available")
            return False
        
        # Step 3: Initiate booking
        booking = self.initiate_facilitator_booking(meeting_type['id'])
        if not booking:
            logger.error("Test aborted: Failed to create booking")
            return False
        
        # Step 4: Confirm participant 2
        if 'participant_2_token' in booking and 'selected_slots' in booking:
            # Use the first selected slot
            selected_slot = booking['selected_slots'][0] if booking['selected_slots'] else None
            if selected_slot:
                confirmation = self.confirm_participant_2(
                    booking['id'],
                    booking['participant_2_token'],
                    selected_slot
                )
                
                if not confirmation:
                    logger.error("Test aborted: Failed to confirm participant 2")
                    return False
                
                # Step 5: Check calendar event
                # Wait a moment for async processing
                logger.info("⏳ Waiting for calendar event processing...")
                import time
                time.sleep(3)
                
                success = self.check_calendar_event(booking['id'])
                
                logger.info("="*60)
                if success:
                    logger.info("✅ TEST PASSED: Calendar events are being created successfully!")
                else:
                    logger.info("❌ TEST FAILED: Calendar event was not created")
                logger.info("="*60)
                
                return success
        else:
            logger.error("Test aborted: Missing participant 2 token or selected slots")
            return False


def main():
    """Main test function"""
    tester = FacilitatorBookingTester()
    success = tester.run_test()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()