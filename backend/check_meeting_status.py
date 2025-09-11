#!/usr/bin/env python
"""
Check the status of the recently created meeting
"""
import os
import sys
import django
import time
from datetime import datetime, timedelta

# Add the backend directory to the Python path
sys.path.insert(0, '/Users/joshcowan/Oneo CRM/backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.scheduling.models import ScheduledMeeting

def check_meeting_status():
    """Check recent meetings for calendar sync status"""
    
    with schema_context('oneotalent'):
        print("=" * 60)
        print("CHECKING MEETING STATUS AND CALENDAR SYNC")
        print("=" * 60)
        
        # Get the most recent meetings
        recent_meetings = ScheduledMeeting.objects.order_by('-created_at')[:5]
        
        print(f"\nFound {recent_meetings.count()} recent meetings:\n")
        
        for meeting in recent_meetings:
            print(f"Meeting ID: {meeting.id}")
            print(f"  Created: {meeting.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Participant: {meeting.participant.email}")
            print(f"  Start: {meeting.start_time.strftime('%Y-%m-%d %H:%M')}")
            print(f"  Status: {meeting.status}")
            print(f"  Calendar sync: {meeting.calendar_sync_status}")
            print(f"  Meeting URL: {meeting.meeting_url or 'Not set'}")
            
            if meeting.booking_data:
                if 'calendar_event_id' in meeting.booking_data:
                    print(f"  ✅ Calendar Event ID: {meeting.booking_data['calendar_event_id']}")
                if 'conference_url' in meeting.booking_data:
                    print(f"  🔗 Conference URL in booking: {meeting.booking_data['conference_url']}")
                if 'unipile_response' in meeting.booking_data:
                    print(f"  📡 UniPile Response stored: Yes")
            
            print("-" * 40)
        
        # Check for the test meeting we just created
        print("\nChecking for test participants...")
        test_meetings = ScheduledMeeting.objects.filter(
            participant__email__startswith='test.participant'
        ).order_by('-created_at')[:3]
        
        if test_meetings:
            print(f"\nFound {test_meetings.count()} test meeting(s):")
            for meeting in test_meetings:
                print(f"\n📅 Test Meeting: {meeting.participant.email}")
                print(f"   Status: {meeting.status}")
                print(f"   Calendar sync: {meeting.calendar_sync_status}")
                print(f"   Meeting URL: {meeting.meeting_url or '❌ Not set'}")
                
                # Wait a bit and check again if still pending
                if meeting.calendar_sync_status == 'pending' and not meeting.meeting_url:
                    print("   ⏳ Waiting 5 seconds for Celery to process...")
                    time.sleep(5)
                    
                    # Refresh from database
                    meeting.refresh_from_db()
                    print(f"   After refresh:")
                    print(f"     Calendar sync: {meeting.calendar_sync_status}")
                    print(f"     Meeting URL: {meeting.meeting_url or '❌ Still not set'}")
                    
                    if meeting.booking_data and 'calendar_event_id' in meeting.booking_data:
                        print(f"     ✅ Calendar Event ID: {meeting.booking_data['calendar_event_id']}")

if __name__ == "__main__":
    check_meeting_status()