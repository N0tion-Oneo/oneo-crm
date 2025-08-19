#!/usr/bin/env python3
"""
Analyze group chat provider logic issues and propose fixes
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

def analyze_group_chat_provider_logic():
    """Analyze how our current provider logic handles group chats"""
    
    print("👥 ANALYZING GROUP CHAT PROVIDER LOGIC")
    print("=" * 50)
    
    with schema_context('oneotalent'):
        from communications.models import Message, MessageDirection
        
        # Find group chat messages
        group_messages = Message.objects.filter(
            channel__channel_type='whatsapp',
            metadata__raw_webhook_data__is_group=True
        ).order_by('-created_at')[:5]
        
        print(f"📊 Found {len(group_messages)} group chat messages")
        
        if not group_messages:
            print("❌ No group chat messages found")
            return
        
        for i, msg in enumerate(group_messages):
            print(f"\n💬 GROUP MESSAGE {i+1}:")
            print("-" * 25)
            
            metadata = msg.metadata or {}
            raw_webhook = metadata.get('raw_webhook_data', {})
            
            print(f"   Content: '{msg.content}'")
            print(f"   Direction: {msg.direction}")
            print(f"   Contact Phone: {msg.contact_phone}")
            print(f"   Contact Name: {metadata.get('contact_name', 'NOT_SET')}")
            
            # Analyze group data
            is_group = raw_webhook.get('is_group', False)
            provider_chat_id = raw_webhook.get('provider_chat_id', '')
            subject = raw_webhook.get('subject', '')
            
            print(f"   Is Group: {is_group}")
            print(f"   Group Subject: '{subject}'")
            print(f"   Provider Chat ID: {provider_chat_id}")
            
            # Show current provider logic attempt
            attendees = raw_webhook.get('attendees', [])
            sender = raw_webhook.get('sender', {})
            
            print(f"   Group Members ({len(attendees)}):")
            for j, att in enumerate(attendees):
                att_name = att.get('attendee_name', 'No name')
                att_id = att.get('attendee_provider_id', 'No ID')
                is_sender = att_id == sender.get('attendee_provider_id', '')
                marker = " ← SENDER" if is_sender else ""
                print(f"      {j+1}. {att_name} ({att_id}){marker}")
            
            # Check current provider logic failure
            contact_found_via_provider_logic = False
            for att in attendees:
                if att.get('attendee_provider_id') == provider_chat_id:
                    contact_found_via_provider_logic = True
                    break
            
            print(f"\n   🎯 PROVIDER LOGIC ANALYSIS:")
            print(f"      Provider Chat ID matches attendee: {contact_found_via_provider_logic}")
            
            if not contact_found_via_provider_logic:
                print(f"      ❌ ISSUE: provider_chat_id is GROUP ID, not individual contact")
                print(f"      ❌ Current logic fails to identify contact in group")
                print(f"      ✅ SOLUTION: Use group subject + sender name for display")
            
            # Show what we should display
            sender_name = sender.get('attendee_name', 'Unknown Sender')
            group_name = subject or 'Group Chat'
            
            print(f"\n   💡 PROPOSED DISPLAY:")
            if msg.direction == MessageDirection.INBOUND:
                display_name = f"{sender_name} (in {group_name})"
            else:
                display_name = f"You (in {group_name})"
            
            print(f"      Should show: '{display_name}'")
            print(f"      Instead of: '{metadata.get('contact_name', 'NOT_SET')}'")

def design_group_chat_fix():
    """Design the fix for group chat provider logic"""
    
    print(f"\n🔧 DESIGNING GROUP CHAT FIX")
    print("=" * 35)
    
    print(f"📋 CURRENT PROVIDER LOGIC (1-on-1 chats):")
    print(f"   • provider_chat_id = contact's phone@s.whatsapp.net")
    print(f"   • Find attendee matching provider_chat_id")
    print(f"   • Use that attendee's name as contact name")
    print(f"   • Works perfectly for 1-on-1 conversations")
    
    print(f"\n❌ PROBLEM WITH GROUP CHATS:")
    print(f"   • provider_chat_id = group-id@g.us (GROUP identifier)")
    print(f"   • No attendee matches this group ID")
    print(f"   • Provider logic fails to find contact")
    print(f"   • Results in 'Unknown Contact' or empty names")
    
    print(f"\n✅ PROPOSED SOLUTION:")
    print(f"   1. Detect group chat: is_group = True")
    print(f"   2. For group chats, use DIFFERENT logic:")
    print(f"      • Contact name = Group subject ('{subject}')")  
    print(f"      • Message sender = individual sender name")
    print(f"      • Display format = 'Sender Name (in Group Name)'")
    print(f"   3. Keep existing logic for 1-on-1 chats")
    
    print(f"\n🎯 IMPLEMENTATION PLAN:")
    print(f"   📁 Files to update:")
    print(f"      • communications/utils/phone_extractor.py")
    print(f"      • communications/api/inbox_views.py")  
    print(f"      • communications/api/conversation_messages.py")
    print(f"      • communications/message_sync.py")
    
    print(f"\n💻 CODE CHANGES NEEDED:")
    print(f"   1. Add is_group detection in provider logic")
    print(f"   2. Create group-specific name extraction")
    print(f"   3. Update conversation display logic")
    print(f"   4. Update message sender logic")
    
    return {
        'files_to_update': [
            'communications/utils/phone_extractor.py',
            'communications/api/inbox_views.py',
            'communications/api/conversation_messages.py', 
            'communications/message_sync.py'
        ],
        'group_logic_needed': True
    }

def test_group_chat_scenarios():
    """Test different group chat scenarios"""
    
    print(f"\n🧪 GROUP CHAT SCENARIOS TO HANDLE:")
    print("=" * 40)
    
    scenarios = [
        {
            'name': 'Inbound Group Message',
            'description': 'Someone sends message to group',
            'display_should_be': 'Sender Name (in Group Name)',
            'contact_should_be': 'Group Name',
            'example': 'Robbie Cowan (in Family 🧓🏼👴🏻👩🏻‍🦱👨🏻‍🦱🐶🐼)'
        },
        {
            'name': 'Outbound Group Message', 
            'description': 'Business sends message to group',
            'display_should_be': 'You (in Group Name)',
            'contact_should_be': 'Group Name',
            'example': 'You (in Family 🧓🏼👴🏻👩🏻‍🦱👨🏻‍🦱🐶🐼)'
        },
        {
            'name': 'Group Without Subject',
            'description': 'Group chat with no subject set',
            'display_should_be': 'Sender Name (in Group Chat)',
            'contact_should_be': 'Group Chat',
            'example': 'John Doe (in Group Chat)'
        },
        {
            'name': 'Group Conversation List',
            'description': 'How group appears in conversation list',
            'display_should_be': 'Group Name (X members)',
            'contact_should_be': 'Group Name',
            'example': 'Family 🧓🏼👴🏻👩🏻‍🦱👨🏻‍🦱🐶🐼 (5 members)'
        }
    ]
    
    for scenario in scenarios:
        print(f"\n📋 {scenario['name']}:")
        print(f"   Description: {scenario['description']}")
        print(f"   Should display: {scenario['display_should_be']}")
        print(f"   Contact field: {scenario['contact_should_be']}")
        print(f"   Example: '{scenario['example']}'")

if __name__ == '__main__':
    print("Analyzing group chat provider logic...\n")
    
    # Analyze current issues
    analyze_group_chat_provider_logic()
    
    # Design the fix
    fix_plan = design_group_chat_fix()
    
    # Test scenarios
    test_group_chat_scenarios()
    
    print(f"\n🎯 SUMMARY:")
    print("=" * 15)
    print(f"✅ Issue identified: Provider logic fails for group chats")
    print(f"✅ Root cause: provider_chat_id is group ID, not contact ID")
    print(f"✅ Solution designed: Add is_group detection + group-specific logic")
    print(f"✅ Files identified: {len(fix_plan['files_to_update'])} files need updates")
    print(f"✅ Ready to implement: Group chat support")
    
    print(f"\n🚀 Next step: Implement group chat provider logic!")
    sys.exit(0)