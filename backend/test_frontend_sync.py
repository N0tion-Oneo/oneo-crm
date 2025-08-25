#!/usr/bin/env python
"""
Test the frontend sync endpoint to see if messages are returned properly
"""
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from communications.channels.whatsapp.api_views import sync_whatsapp_data, get_whatsapp_chats_local_first, get_chat_messages_local_first

User = get_user_model()

def test_frontend_sync():
    """Test the frontend sync flow"""
    
    # Switch to oneotalent schema
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with schema_context(tenant.schema_name):
        print("\n🔍 Testing Frontend Sync Flow")
        print("=" * 60)
        
        # Get a user for the request
        user = User.objects.filter(is_active=True).first()
        if not user:
            print("❌ No active user found")
            return
            
        print(f"✅ Using user: {user.username}")
        
        # Clear existing data first for a clean test
        from communications.models import Message, Conversation, ChatAttendee
        print("\n🧹 Clearing existing data...")
        Message.objects.all().delete()
        Conversation.objects.all().delete()
        ChatAttendee.objects.all().delete()
        print("   ✅ Data cleared")
        
        # Create a request factory
        factory = RequestFactory()
        
        # Step 1: Call sync_whatsapp_data (what the sync button does)
        print("\n📱 Step 1: Calling sync_whatsapp_data (sync button)...")
        sync_request = factory.post('/api/whatsapp/sync/')
        sync_request.user = user
        
        try:
            sync_response = sync_whatsapp_data(sync_request)
            sync_data = sync_response.data
            
            if sync_data.get('success'):
                print(f"   ✅ Sync successful!")
                summary = sync_data.get('summary', {})
                print(f"   Accounts synced: {summary.get('successful_syncs', 0)}/{summary.get('total_accounts', 0)}")
                print(f"   Messages synced: {summary.get('total_messages_synced', 0)}")
                print(f"   Conversations synced: {summary.get('total_conversations_synced', 0)}")
                print(f"   Attendees synced: {summary.get('total_attendees_synced', 0)}")
            else:
                print(f"   ❌ Sync failed: {sync_data.get('error')}")
                return
        except Exception as e:
            print(f"   ❌ Error during sync: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Step 2: Get chats list (what frontend does after sync)
        print("\n📱 Step 2: Getting chats list...")
        chats_request = factory.get('/api/whatsapp/chats/', {
            'account_id': 'mp9Gis3IRtuh9V5oSxZdSA',
            'limit': 5
        })
        chats_request.user = user
        
        try:
            chats_response = get_whatsapp_chats_local_first(chats_request)
            chats_data = chats_response.data
            
            if chats_data.get('success'):
                chats = chats_data.get('chats', [])
                print(f"   ✅ Got {len(chats)} chats")
                
                # Step 3: Get messages for first chat with messages
                for chat in chats:
                    if chat.get('message_count', 0) > 0:
                        print(f"\n📱 Step 3: Getting messages for chat '{chat.get('name', 'Unknown')}'...")
                        print(f"   Chat ID: {chat.get('id')}")
                        print(f"   Message count: {chat.get('message_count')}")
                        
                        messages_request = factory.get(f"/api/whatsapp/chats/{chat.get('id')}/messages/", {
                            'limit': 5
                        })
                        messages_request.user = user
                        
                        try:
                            messages_response = get_chat_messages_local_first(messages_request, chat.get('id'))
                            messages_data = messages_response.data
                            
                            if messages_data.get('success'):
                                messages = messages_data.get('messages', [])
                                print(f"   ✅ Got {len(messages)} messages:")
                                
                                for msg in messages[:5]:
                                    sender_name = msg.get('sender', {}).get('name', 'Unknown')
                                    sender_id = msg.get('sender', {}).get('id', 'N/A')
                                    is_self = msg.get('sender', {}).get('is_self', False)
                                    content = msg.get('content', 'No content')[:50]
                                    direction = msg.get('direction', 'unknown')
                                    
                                    self_indicator = " (You)" if is_self else ""
                                    print(f"      [{direction}] {sender_name}{self_indicator}: {content}")
                                    
                                    if sender_name == 'Unknown' or not sender_id or sender_id == 'None':
                                        print(f"         ⚠️ Missing sender info! ID: {sender_id}")
                            else:
                                print(f"   ❌ Failed to get messages: {messages_data.get('error')}")
                        except Exception as e:
                            print(f"   ❌ Error getting messages: {e}")
                        
                        # Only test first chat with messages
                        break
            else:
                print(f"   ❌ Failed to get chats: {chats_data.get('error')}")
        except Exception as e:
            print(f"   ❌ Error getting chats: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 60)
        print("✅ Frontend sync flow test complete!")
        print("=" * 60)

if __name__ == "__main__":
    test_frontend_sync()