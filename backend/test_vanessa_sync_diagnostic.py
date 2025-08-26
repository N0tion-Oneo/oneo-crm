#!/usr/bin/env python
"""
Diagnostic script to specifically test Vanessa's sync issue
Tracks why only 305 of 727 messages are being saved
"""
import os
import sys
import django
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

# Set logging to DEBUG to see all our diagnostic messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from django_tenants.utils import schema_context
from communications.models import Conversation, Message, Channel, UserChannelConnection, ChatAttendee
from communications.channels.whatsapp.sync.messages import MessageSyncService
from communications.channels.whatsapp.client import WhatsAppClient
from asgiref.sync import async_to_sync

def test_vanessa_sync():
    """Test sync specifically for Vanessa's conversation"""
    
    with schema_context('oneotalent'):
        print("\n" + "="*80)
        print("VANESSA SYNC DIAGNOSTIC TEST")
        print("="*80)
        
        # Find Vanessa's conversation
        vanessa_conv = Conversation.objects.get(id='a8edade9-14f8-4661-b776-c128af1f4f1c')
        print(f"\n📂 Found Vanessa's conversation:")
        print(f"   ID: {vanessa_conv.id}")
        print(f"   External Thread ID: {vanessa_conv.external_thread_id}")
        print(f"   Current messages in DB: {Message.objects.filter(conversation=vanessa_conv).count()}")
        
        # Get channel and connection
        channel = Channel.objects.filter(channel_type='whatsapp').first()
        connection = UserChannelConnection.objects.filter(channel_type='whatsapp').first()
        
        if not channel or not connection:
            print("❌ No WhatsApp channel or connection found")
            return
        
        print(f"\n📱 Using channel: {channel.name}")
        print(f"   Account ID: {connection.unipile_account_id}")
        
        # Initialize services
        whatsapp_client = WhatsAppClient()
        message_sync_service = MessageSyncService(channel, connection)
        
        # First, let's check what the API returns directly
        print(f"\n🔍 Testing direct API call for Vanessa's conversation...")
        print(f"   External thread ID: {vanessa_conv.external_thread_id}")
        
        # Make a direct API call to see what we get
        api_result = async_to_sync(whatsapp_client.get_messages)(
            account_id='',  # Not used for chat-specific endpoints
            conversation_id=vanessa_conv.external_thread_id,
            limit=50  # Start with a small batch
        )
        
        if api_result.get('success'):
            messages = api_result.get('messages', [])
            print(f"\n✅ API returned {len(messages)} messages in first batch")
            
            # Check for duplicates in the API response
            external_ids = [msg.get('id') for msg in messages if msg.get('id')]
            unique_ids = set(external_ids)
            if len(external_ids) != len(unique_ids):
                print(f"⚠️ API returned duplicate IDs! {len(external_ids)} total, {len(unique_ids)} unique")
            
            # Show sample of message IDs
            print(f"\n📝 Sample message IDs from API:")
            for msg in messages[:3]:
                print(f"   - {msg.get('id')}: {msg.get('timestamp', 'no timestamp')[:19]}")
        else:
            print(f"❌ API call failed: {api_result.get('error')}")
            return
        
        # Now clear existing messages and run a fresh sync
        print(f"\n🧹 Clearing existing messages for fresh test...")
        deleted_count = Message.objects.filter(conversation=vanessa_conv).delete()[0]
        print(f"   Deleted {deleted_count} existing messages")
        
        # Run the sync with our enhanced logging
        print(f"\n🚀 Running sync with diagnostic logging...")
        print("   Target: 1000 messages")
        print("   Batch size: 200 messages per API call")
        
        stats = message_sync_service.sync_messages_for_conversation(
            conversation=vanessa_conv,
            max_messages=1000,
            use_pagination=True
        )
        
        print(f"\n📊 Sync Results:")
        print(f"   Messages synced: {stats['messages_synced']}")
        print(f"   Messages created: {stats['messages_created']}")
        print(f"   Messages updated: {stats['messages_updated']}")
        print(f"   API calls made: {stats.get('api_calls', 'unknown')}")
        print(f"   Errors: {stats.get('errors', 0)}")
        print(f"   Skipped: {stats.get('skipped', 0)}")
        
        # Verify what's in the database now
        final_count = Message.objects.filter(conversation=vanessa_conv).count()
        print(f"\n✅ Final database count: {final_count} messages")
        
        if final_count < 700:
            print(f"\n❌ ISSUE CONFIRMED: Only {final_count} messages saved when API has more!")
            print("   Check the logs above for DISCREPANCY messages")
        
        # Check for any unique constraint violations
        print(f"\n🔍 Checking for duplicate external IDs in database...")
        from django.db.models import Count
        duplicates = Message.objects.filter(
            conversation=vanessa_conv
        ).values('external_message_id').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        if duplicates:
            print(f"⚠️ Found {len(duplicates)} duplicate external IDs!")
            for dup in duplicates[:5]:
                print(f"   - {dup['external_message_id']}: {dup['count']} occurrences")
        else:
            print("✅ No duplicate external IDs found")
        
        print("\n" + "="*80)
        print("DIAGNOSTIC TEST COMPLETE")
        print("Check the logs above for detailed information about message processing")
        print("="*80 + "\n")

if __name__ == '__main__':
    test_vanessa_sync()