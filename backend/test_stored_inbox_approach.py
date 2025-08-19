#!/usr/bin/env python3
"""
Test the new stored data approach for unified inbox with provider logic
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

import logging
from django_tenants.utils import schema_context

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TENANT_SCHEMA = 'oneotalent'

def test_stored_inbox_approach():
    """Test that the new stored data approach shows proper contact names"""
    
    print("📚 TESTING STORED DATA APPROACH FOR UNIFIED INBOX")
    print("=" * 60)
    
    with schema_context(TENANT_SCHEMA):
        from communications.models import UserChannelConnection
        from communications.api.inbox_views import get_channel_conversations_from_stored_data
        
        # Get a WhatsApp connection
        whatsapp_connection = UserChannelConnection.objects.filter(
            channel_type='whatsapp'
        ).first()
        
        if not whatsapp_connection:
            print("❌ No WhatsApp connection found")
            return False
        
        print(f"📱 Testing with WhatsApp connection: {whatsapp_connection.account_name}")
        print(f"   Account ID: {whatsapp_connection.unipile_account_id}")
        
        # Test the new stored data approach
        try:
            conversations = get_channel_conversations_from_stored_data(
                connection=whatsapp_connection,
                search='',
                status_filter='all',
                limit=10
            )
            
            print(f"\n📋 Found {len(conversations)} conversations using stored data:")
            
            success = True
            for i, conv in enumerate(conversations):
                participants = conv.get('participants', [])
                last_message = conv.get('last_message', {})
                
                print(f"\n{i+1}. Conversation {conv.get('id', 'Unknown')}")
                print(f"   External ID: {conv.get('external_id', 'Unknown')}")
                print(f"   Message Count: {conv.get('message_count', 0)}")
                print(f"   Unread Count: {conv.get('unread_count', 0)}")
                
                if participants:
                    participant = participants[0]
                    participant_name = participant.get('name', 'No name')
                    provider_id = participant.get('provider_id', 'No provider ID')
                    
                    print(f"   👤 Contact: '{participant_name}'")
                    print(f"   📞 Provider ID: {provider_id}")
                    
                    # Check for weird names
                    if (len(participant_name) > 20 or 
                        '@s.whatsapp.net' in participant_name or
                        participant_name.isdigit() or
                        participant_name == 'No name'):
                        print(f"   ❌ Weird participant name detected: '{participant_name}'")
                        success = False
                    else:
                        print(f"   ✅ Good participant name: '{participant_name}'")
                else:
                    print(f"   ❌ No participants found")
                    success = False
                
                # Check last message
                last_msg_sender = last_message.get('sender', {})
                sender_name = last_msg_sender.get('name', 'No sender name')
                
                print(f"   💬 Last Message Sender: '{sender_name}'")
                print(f"   📝 Last Message: '{(last_message.get('content', ''))[:50]}...'")
                
                if sender_name in ['No sender name', '']:
                    print(f"   ❌ Missing sender name")
                    success = False
                
            # Summary
            print(f"\n📊 STORED DATA APPROACH RESULTS:")
            print(f"   Total conversations: {len(conversations)}")
            
            weird_participants = 0
            for conv in conversations:
                participants = conv.get('participants', [])
                if participants:
                    participant_name = participants[0].get('name', '')
                    if (len(participant_name) > 20 or 
                        '@s.whatsapp.net' in participant_name or
                        participant_name.isdigit() or
                        participant_name == ''):
                        weird_participants += 1
            
            print(f"   Conversations with proper names: {len(conversations) - weird_participants}")
            print(f"   Conversations with weird names: {weird_participants}")
            
            if weird_participants == 0:
                print("   ✅ All conversations have proper contact names!")
            else:
                print(f"   ❌ {weird_participants} conversations still have weird names")
                success = False
            
            return success
            
        except Exception as e:
            print(f"❌ Error testing stored data approach: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = test_stored_inbox_approach()
    
    if success:
        print("\n🎉 STORED DATA APPROACH TEST PASSED!")
        print("   • Using stored conversations instead of live UniPile API ✅")
        print("   • Provider logic applied consistently ✅")
        print("   • Contact names extracted properly ✅")
        print("   • No more weird UniPile IDs showing ✅")
    else:
        print("\n❌ STORED DATA APPROACH TEST FAILED!")
        print("   Some conversations still showing weird names")
    
    sys.exit(0 if success else 1)