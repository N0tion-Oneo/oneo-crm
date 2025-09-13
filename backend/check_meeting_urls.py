#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.scheduling.models import ScheduledMeeting

# Use the oneotalent schema
with schema_context('oneotalent'):
    meetings = ScheduledMeeting.objects.all()
    total = meetings.count()
    print(f"Total meetings: {total}")
    
    if total > 0:
        with_urls = meetings.exclude(meeting_url__isnull=True).exclude(meeting_url='').count()
        print(f"Meetings with URLs: {with_urls}")
        print(f"Meetings without URLs: {total - with_urls}")
        
        print("\nFirst 5 meetings:")
        for meeting in meetings[:5]:
            print(f"  - ID: {meeting.id}")
            print(f"    Meeting Type: {meeting.meeting_type.name if meeting.meeting_type else 'None'}")
            print(f"    Meeting URL: '{meeting.meeting_url}' (empty={not meeting.meeting_url})")
            print(f"    Status: {meeting.status}")
            print(f"    Start: {meeting.start_time}")
            print()
    else:
        print("No meetings found in the database")