#!/usr/bin/env python
"""
Test WhatsApp background sync with centralized account identifier
"""
import os
import sys
import django
import asyncio

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from authentication.models import CustomUser
from communications.models import Channel, UserChannelConnection, Message, ChatAttendee, Conversation
from communications.channels.whatsapp.sync.tasks import sync_account_comprehensive_background

def clear_existing_data(channel):
    """Clear existing data for clean test"""
    print("🧹 Clearing existing data...")
    Message.objects.filter(channel=channel).delete()
    ChatAttendee.objects.filter(channel=channel).delete()
    Conversation.objects.filter(channel=channel).delete()
    print("✅ Data cleared")

def check_results(channel):
    """Check sync results"""
    print("\n📊 Sync Results:")
    
    # Count conversations
    conversations = Conversation.objects.filter(channel=channel)
    print(f"  Conversations: {conversations.count()}")
    
    # Count attendees
    attendees = ChatAttendee.objects.filter(channel=channel)
    owner_attendees = attendees.filter(is_self=True)
    customer_attendees = attendees.filter(is_self=False)
    
    print(f"  Total Attendees: {attendees.count()}")
    print(f"    - Business Owners (is_self=True): {owner_attendees.count()}")
    print(f"    - Customers (is_self=False): {customer_attendees.count()}")
    
    # Show some attendee examples
    if owner_attendees.exists():
        owner = owner_attendees.first()
        print(f"    - Owner example: {owner.name} ({owner.provider_id})")
    
    if customer_attendees.exists():
        customer = customer_attendees.first()
        print(f"    - Customer example: {customer.name} ({customer.provider_id})")
    
    # Count messages
    messages = Message.objects.filter(channel=channel)
    outbound = messages.filter(direction='out')
    inbound = messages.filter(direction='in')
    
    print(f"  Total Messages: {messages.count()}")
    print(f"    - Outbound (from business): {outbound.count()}")
    print(f"    - Inbound (from customers): {inbound.count()}")
    
    # Show recent messages with direction
    print("\n📨 Recent Messages (last 10):")
    recent = messages.select_related('sender').order_by('-created_at')[:10]
    
    for msg in recent:
        sender_info = "Unknown"
        is_self = False
        
        if msg.sender:
            sender_info = msg.sender.name
            is_self = msg.sender.is_self
        elif msg.metadata:
            sender_info = msg.metadata.get('attendee_name', 'Unknown')
            is_self = msg.metadata.get('is_self', False)
        
        content = msg.content[:50] if msg.content else "[No content]"
        print(f"  [{msg.direction:3}] {sender_info} (is_self={is_self}): {content}...")
    
    return {
        'conversations': conversations.count(),
        'attendees': attendees.count(),
        'messages': messages.count(),
        'outbound': outbound.count(),
        'inbound': inbound.count()
    }

def main():
    """Main test function"""
    
    # Switch to oneotalent schema
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with schema_context(tenant.schema_name):
        print(f"\n🔍 Testing WhatsApp Background Sync for tenant: {tenant.name}")
        
        # Get test user
        user = CustomUser.objects.get(email='josh@oneodigital.com')
        print(f"✅ User: {user.email}")
        
        # Get WhatsApp channel that matches user's connection
        # First get the user's WhatsApp connection
        user_connection = UserChannelConnection.objects.filter(
            user=user,
            channel_type='whatsapp'
        ).first()
        
        if not user_connection:
            print("❌ No WhatsApp connection found for user")
            return
        
        # Then get the channel that matches this connection
        channel = Channel.objects.filter(
            channel_type='whatsapp',
            unipile_account_id=user_connection.unipile_account_id
        ).first()
        
        if not channel:
            print("❌ No WhatsApp channel found matching user connection")
            print(f"   Looking for account ID: {user_connection.unipile_account_id}")
            return
        print(f"✅ Channel: {channel.name} ({channel.id})")
        
        # Use the connection we already found
        connection = user_connection
        account_identifier = connection.connection_config.get('phone_number')
        print(f"✅ Connection found with account: {account_identifier}")
        
        # Clear existing data for clean test
        clear_existing_data(channel)
        
        # Trigger background sync
        print("\n🚀 Triggering background sync...")
        
        try:
            result = sync_account_comprehensive_background.delay(
                str(channel.id),
                str(user.id),
                {
                    'force_full_sync': True,
                    'sync_days': 30,
                    'conversations_per_batch': 10,
                    'messages_per_batch': 50
                }
            )
            print(f"✅ Sync task triggered: {result.id}")
            
            # Wait for sync to complete (with timeout)
            print("⏳ Waiting for sync to process (10 seconds)...")
            import time
            time.sleep(10)
            
            # Check results
            results = check_results(channel)
            
            # Verify detection is working
            print("\n🔍 Detection Verification:")
            
            if results['attendees'] > 0:
                owner_count = ChatAttendee.objects.filter(channel=channel, is_self=True).count()
                if owner_count > 0:
                    print("✅ Account owner detection working (found business attendees)")
                else:
                    print("⚠️ No business attendees detected - check account identifier")
            
            if results['messages'] > 0:
                if results['outbound'] > 0 and results['inbound'] > 0:
                    print("✅ Message direction detection working (found both directions)")
                elif results['outbound'] == 0:
                    print("⚠️ No outbound messages detected - all marked as inbound")
                elif results['inbound'] == 0:
                    print("⚠️ No inbound messages detected - all marked as outbound")
            
            print("\n✅ Background sync test complete!")
            
        except Exception as e:
            print(f"❌ Error triggering sync: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()