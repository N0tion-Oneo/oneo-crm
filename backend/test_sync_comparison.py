#!/usr/bin/env python
"""
Compare frontend sync vs background sync
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from django.contrib.auth import get_user_model
from communications.models import UserChannelConnection, Channel, Conversation, Message, ChatAttendee
from communications.channels.whatsapp.background_sync import _run_comprehensive_sync_simplified

User = get_user_model()

def test_frontend_sync_direct():
    """Test the frontend sync method directly"""
    
    # Switch to oneotalent schema
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with schema_context(tenant.schema_name):
        print("\n🚀 TESTING FRONTEND SYNC METHOD DIRECTLY")
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
        
        # Process first connection
        connection = whatsapp_connections.first()
        print(f"\n🔄 Testing with connection: {connection.account_name}")
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
        
        # Run the FRONTEND sync method
        print(f"\n📱 Running _run_comprehensive_sync_simplified (frontend method)...")
        
        sync_options = {
            'days_back': 30,
            'max_messages_per_chat': 50,  # Limit for testing
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
                print(f"\n   ⚠️ Errors encountered:")
                for error in stats['errors'][:5]:  # Show first 5 errors
                    print(f"      - {error}")
            
        except Exception as e:
            print(f"   ❌ Sync failed: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Verify results
        print("\n" + "=" * 60)
        print("📊 VERIFICATION RESULTS")
        print("=" * 60)
        
        # Check conversations
        conversations = Conversation.objects.all()
        print(f"\n📱 CHATS/CONVERSATIONS: {conversations.count()}")
        for conv in conversations[:3]:
            print(f"   - {conv.subject or 'No subject'} (Messages: {conv.messages.count()})")
        
        # Check attendees
        attendees = ChatAttendee.objects.all()
        print(f"\n👥 ATTENDEES: {attendees.count()}")
        account_owners = attendees.filter(is_self=True)
        print(f"   Account owners (is_self=True): {account_owners.count()}")
        
        # Check messages
        messages = Message.objects.all()
        print(f"\n📨 MESSAGES: {messages.count()}")
        
        # Count by direction
        in_messages = messages.filter(direction='inbound').count()
        out_messages = messages.filter(direction='outbound').count()
        
        print(f"\n📊 MESSAGE DIRECTION:")
        print(f"   Inbound (in): {in_messages}")
        print(f"   Outbound (out): {out_messages}")
        
        # Check for issues
        if messages.count() == 0:
            print(f"\n   ❌ ISSUE: No messages synced!")
        elif in_messages == 0:
            print(f"\n   ⚠️ ISSUE: No inbound messages")
        elif out_messages == 0:
            print(f"\n   ⚠️ ISSUE: No outbound messages")
        
        out_without_sender = messages.filter(direction='out', sender__isnull=True).count()
        if out_without_sender > 0:
            print(f"\n   ⚠️ ISSUE: {out_without_sender} outbound messages without sender")
        
        print("\n" + "=" * 60)
        print("✅ FRONTEND SYNC TEST COMPLETE!")
        print("=" * 60)

if __name__ == "__main__":
    test_frontend_sync_direct()