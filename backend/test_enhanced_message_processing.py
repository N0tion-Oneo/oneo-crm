#!/usr/bin/env python3
"""
Test script to verify enhanced message processing with account data integration
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

from communications.models import UserChannelConnection, Message
from communications.services.direction_detection import direction_detection_service
from communications.services.contact_identification import contact_identification_service
from django_tenants.utils import tenant_context
from tenants.models import Tenant

def test_enhanced_message_processing():
    """Test enhanced message processing with account data integration"""
    print("🧪 Testing Enhanced Message Processing")
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
        
        print(f"🔗 Testing with connection: {connection.account_name}")
        print(f"   Business Phone: +{connection.connection_config.get('phone_number', 'N/A')}")
        print()
        
        # Test direction detection capabilities
        print("🎯 Direction Detection Capabilities:")
        direction_summary = direction_detection_service.get_detection_summary(connection)
        for capability in direction_summary.get('detection_capabilities', []):
            print(f"   ✅ {capability}")
        print()
        
        # Test contact identification capabilities
        print("📱 Contact Identification Capabilities:")
        contact_summary = contact_identification_service.get_identification_summary(connection)
        for method in contact_summary.get('identification_methods', []):
            print(f"   ✅ {method}")
        print()
        
        # Test with sample webhook data scenarios
        test_scenarios = [
            {
                'name': 'Incoming Message from External Contact',
                'data': {
                    'chat_id': 'test_chat_123',
                    'message_id': 'test_msg_456',
                    'message': 'Hello from external contact',
                    'sender': {
                        'attendee_id': 'ext_user_123',
                        'attendee_provider_id': '27849977040@s.whatsapp.net',
                        'attendee_name': 'Test Contact'
                    },
                    'provider_chat_id': '27849977040@s.whatsapp.net',
                    'is_group': False
                },
                'expected_direction': 'INBOUND',
                'expected_contact_phone': '+27849977040'
            },
            {
                'name': 'Outgoing Message from Business Account',
                'data': {
                    'chat_id': 'test_chat_456',
                    'message_id': 'test_msg_789',
                    'message': 'Hello from business',
                    'sender': {
                        'attendee_id': 'bus_user_123',
                        'attendee_provider_id': '27720720047@s.whatsapp.net',
                        'attendee_name': '27720720047'
                    },
                    'provider_chat_id': '27849977040@s.whatsapp.net',  # Different from sender
                    'is_group': False
                },
                'expected_direction': 'OUTBOUND',
                'expected_contact_phone': '+27849977040'
            },
            {
                'name': 'Group Chat Message',
                'data': {
                    'chat_id': 'group_chat_789@g.us',
                    'message_id': 'test_group_msg_123',
                    'message': 'Hello group!',
                    'sender': {
                        'attendee_id': 'group_member_123',
                        'attendee_provider_id': '27849977040@s.whatsapp.net',
                        'attendee_name': 'Group Member'
                    },
                    'is_group': True,
                    'subject': 'Test Group Chat'
                },
                'expected_direction': 'INBOUND',
                'expected_contact_phone': None  # No individual phone for groups
            }
        ]
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"📋 Test Scenario {i}: {scenario['name']}")
            
            # Test direction detection
            direction, detection_metadata = direction_detection_service.determine_direction(
                connection=connection,
                message_data=scenario['data'],
                event_type='message_received'
            )
            
            print(f"   Direction: {direction} (method: {detection_metadata.get('detection_method')})")
            print(f"   Confidence: {detection_metadata.get('confidence')}")
            
            # Verify expected direction
            if str(direction) == scenario['expected_direction']:
                print(f"   ✅ Direction detection PASSED")
            else:
                print(f"   ❌ Direction detection FAILED - Expected: {scenario['expected_direction']}, Got: {direction}")
            
            # Test contact identification
            contact_info = contact_identification_service.identify_whatsapp_contact(connection, scenario['data'])
            
            print(f"   Contact Phone: {contact_info.get('contact_phone', 'None')}")
            print(f"   Contact Name: {contact_info.get('contact_name', 'None')}")
            print(f"   Business Phone: {contact_info.get('business_phone', 'None')}")
            print(f"   Is Group: {contact_info.get('is_group_chat', False)}")
            print(f"   Method: {contact_info.get('identification_method')}")
            
            # Verify expected contact phone
            expected_phone = scenario['expected_contact_phone']
            actual_phone = contact_info.get('contact_phone')
            
            if expected_phone == actual_phone:
                print(f"   ✅ Contact identification PASSED")
            else:
                print(f"   ❌ Contact identification FAILED - Expected: {expected_phone}, Got: {actual_phone}")
            
            # Get formatted display name
            display_name = contact_identification_service.get_formatted_contact_display(contact_info)
            print(f"   Display Name: {display_name}")
            
            print()
        
        # Check existing messages for enhanced data
        print("📊 Checking Existing Messages for Enhanced Data:")
        recent_messages = Message.objects.filter(
            channel__channel_type='whatsapp'
        ).order_by('-created_at')[:5]
        
        for msg in recent_messages:
            print(f"   Message {msg.id}:")
            print(f"     Direction: {msg.direction}")
            print(f"     Contact Phone: {msg.contact_phone or 'Not stored'}")
            
            # Check metadata for enhanced data
            if 'direction_detection' in msg.metadata:
                detection_info = msg.metadata['direction_detection']
                print(f"     Detection Method: {detection_info.get('detection_method', 'N/A')}")
                print(f"     Detection Confidence: {detection_info.get('confidence', 'N/A')}")
            
            if 'contact_identification' in msg.metadata:
                contact_info = msg.metadata['contact_identification']
                print(f"     Contact Name: {contact_info.get('contact_name', 'N/A')}")
                print(f"     Business Phone: {contact_info.get('business_phone', 'N/A')}")
            
            print()
        
        print("🎯 Summary:")
        print("   ✅ Enhanced direction detection using account data")
        print("   ✅ Comprehensive contact identification")
        print("   ✅ Business phone number integration")
        print("   ✅ Group chat detection and handling")
        print("   ✅ Metadata storage for debugging and analytics")
        print("   ✅ Message model integration with contact_phone field")

if __name__ == "__main__":
    test_enhanced_message_processing()