#!/usr/bin/env python
"""
Test UniPile calendar API to see actual response format
"""
import os
import sys
import django
import asyncio
from datetime import datetime, timedelta

# Add the backend directory to the Python path
sys.path.insert(0, '/Users/joshcowan/Oneo CRM/backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from django.conf import settings
from communications.unipile.core.client import UnipileClient
from communications.unipile.clients.calendar import UnipileCalendarClient
from communications.models import UserChannelConnection
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async

User = get_user_model()

async def test_calendar_event_creation():
    """Test creating a calendar event with conference"""
    
    # Use a specific tenant context
    with schema_context('oneotalent'):  # or your tenant schema name
        # First check if we have any scheduling profiles with calendar connections
        from communications.scheduling.models import SchedulingProfile
        
        profiles = await sync_to_async(
            SchedulingProfile.objects.filter(
                calendar_connection__isnull=False
            ).select_related('calendar_connection', 'user').first
        )()
        
        if not profiles:
            print("No scheduling profiles with calendar connections found")
            # Try to find any UserChannelConnection
            connections = await sync_to_async(
                UserChannelConnection.objects.filter(
                    channel_type__in=['calendar', 'gmail', 'outlook'],
                    is_active=True,
                    unipile_account_id__isnull=False
                ).first
            )()
        else:
            print(f"Found scheduling profile for user: {profiles.user.email}")
            connections = profiles.calendar_connection
        
        if not connections:
            print("No calendar connections found")
            return
        
        print(f"Found connection: {connections.channel_type} for user {connections.user.email}")
        print(f"UniPile Account ID: {connections.unipile_account_id}")
        
        # Initialize UniPile client
        if hasattr(settings, 'UNIPILE_DSN') and hasattr(settings, 'UNIPILE_API_KEY'):
            client = UnipileClient(settings.UNIPILE_DSN, settings.UNIPILE_API_KEY)
        else:
            print("UniPile not configured in settings")
            return
        
        calendar_client = UnipileCalendarClient(client)
        
        # First, get calendars
        print("\n1. Getting calendars...")
        calendars_response = await calendar_client.get_calendars(connections.unipile_account_id)
        print(f"Calendars response: {calendars_response}")
        
        if not calendars_response or 'data' not in calendars_response:
            print("Failed to get calendars")
            return
        
        # Find primary calendar
        primary_calendar = None
        for cal in calendars_response['data']:
            if cal.get('is_primary') or cal.get('is_default'):
                primary_calendar = cal['id']
                print(f"Found primary calendar: {primary_calendar}")
                break
        
        if not primary_calendar and calendars_response['data']:
            primary_calendar = calendars_response['data'][0]['id']
            print(f"Using first calendar: {primary_calendar}")
        
        if not primary_calendar:
            print("No calendar found")
            return
        
        # Create a test event with Google Meet
        print("\n2. Creating event with Google Meet conference...")
        
        start_time = datetime.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=1)
        
        event_response = await calendar_client.create_event(
            account_id=connections.unipile_account_id,
            calendar_id=primary_calendar,
            title="Test Meeting with Conference",
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            description="This is a test meeting to check UniPile response format",
            location="",
            attendees=["test@example.com"],
            conference_provider="google_meet"  # This should auto-create conference
        )
        
        print(f"\n3. Event creation response:")
        print(f"Response type: {type(event_response)}")
        print(f"Full response: {event_response}")
        
        # Check different possible ID locations
        if event_response:
            print("\n4. Checking response structure:")
            if isinstance(event_response, dict):
                print(f"  - Has 'id': {'id' in event_response}")
                print(f"  - Has 'event_id': {'event_id' in event_response}")
                print(f"  - Has 'data': {'data' in event_response}")
                print(f"  - Has 'conference': {'conference' in event_response}")
                
                if 'data' in event_response:
                    print(f"  - data.id: {event_response['data'].get('id') if isinstance(event_response['data'], dict) else 'N/A'}")
                    print(f"  - data.conference: {event_response['data'].get('conference') if isinstance(event_response['data'], dict) else 'N/A'}")
                
                # Try to extract event ID
                event_id = event_response.get('id') or event_response.get('event_id')
                if not event_id and 'data' in event_response and isinstance(event_response['data'], dict):
                    event_id = event_response['data'].get('id')
                
                if event_id:
                    print(f"\n5. Event ID found: {event_id}")
                    
                    # Now fetch the event to see if conference URL is there
                    print("\n6. Fetching event to check for conference URL...")
                    
                    events_response = await calendar_client.get_events(
                        account_id=connections.unipile_account_id,
                        calendar_id=primary_calendar,
                        start_date=(start_time - timedelta(minutes=1)).isoformat(),
                        end_date=(end_time + timedelta(minutes=1)).isoformat(),
                        limit=10
                    )
                    
                    print(f"Events fetch response: {events_response}")
                    
                    if events_response and 'data' in events_response:
                        for event in events_response['data']:
                            if event.get('id') == event_id:
                                print(f"\n7. Found our event:")
                                print(f"  - Event: {event}")
                                if 'conference' in event:
                                    print(f"  - Conference data: {event['conference']}")
                                break

# Run the async function
if __name__ == "__main__":
    asyncio.run(test_calendar_event_creation())