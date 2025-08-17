#!/usr/bin/env python3
"""
Debug webhook data structure to understand the 'str' object has no attribute 'get' error
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
from communications.webhooks.handlers import webhook_handler

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test webhook data structures that might be causing the error
def test_webhook_structures():
    """Test different webhook data structures to identify the issue"""
    
    # Test structure 1: Normal webhook data
    normal_data = {
        'event': 'message_received',
        'account_id': 'mp9Gis3IRtuh9V5oSxZdSA',
        'message_id': 'test_123',
        'chat_id': '1T1s9uwKX3yXDdHr9p9uWQ',
        'message': 'Test message content',
        'sender': {
            'attendee_id': 'test_attendee',
            'attendee_name': 'Test User',
            'attendee_provider_id': '27849977040@s.whatsapp.net'
        }
    }
    
    # Test structure 2: String data (might be causing the issue)
    string_data = "{'event': 'message_received', 'account_id': 'mp9Gis3IRtuh9V5oSxZdSA'}"
    
    # Test structure 3: List data 
    list_data = ['message_received', 'mp9Gis3IRtuh9V5oSxZdSA']
    
    print("=== Testing Normal Dict Data ===")
    try:
        result = webhook_handler.process_webhook('message_received', normal_data)
        print(f"Normal data result: {result}")
    except Exception as e:
        print(f"Normal data error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Testing String Data ===")
    try:
        result = webhook_handler.process_webhook('message_received', string_data)
        print(f"String data result: {result}")
    except Exception as e:
        print(f"String data error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Testing List Data ===")
    try:
        result = webhook_handler.process_webhook('message_received', list_data)
        print(f"List data result: {result}")
    except Exception as e:
        print(f"List data error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_webhook_structures()