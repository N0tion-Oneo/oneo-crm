#!/usr/bin/env python3
"""
Compare API-sent message data vs webhook-received message data
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

def compare_api_vs_webhook_data():
    """Compare the data structures between API-sent and webhook-received messages"""
    
    print("📊 COMPARING API-SENT vs WEBHOOK-RECEIVED MESSAGE DATA")
    print("=" * 70)
    
    with schema_context('oneotalent'):
        from communications.models import Message, MessageDirection
        
        # Find recent outbound messages with different processing patterns
        outbound_messages = Message.objects.filter(
            direction=MessageDirection.OUTBOUND,
            channel__channel_type='whatsapp'
        ).order_by('-created_at')[:10]
        
        api_sent_messages = []
        webhook_messages = []
        
        for msg in outbound_messages:
            metadata = msg.metadata or {}
            if metadata.get('sent_via_api', False):
                api_sent_messages.append(msg)
            elif metadata.get('raw_webhook_data'):
                webhook_messages.append(msg)
        
        print(f"🔍 Found {len(api_sent_messages)} API-sent messages")
        print(f"📨 Found {len(webhook_messages)} webhook-received messages")
        print()
        
        # Compare API-sent message structure
        if api_sent_messages:
            print("📤 API-SENT MESSAGE STRUCTURE:")
            api_msg = api_sent_messages[0]
            api_metadata = api_msg.metadata or {}
            
            print(f"   Message ID: {str(api_msg.id)[:8]}...")
            print(f"   External ID: {api_msg.external_message_id}")
            print(f"   Content: '{(api_msg.content or '')[:30]}{'...' if len(api_msg.content or '') > 30 else ''}'")
            print(f"   Contact Phone: {api_msg.contact_phone}")
            print(f"   Direction: {api_msg.direction}")
            print(f"   Status: {api_msg.status}")
            
            print(f"\n   📋 Metadata Keys: {list(api_metadata.keys())}")
            
            # Show important metadata fields
            important_fields = ['processing_version', 'sent_via_api', 'contact_name', 'raw_api_response', 'api_request_data']
            for field in important_fields:
                value = api_metadata.get(field, 'NOT_PRESENT')
                if field == 'raw_api_response' and isinstance(value, dict):
                    print(f"   {field}: {list(value.keys())}")
                elif field == 'api_request_data' and isinstance(value, dict):
                    print(f"   {field}: {list(value.keys())}")
                else:
                    print(f"   {field}: {value}")
            
            print()
        
        # Compare webhook-received message structure
        if webhook_messages:
            print("📨 WEBHOOK-RECEIVED MESSAGE STRUCTURE:")
            webhook_msg = webhook_messages[0]
            webhook_metadata = webhook_msg.metadata or {}
            
            print(f"   Message ID: {str(webhook_msg.id)[:8]}...")
            print(f"   External ID: {webhook_msg.external_message_id}")
            print(f"   Content: '{(webhook_msg.content or '')[:30]}{'...' if len(webhook_msg.content or '') > 30 else ''}'")
            print(f"   Contact Phone: {webhook_msg.contact_phone}")
            print(f"   Direction: {webhook_msg.direction}")
            print(f"   Status: {webhook_msg.status}")
            
            print(f"\n   📋 Metadata Keys: {list(webhook_metadata.keys())}")
            
            # Show webhook-specific fields
            webhook_fields = ['processing_version', 'contact_name', 'raw_webhook_data', 'sent_via_api']
            for field in webhook_fields:
                value = webhook_metadata.get(field, 'NOT_PRESENT')
                if field == 'raw_webhook_data' and isinstance(value, dict):
                    webhook_keys = list(value.keys())
                    print(f"   {field}: {webhook_keys}")
                    
                    # Show some important webhook data fields
                    webhook_data = value
                    important_webhook_fields = ['provider_chat_id', 'message_id', 'sender', 'attendees', 'webhook_name']
                    for wf in important_webhook_fields:
                        wf_value = webhook_data.get(wf, 'NOT_PRESENT')
                        if wf == 'sender' and isinstance(wf_value, dict):
                            print(f"      {wf}: {list(wf_value.keys())}")
                        elif wf == 'attendees' and isinstance(wf_value, list) and wf_value:
                            print(f"      {wf}: [{len(wf_value)} attendees] - First: {list(wf_value[0].keys()) if wf_value else []}")
                        else:
                            print(f"      {wf}: {wf_value}")
                else:
                    print(f"   {field}: {value}")
            
            print()
        
        # Compare data overlap
        print("🔄 DATA COMPARISON & OVERLAP:")
        
        if api_sent_messages and webhook_messages:
            api_metadata = api_sent_messages[0].metadata or {}
            webhook_metadata = webhook_messages[0].metadata or {}
            
            api_keys = set(api_metadata.keys())
            webhook_keys = set(webhook_metadata.keys())
            
            print(f"   🔑 API-only keys: {api_keys - webhook_keys}")
            print(f"   📨 Webhook-only keys: {webhook_keys - api_keys}")
            print(f"   🤝 Shared keys: {api_keys & webhook_keys}")
            
            # Check for conflicts in shared keys
            conflicts = []
            for key in api_keys & webhook_keys:
                api_val = api_metadata.get(key)
                webhook_val = webhook_metadata.get(key)
                if api_val != webhook_val:
                    conflicts.append((key, api_val, webhook_val))
            
            if conflicts:
                print(f"\n   ⚠️  CONFLICTS in shared keys:")
                for key, api_val, webhook_val in conflicts:
                    print(f"      {key}: API={api_val} vs Webhook={webhook_val}")
            else:
                print(f"   ✅ No conflicts in shared keys")
        
        print("\n🎯 MERGING STRATEGY RECOMMENDATIONS:")
        
        if not api_sent_messages:
            print("   ❌ No API-sent messages found - unable to compare structures")
        elif not webhook_messages:
            print("   ❌ No webhook messages found - unable to compare structures")
        else:
            print("   📤 API data should be preserved: sent_via_api, raw_api_response, api_request_data")
            print("   📨 Webhook data should be added: raw_webhook_data, delivery status updates")
            print("   🔄 Merge strategy: Keep API fields, add webhook fields, update status/timestamps")
            print("   ⚠️  Conflict resolution: Webhook data wins for status/timestamps, API data wins for send metadata")
        
        return {
            'api_messages': len(api_sent_messages),
            'webhook_messages': len(webhook_messages),
            'comparison_possible': len(api_sent_messages) > 0 and len(webhook_messages) > 0
        }

def show_raw_data_samples():
    """Show raw data samples for detailed inspection"""
    
    print("\n📄 RAW DATA SAMPLES:")
    print("=" * 50)
    
    with schema_context('oneotalent'):
        from communications.models import Message, MessageDirection
        
        # Get one API message and one webhook message
        api_msg = Message.objects.filter(
            direction=MessageDirection.OUTBOUND,
            channel__channel_type='whatsapp',
            metadata__sent_via_api=True
        ).first()
        
        webhook_msg = Message.objects.filter(
            direction=MessageDirection.OUTBOUND,
            channel__channel_type='whatsapp',
            metadata__raw_webhook_data__isnull=False
        ).first()
        
        if api_msg and api_msg.metadata:
            print("📤 SAMPLE API MESSAGE METADATA:")
            print(json.dumps(api_msg.metadata, indent=2, default=str)[:1000] + "..." if len(str(api_msg.metadata)) > 1000 else json.dumps(api_msg.metadata, indent=2, default=str))
            print()
        
        if webhook_msg and webhook_msg.metadata:
            print("📨 SAMPLE WEBHOOK MESSAGE METADATA:")
            webhook_data = webhook_msg.metadata.get('raw_webhook_data', {})
            if webhook_data:
                print("Raw webhook data keys:", list(webhook_data.keys()))
                # Show a few key fields
                sample_fields = ['provider_chat_id', 'message_id', 'sender', 'webhook_name', 'timestamp']
                for field in sample_fields:
                    if field in webhook_data:
                        value = webhook_data[field]
                        if isinstance(value, dict):
                            print(f"{field}: {list(value.keys())}")
                        else:
                            print(f"{field}: {value}")

if __name__ == '__main__':
    result = compare_api_vs_webhook_data()
    show_raw_data_samples()
    
    print(f"\n{'✅' if result['comparison_possible'] else '❌'} ANALYSIS COMPLETE:")
    if result['comparison_possible']:
        print("   • Data structure comparison successful ✅")
        print("   • Merging strategy identified ✅")
        print("   • Ready to implement webhook/API data preservation ✅")
    else:
        print("   • Unable to compare - missing API or webhook message samples ❌")
        print("   • Need to send/receive messages to generate comparison data ❌")