#!/usr/bin/env python3
"""
Test outbound message storage to see what API data gets stored
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context

def test_outbound_message_storage():
    """Check recent outbound messages to see what data is stored"""
    
    print("📤 TESTING OUTBOUND MESSAGE STORAGE")
    print("=" * 60)
    
    with schema_context('oneotalent'):
        from communications.models import Message, MessageDirection
        
        # Find recent outbound messages
        outbound_messages = Message.objects.filter(
            direction=MessageDirection.OUTBOUND,
            channel__channel_type='whatsapp'
        ).order_by('-created_at')[:5]
        
        print(f"📱 Checking {len(outbound_messages)} recent outbound WhatsApp messages:")
        print()
        
        for msg in outbound_messages:
            metadata = msg.metadata or {}
            processing_version = metadata.get('processing_version', 'unknown')
            sent_via_api = metadata.get('sent_via_api', False)
            
            print(f"📨 Message {str(msg.id)[:8]}...")
            print(f"   Content: '{(msg.content or '')[:50]}{'...' if len(msg.content or '') > 50 else ''}'")
            print(f"   Contact Name: '{metadata.get('contact_name', 'No contact_name')}'")
            print(f"   Contact Phone: {msg.contact_phone}")
            print(f"   Processing Version: {processing_version}")
            print(f"   Sent via API: {sent_via_api}")
            print(f"   External Message ID: {msg.external_message_id}")
            
            # Check if we have raw API data stored
            raw_api_response = metadata.get('raw_api_response', {})
            api_request_data = metadata.get('api_request_data', {})
            
            if raw_api_response:
                print(f"   ✅ Has raw API response data: {list(raw_api_response.keys())}")
            else:
                print(f"   ❌ No raw API response data")
                
            if api_request_data:
                print(f"   ✅ Has API request data: {list(api_request_data.keys())}")
            else:
                print(f"   ❌ No API request data")
            
            # Check if we have raw_webhook_data (for comparison with inbound)
            raw_webhook_data = metadata.get('raw_webhook_data', {})
            if raw_webhook_data:
                print(f"   📨 Has webhook data: {list(raw_webhook_data.keys())}")
            else:
                print(f"   📭 No webhook data (expected for outbound)")
            
            print()
        
        # Summary
        print("📊 OUTBOUND MESSAGE STORAGE ANALYSIS:")
        
        api_stored_count = 0
        webhook_stored_count = 0
        
        for msg in outbound_messages:
            metadata = msg.metadata or {}
            if metadata.get('raw_api_response'):
                api_stored_count += 1
            if metadata.get('raw_webhook_data'):
                webhook_stored_count += 1
        
        print(f"   Total outbound messages checked: {len(outbound_messages)}")
        print(f"   Messages with API response data: {api_stored_count}")
        print(f"   Messages with webhook data: {webhook_stored_count}")
        
        print("\n🔍 STORAGE PATTERN:")
        if api_stored_count > 0:
            print("   ✅ Outbound messages are storing raw API responses")
        else:
            print("   ⚠️  Outbound messages are NOT storing raw API responses")
        
        if webhook_stored_count > 0:
            print("   📨 Some outbound messages have webhook data (unusual)")
        else:
            print("   📭 Outbound messages don't have webhook data (expected)")
        
        return {
            'total_messages': len(outbound_messages),
            'api_stored': api_stored_count,
            'webhook_stored': webhook_stored_count
        }

if __name__ == '__main__':
    result = test_outbound_message_storage()
    
    print(f"\n{'✅' if result['api_stored'] > 0 else '❌'} OUTBOUND STORAGE TEST:")
    if result['api_stored'] > 0:
        print("   • API responses are being stored ✅")
        print("   • Outbound messages have complete tracking data ✅") 
        print("   • Provider logic can access sent message details ✅")
    else:
        print("   • API responses are NOT being stored ❌")
        print("   • Limited tracking data for outbound messages ❌")
        print("   • May need to implement API response storage ❌")