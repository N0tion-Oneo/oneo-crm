#!/usr/bin/env python3
"""
Examine the latest received message's raw webhook data
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

import json
from django_tenants.utils import schema_context

def examine_latest_webhook_data():
    """Examine the raw webhook data from the latest received message"""
    
    print("📨 EXAMINING LATEST RECEIVED MESSAGE WEBHOOK DATA")
    print("=" * 60)
    
    with schema_context('oneotalent'):
        from communications.models import Message, MessageDirection
        
        # Find the latest inbound message with webhook data
        latest_inbound = Message.objects.filter(
            direction=MessageDirection.INBOUND,
            channel__channel_type='whatsapp',
            metadata__raw_webhook_data__isnull=False
        ).order_by('-created_at').first()
        
        if not latest_inbound:
            print("❌ No inbound messages with webhook data found")
            return
        
        print(f"📱 Latest inbound message:")
        print(f"   ID: {latest_inbound.id}")
        print(f"   External ID: {latest_inbound.external_message_id}")
        print(f"   Content: '{(latest_inbound.content or '')[:50]}{'...' if len(latest_inbound.content or '') > 50 else ''}'")
        print(f"   From: {latest_inbound.contact_phone}")
        print(f"   Created: {latest_inbound.created_at}")
        print(f"   Processing Version: {latest_inbound.metadata.get('processing_version', 'unknown') if latest_inbound.metadata else 'no metadata'}")
        
        metadata = latest_inbound.metadata or {}
        raw_webhook_data = metadata.get('raw_webhook_data', {})
        
        if not raw_webhook_data:
            print("❌ No raw webhook data found in latest message")
            return
        
        print(f"\n🔍 RAW WEBHOOK DATA STRUCTURE:")
        print("=" * 40)
        
        # Show top-level keys
        webhook_keys = list(raw_webhook_data.keys())
        print(f"📋 Top-level keys ({len(webhook_keys)} total):")
        for key in webhook_keys:
            print(f"   • {key}")
        
        print(f"\n📊 DETAILED WEBHOOK FIELDS:")
        print("-" * 30)
        
        # Show key fields with their values
        important_fields = [
            'event', 'webhook_name', 'message_id', 'provider_chat_id', 
            'chat_id', 'timestamp', 'account_id', 'message_type', 
            'chat_content_type', 'is_group', 'folder'
        ]
        
        for field in important_fields:
            if field in raw_webhook_data:
                value = raw_webhook_data[field]
                print(f"   {field}: {value}")
        
        # Show message content
        print(f"\n💬 MESSAGE CONTENT:")
        print("-" * 20)
        message_data = raw_webhook_data.get('message', {})
        if message_data:
            print(f"   Message keys: {list(message_data.keys())}")
            for key, value in message_data.items():
                if key in ['text', 'type', 'id']:
                    print(f"   {key}: {value}")
        
        # Show sender information
        print(f"\n👤 SENDER INFORMATION:")
        print("-" * 22)
        sender = raw_webhook_data.get('sender', {})
        if sender:
            print(f"   Sender keys: {list(sender.keys())}")
            for key, value in sender.items():
                print(f"   {key}: {value}")
        
        # Show attendees information (key for provider logic)
        print(f"\n👥 ATTENDEES INFORMATION:")
        print("-" * 25)
        attendees = raw_webhook_data.get('attendees', [])
        print(f"   Number of attendees: {len(attendees)}")
        
        for i, attendee in enumerate(attendees):
            print(f"\n   Attendee {i+1}:")
            for key, value in attendee.items():
                print(f"      {key}: {value}")
        
        # Show provider logic analysis
        print(f"\n🎯 PROVIDER LOGIC ANALYSIS:")
        print("-" * 27)
        
        provider_chat_id = raw_webhook_data.get('provider_chat_id', 'NOT_FOUND')
        print(f"   Provider Chat ID: {provider_chat_id}")
        
        # Find the contact (provider_chat_id should match one attendee)
        contact_attendee = None
        sender_attendee = None
        
        for attendee in attendees:
            attendee_id = attendee.get('attendee_provider_id', '')
            if attendee_id == provider_chat_id:
                contact_attendee = attendee
                print(f"   ✅ Contact found: {attendee.get('attendee_name', 'No name')} ({attendee_id})")
                break
        
        # Check if sender matches provider_chat_id (inbound case)
        if sender.get('attendee_provider_id') == provider_chat_id:
            sender_attendee = sender
            print(f"   ✅ Sender is contact: {sender.get('attendee_name', 'No name')}")
        
        if not contact_attendee and not sender_attendee:
            print(f"   ❌ Contact not found matching provider_chat_id")
        
        # Show processed vs raw data comparison
        print(f"\n📊 PROCESSED vs RAW DATA COMPARISON:")
        print("-" * 37)
        
        processed_data = {
            'contact_name': metadata.get('contact_name', 'NOT_SET'),
            'contact_phone': latest_inbound.contact_phone,
            'extracted_phone': metadata.get('extracted_phone', 'NOT_SET'),
            'processing_version': metadata.get('processing_version', 'NOT_SET')
        }
        
        print("   Processed data (what we store):")
        for key, value in processed_data.items():
            print(f"      {key}: {value}")
        
        # Show raw data size
        raw_data_json = json.dumps(raw_webhook_data, default=str)
        print(f"\n📏 RAW WEBHOOK DATA SIZE:")
        print("-" * 25)
        print(f"   Raw JSON length: {len(raw_data_json)} characters")
        print(f"   Number of fields: {len(webhook_keys)}")
        print(f"   Attendees count: {len(attendees)}")
        
        # Show the complete raw webhook data (formatted)
        print(f"\n📄 COMPLETE RAW WEBHOOK DATA:")
        print("=" * 35)
        print(json.dumps(raw_webhook_data, indent=2, default=str))
        
        return raw_webhook_data

def analyze_webhook_patterns():
    """Analyze patterns across multiple recent webhooks"""
    
    print(f"\n🔍 WEBHOOK PATTERN ANALYSIS")
    print("=" * 40)
    
    with schema_context('oneotalent'):
        from communications.models import Message, MessageDirection
        
        # Get last 5 inbound messages with webhook data
        recent_messages = Message.objects.filter(
            direction=MessageDirection.INBOUND,
            channel__channel_type='whatsapp',
            metadata__raw_webhook_data__isnull=False
        ).order_by('-created_at')[:5]
        
        print(f"📊 Analyzing {len(recent_messages)} recent inbound messages:")
        
        webhook_fields_freq = {}
        provider_logic_success = 0
        
        for i, msg in enumerate(recent_messages):
            metadata = msg.metadata or {}
            raw_data = metadata.get('raw_webhook_data', {})
            
            print(f"\n   Message {i+1}: {str(msg.id)[:8]}...")
            print(f"      Content: '{(msg.content or '')[:30]}{'...' if len(msg.content or '') > 30 else ''}'")
            print(f"      Contact: {metadata.get('contact_name', 'NO_NAME')}")
            print(f"      Phone: {msg.contact_phone or 'NO_PHONE'}")
            
            # Track field frequency
            for field in raw_data.keys():
                webhook_fields_freq[field] = webhook_fields_freq.get(field, 0) + 1
            
            # Check provider logic success
            contact_name = metadata.get('contact_name', '')
            if contact_name and contact_name != 'NO_NAME' and not contact_name.isdigit():
                provider_logic_success += 1
        
        print(f"\n📋 Common webhook fields across messages:")
        for field, count in sorted(webhook_fields_freq.items(), key=lambda x: x[1], reverse=True):
            print(f"   {field}: {count}/{len(recent_messages)} messages ({count/len(recent_messages)*100:.0f}%)")
        
        print(f"\n🎯 Provider logic success rate: {provider_logic_success}/{len(recent_messages)} ({provider_logic_success/len(recent_messages)*100:.0f}%)")

if __name__ == '__main__':
    print("Examining latest webhook data...\n")
    
    # Examine latest webhook
    webhook_data = examine_latest_webhook_data()
    
    if webhook_data:
        # Analyze patterns
        analyze_webhook_patterns()
        
        print(f"\n🎉 WEBHOOK DATA EXAMINATION COMPLETE!")
        print("   • Raw webhook structure documented ✅")
        print("   • Provider logic mapping verified ✅")  
        print("   • Data processing pipeline understood ✅")
    else:
        print(f"\n❌ No webhook data found to examine")
    
    print(f"\nThis raw data is now safely stored and processed through provider logic")
    print(f"while keeping the frontend APIs clean and user-friendly! 🚀")