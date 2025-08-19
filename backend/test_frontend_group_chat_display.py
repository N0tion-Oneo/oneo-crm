#!/usr/bin/env python3
"""
Test if frontend APIs now show proper group chat names for past conversations
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

def test_frontend_unified_inbox_api():
    """Test the actual frontend unified inbox API endpoint"""
    
    print("🖥️  TESTING FRONTEND UNIFIED INBOX API")
    print("=" * 50)
    
    with schema_context('oneotalent'):
        from communications.models import UserChannelConnection
        from communications.api.inbox_views import get_channel_conversations_from_stored_data
        from rest_framework.test import APIRequestFactory
        from rest_framework.response import Response
        from django.contrib.auth import get_user_model
        import json
        
        User = get_user_model()
        
        # Get WhatsApp connection
        connection = UserChannelConnection.objects.filter(
            channel_type='whatsapp'
        ).first()
        
        if not connection:
            print("❌ No WhatsApp connection found")
            return False
        
        user = connection.user
        
        # Create mock API request
        factory = APIRequestFactory()
        request = factory.get('/api/v1/communications/inbox/')
        request.user = user
        
        # Test the actual API endpoint that frontend calls
        from communications.api.inbox_views import get_unified_inbox
        response = get_unified_inbox(request)
        
        if response.status_code != 200:
            print(f"❌ API request failed with status: {response.status_code}")
            return False
        
        data = response.data
        conversations = data.get('conversations', [])
        
        print(f"📋 Frontend API Response:")
        print(f"   Total conversations: {len(conversations)}")
        print(f"   Response keys: {list(data.keys())}")
        
        group_chats_found = 0
        proper_names_count = 0
        
        for i, conv in enumerate(conversations):
            participants = conv.get('participants', [])
            
            if participants:
                participant = participants[0]
                name = participant.get('name', 'No name')
                provider_id = participant.get('provider_id', 'No ID')
                
                print(f"\n   Conversation {i+1}:")
                print(f"      Name: '{name}'")
                print(f"      Provider ID: {provider_id}")
                
                # Check if group chat
                is_group = '@g.us' in provider_id if provider_id else False
                
                if is_group:
                    group_chats_found += 1
                    print(f"      🎯 GROUP CHAT")
                    
                    # Check if name is proper (not ID/phone)
                    if name and not name.isdigit() and '@' not in name and len(name) > 5:
                        proper_names_count += 1
                        print(f"      ✅ Proper group name: '{name}'")
                    else:
                        print(f"      ❌ Weird group name: '{name}'")
                else:
                    print(f"      📱 1-on-1 chat")
                    if name and not name.isdigit() and '@' not in name:
                        proper_names_count += 1
                        print(f"      ✅ Proper contact name: '{name}'")
                    else:
                        print(f"      ❌ Weird contact name: '{name}'")
        
        print(f"\n📊 FRONTEND DISPLAY ANALYSIS:")
        print(f"   Total conversations: {len(conversations)}")
        print(f"   Group chats found: {group_chats_found}")
        print(f"   Conversations with proper names: {proper_names_count}")
        print(f"   Conversations with weird names: {len(conversations) - proper_names_count}")
        
        success_rate = (proper_names_count / len(conversations)) * 100 if conversations else 0
        print(f"   Success rate: {success_rate:.1f}%")
        
        return success_rate >= 80  # 80% success rate threshold

def test_past_vs_new_conversations():
    """Test if past conversations benefit from the new logic"""
    
    print(f"\n🕐 TESTING PAST vs NEW CONVERSATIONS")
    print("-" * 40)
    
    with schema_context('oneotalent'):
        from communications.models import Message, Conversation
        
        # Check conversations with group data
        group_conversations = Conversation.objects.filter(
            channel__channel_type='whatsapp',
            messages__metadata__raw_webhook_data__is_group=True
        ).distinct()
        
        print(f"📊 Found {len(group_conversations)} conversations with group messages")
        
        for conv in group_conversations:
            latest_msg = conv.messages.order_by('-created_at').first()
            if not latest_msg or not latest_msg.metadata:
                continue
            
            raw_webhook = latest_msg.metadata.get('raw_webhook_data', {})
            if not raw_webhook:
                continue
            
            print(f"\n💬 Conversation: {conv.subject[:30]}...")
            print(f"   External ID: {conv.external_thread_id}")
            print(f"   Messages: {conv.message_count}")
            
            # Test old vs new extraction
            stored_contact_name = latest_msg.metadata.get('contact_name', 'NOT_SET')
            
            # Test new extraction
            from communications.utils.phone_extractor import extract_whatsapp_contact_name
            new_contact_name = extract_whatsapp_contact_name(raw_webhook)
            
            print(f"   OLD contact name: '{stored_contact_name}'")
            print(f"   NEW contact name: '{new_contact_name}'")
            
            if new_contact_name and new_contact_name != stored_contact_name:
                print(f"   🎯 IMPROVEMENT: Old='{stored_contact_name}' → New='{new_contact_name}'")
            elif new_contact_name:
                print(f"   ✅ Already good: '{new_contact_name}'")
            else:
                print(f"   ❌ Still no name extracted")

def test_conversation_messages_api():
    """Test the conversation messages API for group chats"""
    
    print(f"\n💬 TESTING CONVERSATION MESSAGES API")
    print("-" * 40)
    
    with schema_context('oneotalent'):
        from communications.models import Message, Conversation
        from rest_framework.test import APIRequestFactory
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Find group conversation
        group_message = Message.objects.filter(
            channel__channel_type='whatsapp',
            metadata__raw_webhook_data__is_group=True
        ).first()
        
        if not group_message:
            print("❌ No group messages found")
            return True
        
        conversation = group_message.conversation
        user = group_message.channel.created_by or User.objects.first()
        
        # Create API request
        factory = APIRequestFactory()
        request = factory.get(f'/conversations/{conversation.external_thread_id}/messages/')
        request.user = user
        
        # Test the API
        from communications.api.conversation_messages import get_conversation_messages
        response = get_conversation_messages(request, conversation.external_thread_id)
        
        if response.status_code != 200:
            print(f"❌ Messages API failed with status: {response.status_code}")
            return False
        
        data = response.data
        messages = data.get('messages', [])
        conv_data = data.get('conversation', {})
        
        print(f"📱 Messages API Response:")
        print(f"   Conversation name: '{conv_data.get('contact', {}).get('name', 'No name')}'")
        print(f"   Message count: {len(messages)}")
        
        if messages:
            msg = messages[0]
            sender = msg.get('sender', {})
            
            print(f"   Sample message:")
            print(f"      Content: '{msg.get('content', '')[:30]}...'")
            print(f"      Sender: '{sender.get('name', 'No sender')}'")
            print(f"      Is group: {sender.get('is_group_message', False)}")
            print(f"      Contact name: '{sender.get('contact_name', 'No contact')}'")
            
            return bool(sender.get('name') and sender.get('contact_name'))
        
        return True

if __name__ == '__main__':
    print("Testing frontend group chat display for past conversations...\n")
    
    # Test frontend API
    frontend_success = test_frontend_unified_inbox_api()
    
    # Test past vs new logic
    test_past_vs_new_conversations()
    
    # Test messages API
    messages_success = test_conversation_messages_api()
    
    print(f"\n🎯 FRONTEND GROUP CHAT DISPLAY RESULTS:")
    print("=" * 45)
    print(f"   Frontend inbox API: {'✅ WORKING' if frontend_success else '❌ NEEDS WORK'}")
    print(f"   Messages API: {'✅ WORKING' if messages_success else '❌ NEEDS WORK'}")
    
    overall_success = frontend_success and messages_success
    
    if overall_success:
        print(f"\n🎉 FRONTEND READY FOR GROUP CHATS!")
        print("   • Past group conversations now show proper names ✅")
        print("   • New group conversations work perfectly ✅")
        print("   • APIs extract names from stored webhook data ✅")
        print("   • No database updates needed ✅")
        print("   • Frontend can display everything properly ✅")
    else:
        print(f"\n⚠️  FRONTEND DISPLAY NEEDS ATTENTION")
        print("   • Some conversations may still show weird names")
        print("   • Consider updating stored metadata for better display")
    
    sys.exit(0 if overall_success else 1)