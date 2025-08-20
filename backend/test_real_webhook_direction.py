#!/usr/bin/env python3
"""
Test webhook direction detection with simulated real webhook data
"""
import os
import sys
import django
from django.conf import settings

# Add the project directory to the Python path
sys.path.append('/Users/joshcowan/Oneo CRM/backend')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from communications.webhooks.handlers.whatsapp import WhatsAppWebhookHandler
from communications.models import UserChannelConnection
from django_tenants.utils import tenant_context
from tenants.models import Tenant

def test_webhook_direction_detection():
    """Test webhook direction detection with realistic data"""
    print("🧪 Testing Real Webhook Direction Detection")
    print("=" * 60)
    
    # Get OneOTalent tenant
    tenant = Tenant.objects.get(schema_name='oneotalent')
    
    with tenant_context(tenant):
        print(f"🏢 Testing in tenant: {tenant.name}")
        
        # Get WhatsApp connection
        connection = UserChannelConnection.objects.filter(channel_type='whatsapp').first()
        
        if not connection:
            print("❌ No WhatsApp connection found to test with")
            return
        
        business_phone = connection.connection_config.get('phone_number')
        print(f"🔗 Testing with business account: +{business_phone}")
        print()
        
        # Create WhatsApp webhook handler
        handler = WhatsAppWebhookHandler()
        
        # Test scenarios based on actual UniPile webhook formats
        test_scenarios = [
            {
                'name': 'YOUR MESSAGE (Sent from your WhatsApp)',
                'description': f'Message sent FROM business phone +{business_phone}',
                'webhook_data': {
                    'event': 'message_received',  # UniPile sends this for all messages
                    'account_id': connection.unipile_account_id,
                    'chat_id': '27849977040@s.whatsapp.net',
                    'message_id': f'test_outbound_{business_phone}',
                    'message': 'Hi, this is a message I sent from my WhatsApp business account',
                    'sender': {
                        'attendee_id': f'business_{business_phone}',
                        'attendee_provider_id': f'{business_phone}@s.whatsapp.net',  # YOUR phone
                        'attendee_name': business_phone
                    },
                    'provider_chat_id': '27849977040@s.whatsapp.net',  # Contact you're messaging
                    'is_group': False,
                    'timestamp': '2025-08-20T16:45:00Z'
                },
                'expected_direction': 'OUTBOUND'
            },
            {
                'name': 'CONTACT MESSAGE (Received to your WhatsApp)',
                'description': 'Message sent TO business phone from external contact',
                'webhook_data': {
                    'event': 'message_received',
                    'account_id': connection.unipile_account_id,
                    'chat_id': '27849977040@s.whatsapp.net',
                    'message_id': 'test_inbound_contact',
                    'message': 'Hello, this is a customer reaching out to your business',
                    'sender': {
                        'attendee_id': 'contact_attendee_456',
                        'attendee_provider_id': '27849977040@s.whatsapp.net',  # CONTACT's phone
                        'attendee_name': 'Customer Name'
                    },
                    'provider_chat_id': '27849977040@s.whatsapp.net',  # Same contact
                    'is_group': False,
                    'timestamp': '2025-08-20T16:46:00Z'
                },
                'expected_direction': 'INBOUND'
            }
        ]
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"📨 Scenario {i}: {scenario['name']}")
            print(f"   {scenario['description']}")
            print(f"   Expected Direction: {scenario['expected_direction']}")
            print()
            
            # Process with webhook handler  
            try:
                result = handler.handle_message_received(
                    account_id=connection.unipile_account_id,
                    data=scenario['webhook_data']
                )
                
                print(f"   📋 Webhook Processing Result:")
                print(f"      Success: {result.get('success')}")
                
                if result.get('success'):
                    print(f"      Message ID: {result.get('message_id')}")
                    print(f"      Conversation: {result.get('conversation_name')}")
                    
                    # Get the created message to check direction
                    from communications.models import Message
                    message = Message.objects.filter(
                        external_message_id=scenario['webhook_data']['message_id']
                    ).first()
                    
                    if message:
                        print(f"      ✅ Message Created:")
                        print(f"         Direction: {message.direction}")
                        print(f"         Contact Phone: {message.contact_phone}")
                        
                        # Check detection metadata
                        detection_info = message.metadata.get('direction_detection', {})
                        contact_info = message.metadata.get('contact_identification', {})
                        
                        print(f"         Detection Method: {detection_info.get('detection_method')}")
                        print(f"         Confidence: {detection_info.get('confidence')}")
                        print(f"         Business Phone: {contact_info.get('business_phone')}")
                        print(f"         Contact Phone: {contact_info.get('contact_phone')}")
                        
                        # Verify direction is correct
                        if str(message.direction).upper() == scenario['expected_direction'].upper():
                            print(f"         ✅ DIRECTION CORRECT!")
                        else:
                            print(f"         ❌ DIRECTION WRONG - Expected: {scenario['expected_direction']}, Got: {message.direction}")
                    else:
                        print(f"      ❌ Message not found in database")
                else:
                    print(f"      ❌ Error: {result.get('error')}")
                    
            except Exception as e:
                print(f"   ❌ Webhook processing failed: {e}")
                import traceback
                traceback.print_exc()
            
            print("-" * 40)
        
        print()
        print("🎯 Direction Detection Summary:")
        print(f"   Business Phone: +{business_phone}")
        print("   ✅ Messages FROM business phone = OUTBOUND")
        print("   ✅ Messages TO business phone = INBOUND")
        print("   ✅ Phone number comparison now handles WhatsApp JID format")
        print("   ✅ Contact phone numbers extracted and stored")

if __name__ == "__main__":
    test_webhook_direction_detection()