#!/usr/bin/env python
"""
Test the fix for 'int' object is not iterable error
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from communications.models import Conversation, Channel, UserChannelConnection
from communications.channels.whatsapp.sync.messages import MessageSyncService

def test_fix():
    """Test that the error handling works correctly"""
    
    print("\n" + "="*80)
    print("TESTING ERROR FIX: 'int' object is not iterable")
    print("="*80)
    
    with schema_context('oneotalent'):
        # Get a conversation to test with
        conversation = Conversation.objects.filter(
            channel__channel_type='whatsapp'
        ).first()
        
        if not conversation:
            print("No WhatsApp conversations found")
            return
        
        print(f"\n📂 Testing with conversation: {conversation.external_thread_id[:30]}...")
        
        # Get channel and connection
        channel = Channel.objects.filter(channel_type='whatsapp').first()
        connection = UserChannelConnection.objects.filter(channel_type='whatsapp').first()
        
        if not channel or not connection:
            print("Missing channel or connection")
            return
        
        # Initialize message sync service
        message_service = MessageSyncService(channel, connection)
        
        # Test sync with pagination (where the error occurred)
        print("\n🔍 Testing paginated sync...")
        try:
            stats = message_service.sync_messages_for_conversation(
                conversation,
                max_messages=50,  # Small number for quick test
                use_pagination=True
            )
            
            print(f"✅ Sync completed successfully!")
            print(f"   Messages synced: {stats['messages_synced']}")
            print(f"   Messages created: {stats['messages_created']}")
            print(f"   Errors: {stats.get('errors', [])}")
            
            # Verify errors is a list
            if isinstance(stats.get('errors'), list):
                print(f"✅ 'errors' is correctly a list")
            else:
                print(f"❌ 'errors' is {type(stats.get('errors'))}, not a list!")
                
        except TypeError as e:
            if "'int' object is not iterable" in str(e):
                print(f"❌ ERROR NOT FIXED: {e}")
            else:
                print(f"❌ Different error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

if __name__ == '__main__':
    test_fix()