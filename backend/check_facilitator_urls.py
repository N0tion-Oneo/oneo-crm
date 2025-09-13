#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.scheduling.models import ScheduledMeeting, FacilitatorBooking

# Use the oneotalent schema
with schema_context('oneotalent'):
    # Check facilitator meetings - those that have a facilitator_booking
    facilitator_meetings = ScheduledMeeting.objects.filter(
        facilitator_booking__isnull=False
    ).select_related('facilitator_booking', 'facilitator_booking__scheduled_meeting')
    
    print(f"Total facilitator meetings: {facilitator_meetings.count()}")
    
    for meeting in facilitator_meetings[:3]:
        print(f"\nMeeting ID: {meeting.id}")
        print(f"  has facilitator_booking: {bool(meeting.facilitator_booking)}")
        print(f"  meeting.meeting_url: '{meeting.meeting_url}'")
        
        if meeting.facilitator_booking:
            fb = meeting.facilitator_booking
            print(f"  facilitator_booking exists: Yes")
            print(f"  facilitator_booking.id: {fb.id}")
            print(f"  facilitator_booking.status: {fb.status}")
            
            if fb.scheduled_meeting:
                print(f"  facilitator_booking.scheduled_meeting exists: Yes")
                print(f"  facilitator_booking.scheduled_meeting.id: {fb.scheduled_meeting.id}")
                print(f"  facilitator_booking.scheduled_meeting.meeting_url: '{fb.scheduled_meeting.meeting_url}'")
            else:
                print(f"  facilitator_booking.scheduled_meeting: None")
        else:
            print(f"  facilitator_booking: None")
    
    print("\n" + "="*50)
    print("Checking FacilitatorBooking objects directly:")
    bookings = FacilitatorBooking.objects.select_related('scheduled_meeting').all()[:3]
    
    for booking in bookings:
        print(f"\nFacilitatorBooking ID: {booking.id}")
        print(f"  status: {booking.status}")
        if booking.scheduled_meeting:
            print(f"  scheduled_meeting.id: {booking.scheduled_meeting.id}")
            print(f"  scheduled_meeting.meeting_url: '{booking.scheduled_meeting.meeting_url}'")
        else:
            print(f"  scheduled_meeting: None")