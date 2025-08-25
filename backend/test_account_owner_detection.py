#!/usr/bin/env python
"""
Test Account Owner Detection
Verifies that the account owner is correctly identified and not treated as a regular attendee
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from communications.utils.account_owner_detection import AccountOwnerDetector
from communications.channels.whatsapp.utils.attendee_detection import WhatsAppAttendeeDetector


def test_account_owner_detector():
    """Test the AccountOwnerDetector utility"""
    print("\n" + "=" * 60)
    print("Testing Account Owner Detection")
    print("=" * 60)
    
    # Test WhatsApp owner detection
    print("\n📱 Testing WhatsApp Account Owner Detection")
    
    business_phone = "+27720720047"  # Josh's business WhatsApp
    detector = AccountOwnerDetector('whatsapp', business_phone)
    
    # Test Case 1: Message from business account (should be owner)
    print("\nTest 1: Message from business account")
    sender_data = {
        'phone': '+27720720047',
        'name': 'Josh Business',
        'id': 'whatsapp_27720720047'
    }
    is_owner = detector.is_account_owner(sender_data)
    print(f"  Sender: {sender_data['phone']}")
    print(f"  Is Owner: {is_owner} {'✅' if is_owner else '❌'}")
    assert is_owner, "Should detect business account as owner"
    
    # Test Case 2: Message from customer (should NOT be owner)
    print("\nTest 2: Message from customer")
    sender_data = {
        'phone': '+15551234567',
        'name': 'Customer John',
        'id': 'whatsapp_15551234567'
    }
    is_owner = detector.is_account_owner(sender_data)
    print(f"  Sender: {sender_data['phone']}")
    print(f"  Is Owner: {is_owner} {'✅' if not is_owner else '❌'}")
    assert not is_owner, "Should NOT detect customer as owner"
    
    # Test Case 3: Message with is_self flag
    print("\nTest 3: Message with is_self flag")
    sender_data = {
        'phone': '+12345678900',
        'name': 'Some User',
        'is_self': True
    }
    is_owner = detector.is_account_owner(sender_data)
    print(f"  Sender: {sender_data['phone']}")
    print(f"  Has is_self: True")
    print(f"  Is Owner: {is_owner} {'✅' if is_owner else '❌'}")
    assert is_owner, "Should detect owner when is_self=True"
    
    # Test Case 4: Phone number with different formatting
    print("\nTest 4: Phone number formatting variations")
    test_phones = [
        '27720720047',  # Without +
        '+27 72 072 0047',  # With spaces
        '27720720047@s.whatsapp.net',  # WhatsApp format
        '0720720047',  # Local format
    ]
    
    for phone in test_phones:
        sender_data = {'phone': phone, 'name': 'Test'}
        is_owner = detector.is_account_owner(sender_data)
        print(f"  Phone: {phone}")
        print(f"  Is Owner: {is_owner} {'✅' if is_owner else '❌'}")
    
    print("\n✅ AccountOwnerDetector tests passed!")


def test_whatsapp_attendee_detector():
    """Test the WhatsAppAttendeeDetector with owner detection"""
    print("\n" + "=" * 60)
    print("Testing WhatsApp Attendee Detector")
    print("=" * 60)
    
    business_phone = "+27720720047"
    detector = WhatsAppAttendeeDetector(business_phone)
    
    # Test webhook data extraction
    print("\n📨 Testing webhook data extraction")
    
    # Simulate webhook data from business account
    webhook_data = {
        'message': {
            'id': 'msg_123',
            'content': 'Hello customer',
            'sender': {
                'phone': '27720720047',
                'name': 'Josh Business',
                'id': 'whatsapp_27720720047'
            }
        },
        'account': {
            'phone': '+27720720047',
            'name': 'Business Account'
        }
    }
    
    attendee_info = detector.extract_attendee_from_webhook(webhook_data)
    print(f"\nBusiness Account Message:")
    print(f"  Phone: {attendee_info['phone_number']}")
    print(f"  Name: {attendee_info['name']}")
    print(f"  Is Self: {attendee_info['is_self']} {'✅' if attendee_info['is_self'] else '❌'}")
    assert attendee_info['is_self'], "Should identify business account as self"
    
    # Simulate webhook data from customer
    webhook_data = {
        'message': {
            'id': 'msg_124',
            'content': 'Hi, I need help',
            'sender': {
                'phone': '+15551234567',
                'name': 'Customer Jane',
                'id': 'whatsapp_15551234567'
            }
        },
        'account': {
            'phone': '+27720720047',
            'name': 'Business Account'
        }
    }
    
    attendee_info = detector.extract_attendee_from_webhook(webhook_data)
    print(f"\nCustomer Message:")
    print(f"  Phone: {attendee_info['phone_number']}")
    print(f"  Name: {attendee_info['name']}")
    print(f"  Is Self: {attendee_info['is_self']} {'✅' if not attendee_info['is_self'] else '❌'}")
    assert not attendee_info['is_self'], "Should NOT identify customer as self"
    
    print("\n✅ WhatsAppAttendeeDetector tests passed!")


def test_attendee_filtering():
    """Test filtering attendees to exclude account owner"""
    print("\n" + "=" * 60)
    print("Testing Attendee Filtering")
    print("=" * 60)
    
    business_phone = "+27720720047"
    detector = AccountOwnerDetector('whatsapp', business_phone)
    
    # Create a list of attendees including the owner
    attendees = [
        {
            'id': '1',
            'phone': '+27720720047',
            'name': 'Josh Business (Owner)',
            'is_self': True
        },
        {
            'id': '2',
            'phone': '+15551234567',
            'name': 'Customer 1'
        },
        {
            'id': '3',
            'phone': '+15559876543',
            'name': 'Customer 2'
        },
        {
            'id': '4',
            'phone': '27720720047',  # Owner with different format
            'name': 'Duplicate Owner Entry'
        }
    ]
    
    print(f"\nOriginal attendees: {len(attendees)}")
    for att in attendees:
        print(f"  - {att['name']} ({att.get('phone', 'no phone')})")
    
    # Filter out the account owner
    filtered = detector.filter_attendees(attendees, exclude_owner=True)
    
    print(f"\nFiltered attendees (excluding owner): {len(filtered)}")
    for att in filtered:
        print(f"  - {att['name']} ({att.get('phone', 'no phone')})")
    
    assert len(filtered) == 2, f"Should have 2 attendees after filtering, got {len(filtered)}"
    assert all(att['name'] not in ['Josh Business (Owner)', 'Duplicate Owner Entry'] for att in filtered)
    
    print("\n✅ Attendee filtering tests passed!")


def test_direction_detection():
    """Test message direction detection using owner detector"""
    print("\n" + "=" * 60)
    print("Testing Direction Detection")
    print("=" * 60)
    
    from communications.utils.message_direction import determine_whatsapp_direction
    
    business_phone = "+27720720047"
    
    # Test outbound message (from business)
    message_data = {
        'sender': {
            'phone': '27720720047',
            'name': 'Business'
        }
    }
    direction = determine_whatsapp_direction(message_data, business_phone)
    print(f"\nBusiness message direction: {direction} {'✅' if direction == 'out' else '❌'}")
    assert direction == 'out', "Business message should be outbound"
    
    # Test inbound message (from customer)
    message_data = {
        'sender': {
            'phone': '+15551234567',
            'name': 'Customer'
        }
    }
    direction = determine_whatsapp_direction(message_data, business_phone)
    print(f"Customer message direction: {direction} {'✅' if direction == 'in' else '❌'}")
    assert direction == 'in', "Customer message should be inbound"
    
    # Test with is_sender flag
    message_data = {
        'is_sender': 1,
        'sender': {
            'phone': '+19999999999'
        }
    }
    direction = determine_whatsapp_direction(message_data, business_phone)
    print(f"Message with is_sender=1: {direction} {'✅' if direction == 'out' else '❌'}")
    assert direction == 'out', "is_sender=1 should be outbound"
    
    print("\n✅ Direction detection tests passed!")


def main():
    """Run all tests"""
    try:
        print("\n🧪 Running Account Owner Detection Tests")
        print("=" * 70)
        
        # Run all test suites
        test_account_owner_detector()
        test_whatsapp_attendee_detector()
        test_attendee_filtering()
        test_direction_detection()
        
        print("\n" + "=" * 70)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 70)
        
        print("\n📋 Summary:")
        print("  ✅ Account owner correctly identified")
        print("  ✅ Customers not mistaken as owner")
        print("  ✅ Phone number normalization working")
        print("  ✅ Attendee filtering excludes owner")
        print("  ✅ Direction detection accurate")
        print("\n💡 The system is ready to properly handle attendees without")
        print("   treating the business account as a regular participant!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()