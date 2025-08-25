#!/usr/bin/env python
"""
Direct sync test bypassing API views
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
from communications.models import UserChannelConnection, Channel, Conversation, Message, ChatAttendee
from communications.channels.whatsapp.background_sync import _run_comprehensive_sync_simplified

User = get_user_model()

def test_direct_sync():
    """Run a direct sync test"""
    
    # Switch to oneotalent schema
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with schema_context(tenant.schema_name):
        print("\n🚀 DIRECT SYNC TEST")
        print("=" * 60)
        
        # Get a user
        user = User.objects.filter(is_active=True).first()
        if not user:
            print("❌ No active user found")
            return
            
        print(f"✅ User: {user.username}")
        
        # Get WhatsApp connections
        whatsapp_connections = UserChannelConnection.objects.filter(
            user=user,
            channel_type='whatsapp',
            is_active=True,
            unipile_account_id__isnull=False
        )
        
        print(f"\n📊 Found {whatsapp_connections.count()} WhatsApp connections")
        
        if not whatsapp_connections.exists():
            print("❌ No active WhatsApp connections found")
            return
        
        # Clear existing data for a fresh test
        print("\n🧹 Clearing existing data for fresh sync...")
        Message.objects.all().delete()
        Conversation.objects.all().delete()
        ChatAttendee.objects.all().delete()
        print("   ✅ Data cleared")
        
        # Process each connection
        for connection in whatsapp_connections:
            print(f"\n🔄 Syncing connection: {connection.account_name}")
            print(f"   UniPile account ID: {connection.unipile_account_id}")
            
            # Get or create channel
            channel, created = Channel.objects.get_or_create(
                unipile_account_id=connection.unipile_account_id,
                channel_type='whatsapp',
                defaults={
                    'name': f"WhatsApp Account {connection.account_name}",
                    'auth_status': 'authenticated',
                    'is_active': True,
                    'created_by': user
                }
            )
            
            print(f"   Channel: {channel.name} (created: {created})")
            
            # Run sync
            print(f"   Running sync...")
            
            sync_options = {
                'days_back': 30,
                'max_messages_per_chat': 100,
            }
            
            try:
                stats = _run_comprehensive_sync_simplified(
                    channel=channel,
                    options=sync_options,
                    connection=connection
                )
                
                print(f"\n   ✅ SYNC COMPLETED:")
                print(f"      Chats synced: {stats.get('chats_synced', 0)}")
                print(f"      Messages synced: {stats.get('messages_synced', 0)}")
                print(f"      Attendees synced: {stats.get('attendees_synced', 0)}")
                print(f"      Conversations created: {stats.get('conversations_created', 0)}")
                print(f"      Conversations updated: {stats.get('conversations_updated', 0)}")
                
                if stats.get('errors'):
                    print(f"\n   ⚠️ Errors:")
                    for error in stats['errors']:
                        print(f"      - {error}")
                
            except Exception as e:
                print(f"   ❌ Sync failed: {e}")
                import traceback
                traceback.print_exc()
        
        # Verify results
        print("\n" + "=" * 60)
        print("📊 VERIFICATION RESULTS")
        print("=" * 60)
        
        # Check conversations
        conversations = Conversation.objects.all()
        print(f"\n📱 CHATS/CONVERSATIONS: {conversations.count()}")
        for conv in conversations[:3]:
            print(f"   - {conv.subject or 'No subject'} (External ID: {conv.external_thread_id})")
        
        # Check attendees
        attendees = ChatAttendee.objects.all()
        print(f"\n👥 ATTENDEES: {attendees.count()}")
        
        # Check for account owners
        account_owners = attendees.filter(is_self=True)
        print(f"   Account owners (is_self=True): {account_owners.count()}")
        for owner in account_owners:
            print(f"      - {owner.name} ({owner.phone_number})")
        
        # Regular attendees
        regular_attendees = attendees.filter(is_self=False)
        print(f"   Regular attendees: {regular_attendees.count()}")
        for att in regular_attendees[:5]:
            print(f"      - {att.name} ({att.phone_number})")
        
        # Check messages
        messages = Message.objects.all()
        print(f"\n📨 MESSAGES: {messages.count()}")
        
        # Count by direction
        in_messages = messages.filter(direction='in').count()
        out_messages = messages.filter(direction='out').count()
        
        print(f"\n📊 MESSAGE DIRECTION:")
        print(f"   Inbound (in): {in_messages}")
        print(f"   Outbound (out): {out_messages}")
        
        # Sample messages
        print(f"\n📨 SAMPLE MESSAGES (first 10):")
        for msg in messages[:10]:
            sender_name = msg.sender.name if msg.sender else "No sender"
            content = msg.content[:50] if msg.content else "No content"
            direction_emoji = "📤" if msg.direction == 'out' else "📥"
            
            print(f"   {direction_emoji} [{msg.direction}] {sender_name}: {content}")
            
            # Check for issues
            if msg.direction == 'out' and not msg.sender:
                print(f"      ⚠️ WARNING: Outbound message without sender!")
            elif msg.direction == 'out' and msg.sender and not msg.sender.is_self:
                print(f"      ⚠️ WARNING: Outbound message sender not marked as is_self!")
        
        # Summary
        print("\n" + "=" * 60)
        print("✅ DIRECT SYNC TEST COMPLETE!")
        print("=" * 60)
        print(f"\nSUMMARY:")
        print(f"   ✅ Conversations: {conversations.count()}")
        print(f"   ✅ Attendees: {attendees.count()} (Account owners: {account_owners.count()})")
        print(f"   ✅ Messages: {messages.count()} (In: {in_messages}, Out: {out_messages})")
        
        # Check for potential issues
        if out_messages > 0:
            out_without_sender = messages.filter(direction='out', sender__isnull=True).count()
            if out_without_sender > 0:
                print(f"\n   ⚠️ Issue: {out_without_sender} outbound messages without sender")
        
        if messages.count() > 0 and in_messages == 0:
            print(f"\n   ⚠️ Issue: No inbound messages found")
        
        if messages.count() > 0 and out_messages == 0:
            print(f"\n   ⚠️ Issue: No outbound messages found")

if __name__ == "__main__":
    test_direct_sync()