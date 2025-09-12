#!/usr/bin/env python
"""Test script to verify unified event creation system"""

import os
import sys
import django
from datetime import datetime, timedelta
import pytz
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from tenants.models import Tenant
from communications.models import Channel, ChannelType, Conversation, Message
from communications.scheduling.models import SchedulingProfile, MeetingType
from communications.scheduling.services import BookingProcessor
from asgiref.sync import async_to_sync

User = get_user_model()

def test_manual_event_creation():
    """Test creating a manual calendar event via the unified system"""
    
    print("\n=== Testing Manual Event Creation (Unified System) ===\n")
    
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
        
        # Check for scheduling profile
        profile = SchedulingProfile.objects.filter(user=user).first()
        if profile:
            print(f"✅ User has scheduling profile with calendar: {bool(profile.calendar_connection)}")
        else:
            print("⚠️  User has no scheduling profile (events will be created without calendar sync)")
        
        # Prepare event data
        now = datetime.now(pytz.UTC)
        start_time = (now + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)
        
        # Test 1: Manual event without record
        print("\n📅 Test 1: Creating manual event without record")
        try:
            processor = BookingProcessor(meeting_type=None)
            result = async_to_sync(processor.create_manual_event)(
                user=user,
                title='Test Manual Meeting',
                start_time=start_time,
                end_time=end_time,
                attendees=['test@example.com', 'another@example.com'],
                location='Conference Room A',
                location_type='in_person',
                description='Testing unified event creation system',
                add_to_calendar=False  # Don't try to sync with UniPile for test
            )
            
            if result.get('success'):
                print(f"✅ Event created successfully!")
                print(f"   - Conversation ID: {result.get('conversation_id')}")
                print(f"   - Message: {result.get('message')}")
                
                # Verify the conversation was created
                conv_id = result.get('conversation_id')
                if conv_id:
                    conv = Conversation.objects.get(id=conv_id)
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
                    
                    # Check participants
                    from communications.models import ConversationParticipant
                    conv_participants = ConversationParticipant.objects.filter(conversation=conv)
                    print(f"\n👥 Participants ({conv_participants.count()}):")
                    for cp in conv_participants:
                        print(f"   - {cp.participant.email} ({cp.role})")
            else:
                print(f"❌ Failed to create event: {result.get('error')}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating manual event: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test 2: Manual event with record (if available)
        from pipelines.models import Record
        record = Record.objects.first()
        if record:
            print(f"\n📅 Test 2: Creating manual event with record #{record.id}")
            try:
                processor = BookingProcessor(meeting_type=None)
                result = async_to_sync(processor.create_manual_event)(
                    user=user,
                    title='Customer Follow-up Meeting',
                    start_time=start_time + timedelta(hours=2),
                    end_time=end_time + timedelta(hours=2),
                    attendees=['customer@example.com'],
                    location='https://meet.google.com/abc-defg-hij',
                    location_type='google_meet',
                    description='Follow-up meeting with customer',
                    record=record,
                    add_to_calendar=False
                )
                
                if result.get('success'):
                    print(f"✅ Event with record created successfully!")
                    print(f"   - Conversation ID: {result.get('conversation_id')}")
                    conv_id = result.get('conversation_id')
                    if conv_id:
                        conv = Conversation.objects.get(id=conv_id)
                        # Check if record participant was added
                        from communications.models import ConversationParticipant, Participant
                        record_participant = Participant.objects.filter(contact_record=record).first()
                        if record_participant:
                            print(f"   - Record participant added: {record_participant.email or 'No email'}")
                else:
                    print(f"❌ Failed to create event with record: {result.get('error')}")
                    
            except Exception as e:
                print(f"❌ Error creating event with record: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("\n⚠️  No records found, skipping Test 2")
        
        return True

def test_booking_flow():
    """Test the existing booking flow still works"""
    
    print("\n=== Testing Booking Flow (Existing System) ===\n")
    
    # Get tenant
    tenant = Tenant.objects.filter(schema_name='oneotalent').first()
    if not tenant:
        tenant = Tenant.objects.exclude(schema_name='public').first()
    
    if not tenant:
        print("❌ No tenant found")
        return False
    
    print(f"✅ Using tenant: {tenant.name}")
    
    with schema_context(tenant.schema_name):
        # Get user with scheduling profile
        profile = SchedulingProfile.objects.filter(is_active=True).first()
        if not profile:
            print("❌ No active scheduling profile found")
            return False
        
        user = profile.user
        print(f"✅ Using user: {user.username} with scheduling profile")
        
        # Get or create a meeting type
        meeting_type = MeetingType.objects.filter(user=user, is_active=True).first()
        if not meeting_type:
            print("⚠️  No active meeting type, creating one...")
            meeting_type = MeetingType.objects.create(
                user=user,
                name="Test Meeting",
                duration=30,
                description="Test meeting type for booking",
                location_type='google_meet',
                is_active=True
            )
            print(f"✅ Created meeting type: {meeting_type.name}")
        else:
            print(f"✅ Using existing meeting type: {meeting_type.name}")
        
        # Simulate a booking
        now = datetime.now(pytz.UTC)
        slot_time = (now + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
        
        print(f"\n📅 Simulating booking for {slot_time}")
        
        try:
            processor = BookingProcessor(meeting_type=meeting_type)
            
            # Process a booking with correct parameters
            booking_data = {
                'name': 'Test Customer',
                'email': 'customer@example.com',
                'notes': 'Testing the booking system',
                'additional_guests': ['colleague@example.com']
            }
            
            selected_slot = {
                'datetime': slot_time.isoformat(),
                'duration': meeting_type.duration_minutes
            }
            
            meeting = async_to_sync(processor.process_booking)(
                booking_data=booking_data,
                selected_slot=selected_slot
            )
            
            print(f"✅ Booking processed successfully!")
            print(f"   - Meeting ID: {meeting.id}")
            print(f"   - Conversation ID: {meeting.conversation_id if hasattr(meeting, 'conversation_id') else 'N/A'}")
            print(f"   - Status: Booking confirmed")
            print(f"\n📋 Scheduled Meeting Details:")
            print(f"   - Title: {meeting.title}")
            print(f"   - Start: {meeting.start_time}")
            print(f"   - End: {meeting.end_time}")
            print(f"   - Status: {meeting.status}")
            print(f"   - Booker: {meeting.booker_email}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error processing booking: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    # Test both flows
    manual_success = test_manual_event_creation()
    booking_success = test_booking_flow()
    
    print("\n" + "="*50)
    print("UNIFIED EVENT SYSTEM TEST RESULTS:")
    print("="*50)
    print(f"Manual Event Creation: {'✅ PASSED' if manual_success else '❌ FAILED'}")
    print(f"Booking Flow:          {'✅ PASSED' if booking_success else '❌ FAILED'}")
    print("="*50)
    
    if manual_success and booking_success:
        print("\n🎉 All tests passed! The unified event system is working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Please review the output above.")
        sys.exit(1)