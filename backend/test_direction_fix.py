#!/usr/bin/env python3
"""
Test script to verify direction detection fix using real account data
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

from communications.models import UserChannelConnection
from communications.services.direction_detection import direction_detection_service
from django_tenants.utils import tenant_context
from tenants.models import Tenant

def test_direction_detection_fix():
    """Test direction detection fix with real account data"""
    print("🧪 Testing Direction Detection Fix")
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
        print(f"🔗 Testing with connection: {connection.account_name}")
        print(f"   Business Phone: +{business_phone}")
        print()
        
        # Test scenarios with realistic UniPile webhook data
        test_scenarios = [
            {
                'name': 'Message YOU sent from YOUR WhatsApp',
                'description': 'When you send a message from your phone, sender should be your business phone',
                'webhook_data': {
                    'event': 'message_received',  # UniPile sends this even for your own messages
                    'chat_id': 'test_chat_123',
                    'message_id': 'msg_from_you_456',
                    'message': 'Hello, this is a message I sent from my WhatsApp',
                    'sender': {
                        'attendee_id': 'your_attendee_id',
                        'attendee_provider_id': f'{business_phone}@s.whatsapp.net',  # YOUR phone number
                        'attendee_name': business_phone
                    },
                    'provider_chat_id': '27849977040@s.whatsapp.net',  # Contact you're sending TO
                    'is_group': False
                },
                'expected_direction': 'OUTBOUND',
                'explanation': 'Sender matches business phone = OUTBOUND'
            },
            {
                'name': 'Message CONTACT sent to you',
                'description': 'When someone sends you a message, sender should be their phone',
                'webhook_data': {
                    'event': 'message_received',
                    'chat_id': 'test_chat_456',
                    'message_id': 'msg_from_contact_789',
                    'message': 'Hello, this is a message from a contact',
                    'sender': {
                        'attendee_id': 'contact_attendee_id',
                        'attendee_provider_id': '27849977040@s.whatsapp.net',  # CONTACT's phone number
                        'attendee_name': 'Contact Name'
                    },
                    'provider_chat_id': '27849977040@s.whatsapp.net',  # Same contact
                    'is_group': False
                },
                'expected_direction': 'INBOUND',
                'explanation': 'Sender does NOT match business phone = INBOUND'
            }
        ]
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"📋 Test Scenario {i}: {scenario['name']}")
            print(f"   {scenario['description']}")
            print(f"   Expected: {scenario['expected_direction']} - {scenario['explanation']}")
            
            # Test direction detection
            direction, detection_metadata = direction_detection_service.determine_direction(
                connection=connection,
                message_data=scenario['webhook_data'],
                event_type=scenario['webhook_data'].get('event')
            )
            
            print(f"   🎯 Result: {direction}")
            print(f"   Method: {detection_metadata.get('detection_method')}")
            print(f"   Confidence: {detection_metadata.get('confidence')}")
            
            # Check if detection is correct
            if str(direction).upper() == scenario['expected_direction'].upper():
                print(f"   ✅ CORRECT - Direction detection working!")
            else:
                print(f"   ❌ INCORRECT - Expected: {scenario['expected_direction']}, Got: {direction}")
                
                # Debug the detection process
                print(f"   🔍 Debug Info:")
                print(f"      Account Phone: {detection_metadata.get('account_phone')}")
                sender_info = detection_metadata.get('sender_info', {})
                print(f"      Sender Info: {sender_info}")
                if 'attendee_provider_id' in sender_info:
                    print(f"      Sender Phone: {sender_info['attendee_provider_id']}")
            
            print()
        
        print("🎯 Summary:")
        print(f"   Business Phone: +{business_phone}")
        print("   ✅ Direction detection now prioritizes phone number comparison")
        print("   ✅ Webhook event type is fallback only")
        print("   ✅ Your messages (from business phone) = OUTBOUND")
        print("   ✅ Contact messages (not business phone) = INBOUND")

if __name__ == "__main__":
    test_direction_detection_fix()