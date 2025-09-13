#!/usr/bin/env python
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.scheduling.models import ScheduledMeeting
from communications.scheduling.serializers import ScheduledMeetingSerializer
from communications.scheduling.views import ScheduledMeetingViewSet
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from django.contrib.auth import get_user_model

User = get_user_model()

# Use the oneotalent schema
with schema_context('oneotalent'):
    # Get a meeting with a URL
    meeting_with_url = ScheduledMeeting.objects.exclude(
        meeting_url__isnull=True
    ).exclude(
        meeting_url=''
    ).first()
    
    if meeting_with_url:
        print(f"Testing meeting ID: {meeting_with_url.id}")
        print(f"Meeting URL in DB: '{meeting_with_url.meeting_url}'")
        print(f"Meeting Type: {meeting_with_url.meeting_type.name if meeting_with_url.meeting_type else 'None'}")
        
        # Create a request context
        factory = APIRequestFactory()
        request = factory.get('/api/v1/communications/scheduling/meetings/')
        
        # Get a user for context
        user = User.objects.filter(is_active=True).first()
        if user:
            request.user = user
            
            # Serialize the meeting directly
            from rest_framework.request import Request
            request = Request(request)
            request.user = user
            
            # Serialize the meeting directly
            serializer = ScheduledMeetingSerializer(meeting_with_url, context={'request': request})
            data = serializer.data
            
            print(f"\nSerialized data:")
            print(f"  id: {data.get('id')}")
            print(f"  meeting_url: '{data.get('meeting_url')}'")
            print(f"  meeting_location: '{data.get('meeting_location')}'")
            print(f"  meeting_type: {data.get('meeting_type')}")
            print(f"  status: {data.get('status')}")
            
            # Check if meeting_url is in the serialized output
            if 'meeting_url' in data:
                if data['meeting_url']:
                    print(f"\n✅ meeting_url is correctly included in API response: '{data['meeting_url']}'")
                else:
                    print(f"\n⚠️ meeting_url is included but empty in API response")
            else:
                print(f"\n❌ meeting_url is NOT included in API response")
        else:
            print("No active user found")
    else:
        print("No meetings with URLs found in the database")