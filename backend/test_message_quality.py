#!/usr/bin/env python
"""
Check the quality of synced message data
"""
import os
import sys
import django
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.models import Channel, Conversation, ChatAttendee, Message
from django.utils import timezone

def check_message_quality():
    """Check the quality of synced messages"""
    
    with schema_context('oneotalent'):
        print("\n=== MESSAGE DATA QUALITY CHECK ===\n")
        
        # Get channel
        channel = Channel.objects.filter(
            channel_type='whatsapp',
            unipile_account_id='mp9Gis3IRtuh9V5oSxZdSA'
        ).first()
        
        if not channel:
            print("❌ No channel found")
            return
        
        # 1. Check Conversations
        print("--- CONVERSATIONS ---")
        conversations = Conversation.objects.filter(channel=channel)
        for conv in conversations:
            print(f"\n📱 Conversation: {conv.subject or 'No subject'}")
            print(f"   External ID: {conv.external_thread_id}")
            print(f"   Type: {conv.conversation_type}")
            print(f"   Last Message: {conv.last_message_at}")
            print(f"   Message Count: {conv.message_count}")
            print(f"   Unread Count: {conv.unread_count}")
            print(f"   Participant Count: {conv.participant_count}")
            
            # Check messages
            messages = Message.objects.filter(conversation=conv).order_by('-sent_at')[:10]
            
            print(f"\n   📨 Messages ({messages.count()} total):")
            for msg in messages:
                # Check direction
                direction_emoji = "➡️" if msg.direction == 'outbound' else "⬅️"
                
                # Format timestamp
                if msg.sent_at:
                    time_str = msg.sent_at.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    time_str = "No timestamp"
                
                # Get sender name
                if msg.sender:
                    sender_name = msg.sender.name
                    is_self = " (YOU)" if msg.sender.is_self else ""
                else:
                    sender_name = "Unknown"
                    is_self = ""
                
                # Content preview
                content = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
                
                print(f"      {direction_emoji} [{time_str}] {sender_name}{is_self}: {content}")
                
                # Check metadata quality
                if msg.metadata:
                    api_data = msg.metadata.get('api_data', {})
                    if api_data:
                        # Check for rich data
                        has_original = 'original' in api_data
                        has_timestamp = 'timestamp' in api_data
                        has_sender_id = 'sender_id' in api_data or 'sender_attendee_id' in api_data
                        
                        if not all([has_original, has_timestamp, has_sender_id]):
                            print(f"         ⚠️  Missing data: original={has_original}, timestamp={has_timestamp}, sender={has_sender_id}")
        
        # 2. Check Attendees
        print("\n--- ATTENDEES ---")
        attendees = ChatAttendee.objects.filter(channel=channel)
        
        for att in attendees:
            print(f"\n👤 {att.name}")
            print(f"   External ID: {att.external_attendee_id}")
            print(f"   Provider ID: {att.provider_id}")
            print(f"   Is Self: {'✅ YES (Account Owner)' if att.is_self else '❌ No'}")
            print(f"   Picture URL: {'✅ Has picture' if att.picture_url else '❌ No picture'}")
            
            # Check metadata
            if att.metadata:
                phone = att.metadata.get('phone_number', 'No phone')
                role = att.metadata.get('role', 'No role')
                status = att.metadata.get('status', 'No status')
                last_seen = att.metadata.get('last_seen', 'Never')
                
                print(f"   Phone: {phone}")
                print(f"   Role: {role}")
                print(f"   Status: {status}")
                print(f"   Last Seen: {last_seen}")
            
            # Count messages from this attendee
            msg_count = Message.objects.filter(sender=att).count()
            print(f"   Messages sent: {msg_count}")
        
        # 3. Data Quality Summary
        print("\n--- DATA QUALITY SUMMARY ---")
        
        # Messages with proper direction
        total_messages = Message.objects.filter(channel=channel).count()
        inbound = Message.objects.filter(channel=channel, direction='inbound').count()
        outbound = Message.objects.filter(channel=channel, direction='outbound').count()
        
        print(f"\n📊 Message Direction:")
        print(f"   Total: {total_messages}")
        print(f"   Inbound: {inbound} ({inbound*100//total_messages if total_messages else 0}%)")
        print(f"   Outbound: {outbound} ({outbound*100//total_messages if total_messages else 0}%)")
        
        # Messages with timestamps
        with_timestamp = Message.objects.filter(channel=channel).exclude(sent_at__isnull=True).count()
        print(f"\n⏰ Timestamps:")
        print(f"   With timestamp: {with_timestamp}/{total_messages} ({with_timestamp*100//total_messages if total_messages else 0}%)")
        
        # Messages with senders
        with_sender = Message.objects.filter(channel=channel).exclude(sender__isnull=True).count()
        print(f"\n👤 Sender Attribution:")
        print(f"   With sender: {with_sender}/{total_messages} ({with_sender*100//total_messages if total_messages else 0}%)")
        
        # Check for account owner
        account_owner = ChatAttendee.objects.filter(channel=channel, is_self=True).first()
        if account_owner:
            print(f"\n✅ Account owner identified: {account_owner.name}")
        else:
            print(f"\n⚠️  No account owner identified (all messages appear as inbound)")
        
        # Attendee name quality
        generic_names = ChatAttendee.objects.filter(
            channel=channel,
            name__startswith='WhatsApp User'
        ).count()
        
        print(f"\n📝 Name Quality:")
        print(f"   Generic names: {generic_names}/{attendees.count()} attendees")
        print(f"   Named attendees: {attendees.count() - generic_names}/{attendees.count()}")

if __name__ == "__main__":
    check_message_quality()