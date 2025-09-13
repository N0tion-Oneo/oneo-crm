#!/usr/bin/env python
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

# Use the oneotalent schema
with schema_context('oneotalent'):
    # Get a user to authenticate with
    user = User.objects.filter(is_active=True).first()
    if user:
        # Generate JWT token
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        
        # Create API client
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # Make request to meetings endpoint
        response = client.get('/api/v1/communications/scheduling/meetings/')
        
        if response.status_code == 200:
            data = response.json()
            print(f"Total meetings: {data.get('count', 0)}")
            
            if data.get('results'):
                # Get the first meeting
                meeting = data['results'][0]
                print("\n=== First Meeting Structure ===")
                print(f"ID: {meeting.get('id')}")
                print(f"Meeting Type: {meeting.get('meeting_type')}")
                print(f"Meeting Type Name: {meeting.get('meeting_type_name')}")
                
                # Check participant_detail structure
                participant_detail = meeting.get('participant_detail')
                print(f"\n=== Participant Detail Structure ===")
                if participant_detail:
                    print(f"Type: {type(participant_detail)}")
                    print(f"Keys: {list(participant_detail.keys()) if isinstance(participant_detail, dict) else 'Not a dict'}")
                    print(f"Name: {participant_detail.get('name') if isinstance(participant_detail, dict) else 'N/A'}")
                    print(f"Email: {participant_detail.get('email') if isinstance(participant_detail, dict) else 'N/A'}")
                    print(f"Phone: {participant_detail.get('phone') if isinstance(participant_detail, dict) else 'N/A'}")
                else:
                    print("participant_detail is None")
                
                # Check facilitator_booking structure
                facilitator_booking = meeting.get('facilitator_booking')
                print(f"\n=== Facilitator Booking Structure ===")
                if facilitator_booking:
                    print(f"Type: {type(facilitator_booking)}")
                    print(f"Keys: {list(facilitator_booking.keys()) if isinstance(facilitator_booking, dict) else 'Not a dict'}")
                    if isinstance(facilitator_booking, dict):
                        facilitator = facilitator_booking.get('facilitator')
                        if facilitator:
                            print(f"Facilitator type: {type(facilitator)}")
                            print(f"Facilitator keys: {list(facilitator.keys()) if isinstance(facilitator, dict) else 'Not a dict'}")
                else:
                    print("facilitator_booking is None")
                
                # Print full JSON structure for debugging
                print(f"\n=== Full Meeting JSON (first 500 chars) ===")
                print(json.dumps(meeting, indent=2, default=str)[:500])
        else:
            print(f"API request failed with status {response.status_code}")
            print(f"Response: {response.content}")
    else:
        print("No active user found in oneotalent schema")