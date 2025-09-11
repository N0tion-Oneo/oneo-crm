#!/usr/bin/env python
"""
Test the full scheduling process including UniPile event creation
"""
import os
import sys
import django
import json
from datetime import datetime, timedelta

# Add the backend directory to the Python path
sys.path.insert(0, '/Users/joshcowan/Oneo CRM/backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from django.conf import settings
from django.contrib.auth import get_user_model
from communications.scheduling.models import (
    SchedulingProfile, MeetingType, ScheduledMeeting
)
from communications.scheduling.services import BookingProcessor
from pipelines.models import Pipeline

User = get_user_model()

def test_full_scheduling():
    """Test the complete scheduling flow"""
    
    # Use the oneotalent tenant
    with schema_context('oneotalent'):
        print("=" * 60)
        print("TESTING FULL SCHEDULING PROCESS")
        print("=" * 60)
        
        # 1. Check for existing user with scheduling setup
        print("\n1. Checking for users with scheduling profiles...")
        profiles = SchedulingProfile.objects.select_related('user', 'calendar_connection').all()
        
        if not profiles.exists():
            print("   ❌ No scheduling profiles found")
            print("   Creating a test profile...")
            
            # Get or create a test user
            user = User.objects.filter(email='admin@oneo.com').first()
            if not user:
                user = User.objects.first()
            
            if not user:
                print("   ❌ No users found in tenant")
                return
            
            print(f"   Using user: {user.email}")
            
            # Create a basic scheduling profile
            profile = SchedulingProfile.objects.create(
                user=user,
                timezone='America/New_York',
                buffer_minutes=15,
                min_notice_hours=1,
                max_advance_days=60,
                working_hours={
                    "monday": [{"start": "09:00", "end": "17:00"}],
                    "tuesday": [{"start": "09:00", "end": "17:00"}],
                    "wednesday": [{"start": "09:00", "end": "17:00"}],
                    "thursday": [{"start": "09:00", "end": "17:00"}],
                    "friday": [{"start": "09:00", "end": "17:00"}],
                    "saturday": [],
                    "sunday": []
                }
            )
            print(f"   ✅ Created scheduling profile for {user.email}")
        else:
            profile = profiles.first()
            user = profile.user
            print(f"   ✅ Found profile for user: {user.email}")
            if profile.calendar_connection:
                print(f"      Calendar connected: {profile.calendar_connection.channel_type}")
                print(f"      UniPile Account ID: {profile.calendar_connection.unipile_account_id}")
            else:
                print("      ⚠️  No calendar connection")
        
        # 2. Check for meeting types
        print("\n2. Checking for meeting types...")
        meeting_types = MeetingType.objects.filter(user=user, is_active=True)
        
        if not meeting_types.exists():
            print("   ❌ No meeting types found")
            print("   Creating a test meeting type...")
            
            # Get a pipeline for the meeting type
            pipeline = Pipeline.objects.first()
            
            meeting_type = MeetingType.objects.create(
                user=user,
                name="Test Meeting with Google Meet",
                slug="test-meeting",
                description="Test meeting for UniPile integration",
                duration_minutes=30,
                location_type='google_meet',  # This should trigger conference creation
                pipeline=pipeline if pipeline else None,
                is_active=True
            )
            print(f"   ✅ Created meeting type: {meeting_type.name}")
        else:
            meeting_type = meeting_types.first()
            print(f"   ✅ Found meeting type: {meeting_type.name}")
            print(f"      Duration: {meeting_type.duration_minutes} minutes")
            print(f"      Location type: {meeting_type.location_type}")
            print(f"      Calendar ID: {meeting_type.calendar_id or 'Not set'}")
        
        # 3. Simulate a booking
        print("\n3. Simulating a booking...")
        
        # Prepare booking data with timezone awareness
        from django.utils import timezone as django_tz
        tomorrow = django_tz.now() + timedelta(days=1)
        start_time = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(minutes=meeting_type.duration_minutes)
        
        # Generate unique phone number for each test
        import random
        phone_suffix = random.randint(1000, 9999)
        
        booking_data = {
            'email': f'test.participant{phone_suffix}@example.com',
            'name': f'Test Participant {phone_suffix}',
            'phone': f'+1555{phone_suffix:04d}',
            'timezone': 'America/New_York',
            'notes': 'This is a test booking to check UniPile integration',
            'ip_address': '127.0.0.1',
            'user_agent': 'Test Script'
        }
        
        selected_slot = {
            'start': start_time.isoformat(),
            'end': end_time.isoformat()
        }
        
        print(f"   Booking details:")
        print(f"      Participant: {booking_data['name']} ({booking_data['email']})")
        print(f"      Time: {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%H:%M')}")
        print(f"      Meeting type: {meeting_type.name}")
        
        # Check for existing meetings at this time
        existing = ScheduledMeeting.objects.filter(
            meeting_type=meeting_type,
            start_time=start_time,
            status__in=['scheduled', 'confirmed']
        ).exists()
        
        if existing:
            print("   ⚠️  Meeting already exists at this time")
            # Find another slot
            start_time = start_time + timedelta(hours=1)
            end_time = start_time + timedelta(minutes=meeting_type.duration_minutes)
            selected_slot = {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            }
            print(f"      Using new time: {start_time.strftime('%H:%M')}")
        
        # Process the booking
        try:
            processor = BookingProcessor(meeting_type=meeting_type)
            meeting = processor.process_booking_sync(booking_data, selected_slot)
            
            print(f"\n   ✅ Meeting booked successfully!")
            print(f"      Meeting ID: {meeting.id}")
            print(f"      Status: {meeting.status}")
            print(f"      Meeting URL: {meeting.meeting_url or 'Not set yet'}")
            print(f"      Calendar sync status: {meeting.calendar_sync_status}")
            
            # 4. Check if calendar invite task was queued
            print("\n4. Calendar invite task:")
            if profile.calendar_connection:
                print("   📅 Calendar invite should be processing via Celery")
                print("   Check Celery logs for task execution")
                
                # Check booking_data for stored info
                if 'calendar_event_id' in meeting.booking_data:
                    print(f"   Calendar Event ID: {meeting.booking_data['calendar_event_id']}")
                if 'conference_url' in meeting.booking_data:
                    print(f"   Conference URL: {meeting.booking_data['conference_url']}")
            else:
                print("   ⚠️  No calendar connection - invite won't be sent")
            
            # 5. List recent scheduled meetings
            print("\n5. Recent scheduled meetings:")
            recent_meetings = ScheduledMeeting.objects.filter(
                host=user
            ).order_by('-created_at')[:5]
            
            for m in recent_meetings:
                print(f"   - {m.meeting_type.name}")
                print(f"     {m.start_time.strftime('%Y-%m-%d %H:%M')} ({m.status})")
                print(f"     Participant: {m.participant.email}")
                print(f"     Meeting URL: {m.meeting_url or 'None'}")
                if m.booking_data:
                    if 'calendar_event_id' in m.booking_data:
                        print(f"     Calendar Event: {m.booking_data.get('calendar_event_id')}")
                print()
            
        except Exception as e:
            print(f"\n   ❌ Booking failed: {e}")
            import traceback
            traceback.print_exc()
        
        print("=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)
        
        # Summary
        print("\n📊 SUMMARY:")
        print(f"   Profile: {'✅' if profile else '❌'}")
        print(f"   Calendar: {'✅' if profile.calendar_connection else '❌ Not connected'}")
        print(f"   Meeting Type: {'✅' if meeting_type else '❌'}")
        print(f"   Booking: {'✅' if 'meeting' in locals() else '❌'}")
        
        if not profile.calendar_connection:
            print("\n⚠️  NEXT STEPS:")
            print("   1. Connect a calendar via UniPile")
            print("   2. Update the SchedulingProfile with calendar_connection")
            print("   3. Run this test again to see calendar event creation")

if __name__ == "__main__":
    test_full_scheduling()