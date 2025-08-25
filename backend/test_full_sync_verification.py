#!/usr/bin/env python
"""
Run a full sync and verify everything is working
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
from communications.models import Conversation, Message, ChatAttendee

User = get_user_model()

def test_full_sync_verification():
    """Run a full sync and verify all components"""
    
    # Switch to oneotalent schema
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with schema_context(tenant.schema_name):
        print("\n🚀 FULL SYNC VERIFICATION TEST")
        print("=" * 60)
        
        # Get a user for the request
        user = User.objects.filter(is_active=True).first()
        if not user:
            print("❌ No active user found")
            return
            
        print(f"✅ User: {user.username}")
        
        # Create a request factory
        factory = RequestFactory()
        
        # Clear existing data for a fresh test
        print("\n🧹 Clearing existing data for fresh sync...")
        Message.objects.all().delete()
        Conversation.objects.all().delete()
        ChatAttendee.objects.all().delete()
        print("   ✅ Data cleared")
        
        # Step 1: Run the sync
        print("\n📱 Step 1: Running sync_whatsapp_data...")
        sync_request = factory.post('/api/whatsapp/sync/')
        sync_request.user = user
        
        try:
            sync_response = sync_whatsapp_data(sync_request)
            sync_data = sync_response.data
            
            if sync_data.get('success'):
                print(f"   ✅ Sync successful!")
                summary = sync_data.get('summary', {})
                print(f"   📊 Sync Results:")
                print(f"      Accounts synced: {summary.get('successful_syncs', 0)}/{summary.get('total_accounts', 0)}")
                print(f"      Messages synced: {summary.get('total_messages_synced', 0)}")
                print(f"      Conversations synced: {summary.get('total_conversations_synced', 0)}")
                print(f"      Attendees synced: {summary.get('total_attendees_synced', 0)}")
                
                # Show individual results
                for result in sync_data.get('sync_results', []):
                    if result.get('success'):
                        print(f"\n      Account {result.get('account_id')}:")
                        print(f"         Messages: {result.get('messages_synced', 0)}")
                        print(f"         Conversations: {result.get('conversations_synced', 0)}")
                        print(f"         Attendees: {result.get('attendees_synced', 0)}")
            else:
                print(f"   ❌ Sync failed: {sync_data.get('error')}")
                return
        except Exception as e:
            print(f"   ❌ Error during sync: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Step 2: Verify chats were created
        print("\n📱 Step 2: Verifying chats...")
        chats_request = factory.get('/api/whatsapp/chats/', {
            'account_id': 'mp9Gis3IRtuh9V5oSxZdSA',
            'limit': 10
        })
        chats_request.user = user
        
        try:
            chats_response = get_whatsapp_chats_local_first(chats_request)
            chats_data = chats_response.data
            
            if chats_data.get('success'):
                chats = chats_data.get('chats', [])
                print(f"   ✅ Got {len(chats)} chats")
                
                # Show first 3 chats
                for i, chat in enumerate(chats[:3], 1):
                    print(f"\n   Chat {i}:")
                    print(f"      Name: {chat.get('name', 'Unknown')}")
                    print(f"      ID: {chat.get('id')}")
                    print(f"      Message count: {chat.get('message_count', 0)}")
                    print(f"      Attendee count: {len(chat.get('attendees', []))}")
                    
                    # Show attendees
                    for att in chat.get('attendees', [])[:2]:
                        print(f"      Attendee: {att.get('name')} ({att.get('phone')})")
            else:
                print(f"   ❌ Failed to get chats: {chats_data.get('error')}")
        except Exception as e:
            print(f"   ❌ Error getting chats: {e}")
        
        # Step 3: Verify attendees
        print("\n👥 Step 3: Verifying attendees...")
        total_attendees = ChatAttendee.objects.count()
        print(f"   Total attendees in database: {total_attendees}")
        
        # Check account owner attendees
        account_owner_attendees = ChatAttendee.objects.filter(is_self=True)
        print(f"   Account owner attendees (is_self=True): {account_owner_attendees.count()}")
        for att in account_owner_attendees[:3]:
            print(f"      - {att.name} ({att.external_attendee_id})")
        
        # Step 4: Verify messages and direction
        print("\n📨 Step 4: Verifying messages and direction...")
        
        # Find a chat with messages
        chat_with_messages = None
        for chat in chats:
            if chat.get('message_count', 0) > 0:
                chat_with_messages = chat
                break
        
        if chat_with_messages:
            print(f"   Testing chat: {chat_with_messages.get('name', 'Unknown')}")
            print(f"   Chat ID: {chat_with_messages.get('id')}")
            
            messages_request = factory.get(f"/api/whatsapp/chats/{chat_with_messages.get('id')}/messages/", {
                'limit': 10
            })
            messages_request.user = user
            
            try:
                messages_response = get_chat_messages_local_first(messages_request, chat_with_messages.get('id'))
                messages_data = messages_response.data
                
                if messages_data.get('success'):
                    messages = messages_data.get('messages', [])
                    print(f"   ✅ Got {len(messages)} messages")
                    
                    # Count by direction
                    in_count = sum(1 for m in messages if m.get('direction') == 'in')
                    out_count = sum(1 for m in messages if m.get('direction') == 'out')
                    
                    print(f"\n   📊 Message Direction Summary:")
                    print(f"      Inbound (in): {in_count}")
                    print(f"      Outbound (out): {out_count}")
                    
                    print(f"\n   📨 Sample Messages:")
                    for msg in messages[:5]:
                        sender_name = msg.get('sender', {}).get('name', 'Unknown')
                        sender_id = msg.get('sender', {}).get('id', 'N/A')
                        is_self = msg.get('sender', {}).get('is_self', False)
                        content = msg.get('content', 'No content')[:50]
                        direction = msg.get('direction', 'unknown')
                        
                        direction_emoji = "📤" if direction == 'out' else "📥"
                        self_indicator = " (You)" if is_self else ""
                        
                        print(f"      {direction_emoji} [{direction}] {sender_name}{self_indicator}: {content}")
                        
                        # Verify outbound messages have proper sender
                        if direction == 'out' and (sender_name == 'Unknown' or not sender_id or sender_id == 'None'):
                            print(f"         ⚠️ WARNING: Outbound message missing sender info!")
                        elif direction == 'out' and not is_self:
                            print(f"         ⚠️ WARNING: Outbound message not marked as is_self!")
                else:
                    print(f"   ❌ Failed to get messages: {messages_data.get('error')}")
            except Exception as e:
                print(f"   ❌ Error getting messages: {e}")
        else:
            print("   ⚠️ No chats with messages found")
        
        # Step 5: Database verification
        print("\n🗄️ Step 5: Database Verification...")
        total_conversations = Conversation.objects.count()
        total_messages = Message.objects.count()
        total_attendees = ChatAttendee.objects.count()
        
        print(f"   📊 Database Totals:")
        print(f"      Conversations: {total_conversations}")
        print(f"      Messages: {total_messages}")
        print(f"      Attendees: {total_attendees}")
        
        # Check message directions in database
        in_messages = Message.objects.filter(direction='in').count()
        out_messages = Message.objects.filter(direction='out').count()
        
        print(f"\n   📊 Message Directions in Database:")
        print(f"      Inbound: {in_messages}")
        print(f"      Outbound: {out_messages}")
        
        # Check messages with senders
        messages_with_sender = Message.objects.filter(sender__isnull=False).count()
        messages_without_sender = Message.objects.filter(sender__isnull=True).count()
        
        print(f"\n   📊 Message Sender Linking:")
        print(f"      With sender: {messages_with_sender}")
        print(f"      Without sender: {messages_without_sender}")
        
        if messages_without_sender > 0:
            # Check if they're all outbound
            orphaned_out = Message.objects.filter(sender__isnull=True, direction='out').count()
            orphaned_in = Message.objects.filter(sender__isnull=True, direction='in').count()
            print(f"      Orphaned outbound: {orphaned_out}")
            print(f"      Orphaned inbound: {orphaned_in}")
        
        print("\n" + "=" * 60)
        print("✅ FULL SYNC VERIFICATION COMPLETE!")
        print("=" * 60)

if __name__ == "__main__":
    test_full_sync_verification()