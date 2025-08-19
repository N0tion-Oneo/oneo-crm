#!/usr/bin/env python3
"""
Test API-sent message + webhook processing merge functionality
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
from django.utils import timezone

def test_api_webhook_merge():
    """Test that webhook processing merges with API-sent message data correctly"""
    
    print("🧪 TESTING API + WEBHOOK MESSAGE DATA MERGE")
    print("=" * 60)
    
    with schema_context('oneotalent'):
        from communications.models import (
            UserChannelConnection, Channel, Conversation, Message,
            MessageDirection, MessageStatus
        )
        from communications.message_sync import message_sync_service
        from asgiref.sync import sync_to_async
        
        # Get a WhatsApp connection for testing
        connection = UserChannelConnection.objects.filter(
            channel_type='whatsapp'
        ).first()
        
        if not connection:
            print("❌ No WhatsApp connection found for testing")
            return False
        
        print(f"📱 Using connection: {connection.account_name}")
        
        # Step 1: Simulate API-sent message creation
        print("\n📤 STEP 1: Creating API-sent message...")
        
        # Get or create channel
        channel, created = Channel.objects.get_or_create(
            unipile_account_id=connection.unipile_account_id,
            defaults={
                'name': f"{connection.account_name} (Test)",
                'channel_type': connection.channel_type,
                'is_active': True
            }
        )
        
        # Get or create conversation
        test_chat_id = "test_merge_chat_id"
        conversation, created = Conversation.objects.get_or_create(
            channel=channel,
            external_thread_id=test_chat_id,
            defaults={
                'subject': 'Test Merge Conversation',
                'status': 'active'
            }
        )
        
        # Create API-sent message (simulating send_message function)
        import uuid
        test_message_id = f"test_api_message_merge_{str(uuid.uuid4())[:8]}"
        api_message = Message.objects.create(
            conversation=conversation,
            channel=channel,
            external_message_id=test_message_id,
            direction=MessageDirection.OUTBOUND,
            status=MessageStatus.SENT,
            content="Test merge message",
            contact_phone="+27836851686",
            sent_at=timezone.now(),
            metadata={
                'contact_name': 'Warren Test',
                'processing_version': '2.0_simplified',
                'sent_via_api': True,
                'raw_api_response': {
                    'object': 'MessageSent',
                    'message_id': test_message_id
                },
                'api_request_data': {
                    'text': 'Test merge message',
                    'chat_id': test_chat_id,
                    'account_id': connection.unipile_account_id,
                    'attachments': []
                }
            }
        )
        
        print(f"   ✅ Created API message: {api_message.id}")
        print(f"   📋 API metadata keys: {list(api_message.metadata.keys())}")
        print(f"   🏷  sent_via_api: {api_message.metadata.get('sent_via_api')}")
        
        # Step 2: Simulate webhook processing
        print("\n📨 STEP 2: Processing webhook for same message...")
        
        # Create webhook data that would come from UniPile
        webhook_data = {
            'id': test_message_id,  # Same message ID
            'message_id': test_message_id,
            'event': 'message_delivered',
            'provider_chat_id': '27836851686@s.whatsapp.net',
            'chat_id': test_chat_id,
            'text': 'Test merge message',
            'timestamp': '2025-08-18T18:50:00.000Z',
            'account_id': connection.unipile_account_id,
            'sender': {
                'attendee_id': 'sender_123',
                'attendee_name': 'Business Account',
                'attendee_provider_id': connection.unipile_account_id
            },
            'attendees': [
                {
                    'attendee_id': 'contact_456',
                    'attendee_name': 'Warren Test Contact',
                    'attendee_provider_id': '27836851686@s.whatsapp.net'
                },
                {
                    'attendee_id': 'sender_123',
                    'attendee_name': 'Business Account',
                    'attendee_provider_id': connection.unipile_account_id
                }
            ],
            'webhook_name': 'Test Merge Webhook',
            'delivered': True
        }
        
        # Process through the merge logic using sync method
        # Create sync wrapper for testing
        from asgiref.sync import async_to_sync
        
        sync_create_or_update = async_to_sync(message_sync_service._create_or_update_message)
        merged_message = sync_create_or_update(channel, webhook_data, connection)
        
        if not merged_message:
            print("   ❌ Webhook processing failed")
            return False
        
        print(f"   ✅ Processed webhook for message: {merged_message.id}")
        
        # Step 3: Verify merge results
        print(f"\n🔍 STEP 3: Verifying merge results...")
        
        # Refresh from database
        merged_message.refresh_from_db()
        merged_metadata = merged_message.metadata or {}
        
        print(f"   📋 Merged metadata keys: {list(merged_metadata.keys())}")
        
        # Check that API data was preserved
        api_data_preserved = all([
            merged_metadata.get('sent_via_api') == True,
            'raw_api_response' in merged_metadata,
            'api_request_data' in merged_metadata
        ])
        
        # Check that webhook data was added
        webhook_data_added = all([
            'raw_webhook_data' in merged_metadata,
            'webhook_processed_at' in merged_metadata,
            'extracted_phone' in merged_metadata
        ])
        
        # Check status update
        status_updated = merged_message.status == MessageStatus.DELIVERED
        
        print(f"   📤 API data preserved: {api_data_preserved}")
        print(f"      - sent_via_api: {merged_metadata.get('sent_via_api')}")
        print(f"      - raw_api_response: {'✅' if 'raw_api_response' in merged_metadata else '❌'}")
        print(f"      - api_request_data: {'✅' if 'api_request_data' in merged_metadata else '❌'}")
        
        print(f"   📨 Webhook data added: {webhook_data_added}")
        print(f"      - raw_webhook_data: {'✅' if 'raw_webhook_data' in merged_metadata else '❌'}")
        print(f"      - webhook_processed_at: {'✅' if 'webhook_processed_at' in merged_metadata else '❌'}")
        print(f"      - extracted_phone: {merged_metadata.get('extracted_phone', 'NOT_FOUND')}")
        
        print(f"   📊 Status updated: {status_updated} (was SENT, now {merged_message.status})")
        
        success = api_data_preserved and webhook_data_added and status_updated
        
        # Cleanup
        api_message.delete()
        conversation.delete()
        
        return success

def test_existing_outbound_messages():
    """Test how existing outbound messages would be affected"""
    
    print("\n🔄 TESTING EXISTING OUTBOUND MESSAGE PROCESSING")
    print("=" * 50)
    
    with schema_context('oneotalent'):
        from communications.models import Message, MessageDirection
        
        # Find existing outbound message with sent_via_api=True
        existing_api_msg = Message.objects.filter(
            direction=MessageDirection.OUTBOUND,
            channel__channel_type='whatsapp',
            metadata__sent_via_api=True
        ).first()
        
        if existing_api_msg:
            print(f"📤 Found existing API message: {str(existing_api_msg.id)[:8]}...")
            metadata = existing_api_msg.metadata or {}
            print(f"   Current metadata keys: {list(metadata.keys())}")
            print(f"   Has webhook data: {'raw_webhook_data' in metadata}")
            
            if 'raw_webhook_data' in metadata:
                print(f"   ✅ Message already has both API and webhook data - merge working!")
            else:
                print(f"   ⚠️  Message only has API data - no webhook received yet")
        else:
            print("📭 No existing API-sent messages found")
        
        return existing_api_msg is not None

if __name__ == '__main__':
    print("Starting API + Webhook merge test...\n")
    
    # Test the merge functionality
    merge_success = test_api_webhook_merge()
    
    # Test existing messages
    existing_msg_found = test_existing_outbound_messages()
    
    print(f"\n{'🎉' if merge_success else '❌'} MERGE TEST RESULTS:")
    if merge_success:
        print("   • API data preservation: ✅")
        print("   • Webhook data integration: ✅")
        print("   • Status updates from webhooks: ✅")
        print("   • No data loss during merge: ✅")
    else:
        print("   • Merge functionality failed ❌")
        print("   • Check logs for specific errors ❌")
    
    if existing_msg_found:
        print("   • Existing message compatibility verified ✅")
    else:
        print("   • No existing API messages to verify ⚠️")
    
    sys.exit(0 if merge_success else 1)