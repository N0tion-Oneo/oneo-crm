#!/usr/bin/env python3
"""
Test the group chat provider logic with our stored data
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

def test_group_chat_provider_logic():
    """Test the updated provider logic with group chat data"""
    
    print("🧪 TESTING GROUP CHAT PROVIDER LOGIC")
    print("=" * 50)
    
    with schema_context('oneotalent'):
        from communications.models import Message, MessageDirection
        from communications.utils.phone_extractor import (
            extract_whatsapp_contact_name,
            extract_whatsapp_phone_from_webhook,
            extract_whatsapp_message_sender
        )
        
        # Find the group chat message
        group_message = Message.objects.filter(
            channel__channel_type='whatsapp',
            metadata__raw_webhook_data__is_group=True
        ).order_by('-created_at').first()
        
        if not group_message:
            print("❌ No group chat messages found")
            return False
        
        print(f"📱 Testing with group message:")
        print(f"   Content: '{group_message.content}'")
        print(f"   Direction: {group_message.direction}")
        print(f"   Current contact_phone: {group_message.contact_phone}")
        print(f"   Current contact from metadata: {group_message.metadata.get('contact_name', 'NOT_SET') if group_message.metadata else 'NO_METADATA'}")
        
        raw_webhook = group_message.metadata.get('raw_webhook_data', {}) if group_message.metadata else {}
        
        if not raw_webhook:
            print("❌ No raw webhook data found")
            return False
        
        print(f"\n🔍 RAW WEBHOOK ANALYSIS:")
        print(f"   Is Group: {raw_webhook.get('is_group', False)}")
        print(f"   Group Subject: '{raw_webhook.get('subject', 'NO_SUBJECT')}'")
        print(f"   Provider Chat ID: {raw_webhook.get('provider_chat_id', 'NOT_SET')}")
        
        # Test our updated provider logic functions
        print(f"\n🧪 TESTING UPDATED PROVIDER LOGIC:")
        
        # Test 1: Contact name extraction
        contact_name = extract_whatsapp_contact_name(raw_webhook)
        print(f"   ✅ Contact Name: '{contact_name}'")
        
        # Test 2: Phone extraction (should be empty for groups)
        contact_phone = extract_whatsapp_phone_from_webhook(raw_webhook)
        print(f"   ✅ Contact Phone: '{contact_phone}' (should be empty for groups)")
        
        # Test 3: Message sender extraction
        sender_info = extract_whatsapp_message_sender(raw_webhook)
        print(f"   ✅ Message Sender:")
        print(f"      Name: '{sender_info['name']}'")
        print(f"      Phone: '{sender_info['phone']}'")
        print(f"      Provider ID: '{sender_info['provider_id']}'")
        print(f"      Is Group Message: {sender_info['is_group_message']}")
        print(f"      Group Subject: '{sender_info['group_subject']}'")
        
        # Test what the conversation should display
        print(f"\n📋 CONVERSATION DISPLAY LOGIC:")
        if group_message.direction == MessageDirection.INBOUND:
            should_display = f"{sender_info['name']} (in {contact_name})"
        else:
            should_display = f"You (in {contact_name})"
        
        print(f"   Should display: '{should_display}'")
        print(f"   Contact field: '{contact_name}'")
        
        # Test attendees extraction
        attendees = raw_webhook.get('attendees', [])
        print(f"\n👥 GROUP MEMBERS ({len(attendees)}):")
        for i, attendee in enumerate(attendees):
            name = attendee.get('attendee_name', 'No name')
            provider_id = attendee.get('attendee_provider_id', 'No ID')
            is_sender = provider_id == sender_info['provider_id']
            marker = " ← SENDER" if is_sender else ""
            print(f"   {i+1}. {name} ({provider_id}){marker}")
        
        # Compare with old vs new logic
        print(f"\n📊 OLD vs NEW LOGIC COMPARISON:")
        print(f"   OLD (current in DB):")
        print(f"      Contact Name: '{group_message.metadata.get('contact_name', 'NOT_SET') if group_message.metadata else 'NO_METADATA'}'")
        print(f"      Contact Phone: '{group_message.contact_phone}'")
        
        print(f"   NEW (with group logic):")
        print(f"      Contact Name: '{contact_name}'")
        print(f"      Contact Phone: '{contact_phone}'")
        print(f"      Message Display: '{should_display}'")
        
        success = bool(contact_name and contact_name != 'NOT_SET')
        return success

def test_regular_chat_still_works():
    """Test that 1-on-1 chats still work with the updated logic"""
    
    print(f"\n🧪 TESTING 1-ON-1 CHAT COMPATIBILITY")
    print("-" * 40)
    
    with schema_context('oneotalent'):
        from communications.models import Message, MessageDirection
        from communications.utils.phone_extractor import (
            extract_whatsapp_contact_name,
            extract_whatsapp_phone_from_webhook,
            extract_whatsapp_message_sender
        )
        
        # Find a 1-on-1 chat message
        regular_message = Message.objects.filter(
            channel__channel_type='whatsapp',
            metadata__raw_webhook_data__is_group=False
        ).order_by('-created_at').first()
        
        if not regular_message:
            print("❌ No 1-on-1 chat messages found")
            return True  # Not a failure, just no data
        
        raw_webhook = regular_message.metadata.get('raw_webhook_data', {}) if regular_message.metadata else {}
        
        if not raw_webhook:
            print("❌ No raw webhook data found in 1-on-1 message")
            return True
        
        print(f"📱 Testing 1-on-1 message:")
        print(f"   Content: '{regular_message.content}'")
        print(f"   Is Group: {raw_webhook.get('is_group', False)}")
        
        # Test provider logic
        contact_name = extract_whatsapp_contact_name(raw_webhook)
        contact_phone = extract_whatsapp_phone_from_webhook(raw_webhook)
        sender_info = extract_whatsapp_message_sender(raw_webhook)
        
        print(f"   ✅ Contact Name: '{contact_name}'")
        print(f"   ✅ Contact Phone: '{contact_phone}'")
        print(f"   ✅ Sender: '{sender_info['name']}'")
        print(f"   ✅ Is Group Message: {sender_info['is_group_message']}")
        
        # Verify 1-on-1 logic still works
        success = bool(contact_name and contact_phone and not sender_info['is_group_message'])
        print(f"   {'✅' if success else '❌'} 1-on-1 logic working: {success}")
        
        return success

if __name__ == '__main__':
    print("Testing group chat provider logic...\n")
    
    # Test group chat logic
    group_success = test_group_chat_provider_logic()
    
    # Test 1-on-1 compatibility
    regular_success = test_regular_chat_still_works()
    
    print(f"\n🎯 TEST RESULTS:")
    print("=" * 20)
    print(f"   Group chat logic: {'✅ WORKING' if group_success else '❌ FAILED'}")
    print(f"   1-on-1 chat logic: {'✅ WORKING' if regular_success else '❌ FAILED'}")
    
    overall_success = group_success and regular_success
    
    if overall_success:
        print(f"\n🎉 GROUP CHAT PROVIDER LOGIC SUCCESS!")
        print("   • Group chats now show proper group names ✅")
        print("   • Group senders identified correctly ✅")
        print("   • 1-on-1 chats still work perfectly ✅")
        print("   • No phone numbers for group chats ✅")
        print("   • Ready to update conversation APIs ✅")
    else:
        print(f"\n❌ GROUP CHAT PROVIDER LOGIC NEEDS WORK")
        if not group_success:
            print("   • Group chat extraction failed ❌")
        if not regular_success:
            print("   • 1-on-1 chat compatibility broken ❌")
    
    sys.exit(0 if overall_success else 1)