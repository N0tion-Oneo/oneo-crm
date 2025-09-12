#!/usr/bin/env python
"""Test script to create a calendar event and verify alignment"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import Channel, ChannelType, Conversation, Message
from rest_framework.test import APIClient
import json

User = get_user_model()

def test_create_calendar_event():
    """Test creating a calendar event via API"""
    
    print("\n=== Testing Calendar Event Creation ===\n")
    
    # Get tenant
    tenant = Tenant.objects.filter(schema_name='oneotalent').first()
    if not tenant:
        tenant = Tenant.objects.exclude(schema_name='public').first()
    
    if not tenant:
        print("❌ No tenant found")
        return False
    
    print(f"✅ Using tenant: {tenant.name}")
    
    with schema_context(tenant.schema_name):
        # Get user
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            print("❌ No superuser found")
            return False
        
        print(f"✅ Using user: {user.username}")
        
        # Prepare event data
        now = datetime.now()
        start_time = (now + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)
        
        event_data = {
            'title': 'Test Alignment Meeting',
            'event_type': 'meeting',
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'location': 'Conference Room A',
            'location_type': 'in_person',
            'description': 'Testing calendar event alignment with scheduling pattern',
            'attendees': ['test@example.com'],
            'add_to_calendar': False  # Don't try to sync with UniPile for test
        }
        
        print(f"\n📅 Creating event: {event_data['title']}")
        print(f"   Start: {start_time}")
        print(f"   End: {end_time}")
        
        # Simulate API call by directly calling the view
        from communications.calendar.views import CustomCalendarEventViewSet
        from rest_framework.request import Request
        from rest_framework.test import APIRequestFactory
        
        factory = APIRequestFactory()
        request = factory.post('/api/v1/communications/calendar/events/create_event/', 
                              data=event_data, 
                              format='json')
        request.user = user
        
        view = CustomCalendarEventViewSet()
        view.request = request
        
        try:
            response = view.create_event(request)
            
            if response.status_code == 200:
                print(f"\n✅ Event created successfully!")
                data = response.data
                
                if 'conversation_id' in data:
                    # Check the created conversation
                    conv = Conversation.objects.get(id=data['conversation_id'])
                    print(f"\n📋 Conversation Details:")
                    print(f"   - Subject: {conv.subject}")
                    print(f"   - Type: {conv.conversation_type}")
                    print(f"   - Status: {conv.status}")
                    print(f"   - External ID: {conv.external_thread_id}")
                    
                    # Check message
                    msg = Message.objects.filter(conversation=conv).first()
                    if msg:
                        print(f"\n💬 Message Details:")
                        print(f"   - Direction: {msg.direction}")
                        print(f"   - Status: {msg.status}")
                        print(f"   - Has channel: {'✅' if msg.channel else '❌'}")
                        if msg.metadata:
                            print(f"   - Message type: {msg.metadata.get('message_type', 'N/A')}")
                            print(f"   - Sender type: {msg.metadata.get('sender_type', 'N/A')}")
                    
                    # Check channel
                    if conv.channel:
                        print(f"\n📡 Channel Details:")
                        print(f"   - Name: {conv.channel.name}")
                        print(f"   - Type: {conv.channel.channel_type}")
                        print(f"   - Auth status: {conv.channel.auth_status}")
                        
                    return True
                else:
                    print(f"⚠️  Response missing conversation_id: {data}")
            else:
                print(f"❌ Failed with status {response.status_code}: {response.data}")
                
        except Exception as e:
            print(f"❌ Error creating event: {e}")
            import traceback
            traceback.print_exc()
            
    return False

if __name__ == "__main__":
    success = test_create_calendar_event()
    sys.exit(0 if success else 1)