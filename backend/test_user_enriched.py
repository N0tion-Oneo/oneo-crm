#!/usr/bin/env python
"""
Test script to verify the user-enriched workflow system
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from workflows.triggers.handlers.communication_handlers import EmailReceivedHandler, MessageReceivedHandler
from workflows.triggers.types import TriggerEvent
from datetime import datetime
import asyncio
import json

User = get_user_model()

async def test_trigger_handlers():
    """Test the updated trigger handlers with user-based filtering"""

    print("Testing User-Enriched Workflow System")
    print("=" * 50)

    # Create test trigger configurations
    trigger_config_all_users = {
        'monitor_users': 'all'
    }

    trigger_config_specific_user = {
        'monitor_users': ['user123']
    }

    trigger_config_user_with_account = {
        'monitor_users': [
            {'user_id': 'user456', 'account_id': 'account789'}
        ]
    }

    trigger_config_mixed = {
        'monitor_users': [
            'user123',
            {'user_id': 'user456', 'account_id': 'account789'}
        ]
    }

    # Create test event data
    test_event = TriggerEvent(
        event_type='email_received',
        event_data={
            'user_id': 'user123',
            'account_id': 'account111',
            'sender': 'test@example.com',
            'subject': 'Test Email',
            'recipient': 'user@company.com',
            'message_id': 'msg123',
            'account_name': 'User Email Account'
        },
        timestamp=datetime.now()
    )

    # Initialize handlers
    email_handler = EmailReceivedHandler()
    message_handler = MessageReceivedHandler()

    # Create mock trigger object
    class MockTrigger:
        def __init__(self, configuration):
            self.configuration = configuration

    print("\n1. Testing 'all users' configuration:")
    trigger = MockTrigger(trigger_config_all_users)
    matches = await email_handler.matches_event(trigger, test_event)
    print(f"   Event matches 'all users' trigger: {matches}")
    assert matches == True, "Should match when monitoring all users"

    print("\n2. Testing specific user configuration:")
    trigger = MockTrigger(trigger_config_specific_user)
    matches = await email_handler.matches_event(trigger, test_event)
    print(f"   Event matches user 'user123' trigger: {matches}")
    assert matches == True, "Should match when event user_id matches monitored user"

    print("\n3. Testing user with specific account:")
    trigger = MockTrigger(trigger_config_user_with_account)
    matches = await email_handler.matches_event(trigger, test_event)
    print(f"   Event matches user456/account789 trigger: {matches}")
    assert matches == False, "Should not match when user_id doesn't match"

    # Test with matching user and account
    test_event_matching_account = TriggerEvent(
        event_type='email_received',
        event_data={
            'user_id': 'user456',
            'account_id': 'account789',
            'sender': 'test@example.com',
            'subject': 'Test Email'
        },
        timestamp=datetime.now()
    )

    matches = await email_handler.matches_event(trigger, test_event_matching_account)
    print(f"   Event matches user456/account789 with correct data: {matches}")
    assert matches == True, "Should match when both user_id and account_id match"

    print("\n4. Testing mixed configuration:")
    trigger = MockTrigger(trigger_config_mixed)
    matches = await email_handler.matches_event(trigger, test_event)
    print(f"   Event matches mixed configuration for user123: {matches}")
    assert matches == True, "Should match when user_id is in the list"

    print("\n5. Testing message handler with LinkedIn:")
    linkedin_event = TriggerEvent(
        event_type='message_received',
        event_data={
            'user_id': 'user123',
            'account_id': 'linkedin_account',
            'channel': 'linkedin',
            'sender': 'John Doe',
            'content': 'Hello, interested in your services',
            'thread_id': 'thread123'
        },
        timestamp=datetime.now()
    )

    trigger = MockTrigger({'monitor_users': ['user123'], 'monitor_channels': ['linkedin']})
    matches = await message_handler.matches_event(trigger, linkedin_event)
    print(f"   LinkedIn message matches trigger: {matches}")
    assert matches == True, "Should match LinkedIn message for monitored user"

    print("\n6. Testing data extraction:")
    extracted = await email_handler.extract_data(None, test_event)
    print(f"   Extracted user_id: {extracted.get('user_id')}")
    print(f"   Extracted account_id: {extracted.get('account_id')}")
    print(f"   Extracted account_name: {extracted.get('account_name')}")
    assert extracted.get('user_id') == 'user123', "Should extract user_id"
    assert extracted.get('account_id') == 'account111', "Should extract account_id"

    print("\n✅ All tests passed! User-enriched workflow system is working correctly.")
    print("\nKey Features Verified:")
    print("• Support for 'all users' monitoring")
    print("• Support for specific user selection")
    print("• Support for user + account combinations")
    print("• Proper event filtering based on configuration")
    print("• Data extraction includes user and account information")

    return True

if __name__ == '__main__':
    # Run async tests
    result = asyncio.run(test_trigger_handlers())
    sys.exit(0 if result else 1)